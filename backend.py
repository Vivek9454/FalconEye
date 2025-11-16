import os
import cv2
import time
import uuid
import json
import boto3
import threading
import requests
import numpy as np
from datetime import datetime, timezone, timedelta
import concurrent.futures
import multiprocessing
from concurrent.futures import TimeoutError as FutureTimeoutError
try:
    import faces_worker
except Exception:
    faces_worker = None
from ultralytics import YOLO
from flask import Flask, request, jsonify, Response, send_from_directory, send_file, render_template_string, redirect, url_for, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import torch
from collections import defaultdict, deque
import base64
try:
    # Optional high-accuracy face engine (InsightFace)
    from faces.insight_engine import is_available as insight_available, encode_image_bgr as insight_encode
except Exception:
    insight_available = lambda: False  # noqa: E731
    insight_encode = None
try:
    import face_recognition
except Exception:
    face_recognition = None
# Removed Firebase imports - using local notifications now
from local_notification_service import notification_service, send_push_notification, send_security_alert, send_test_notification, get_notification_status

# ---------------- CONFIG ----------------
# Dynamic Network Profiles: define multiple IP groups; the app will auto-select
# the first reachable profile on startup. Env vars override when set.

NETWORK_PROFILES = [
    {
        "name": "home",
        "cameras": {
            "cam1": "http://10.103.190.6/jpg",         # ESP32 snapshot (update if different IP)
            "cam2": "http://10.103.190.170:8081/",     # Pi Zero MJPEG
        },
        "esp_pan_base": "http://10.103.190.58",
    },
    {
        "name": "hotspot",
        "cameras": {
            "cam1": "http://10.103.190.6/jpg",
            "cam2": "http://10.103.190.170:8081/",
        },
        "esp_pan_base": "http://10.103.190.58",
    },
]

# Allow full override via env JSON strings if user wants
import json as _json_mod
try:
    _env_profiles = os.getenv("FALCONEYE_NETWORK_PROFILES")
    if _env_profiles:
        NETWORK_PROFILES = _json_mod.loads(_env_profiles)
except Exception:
    pass

# Helper to test reachability quickly
def _is_reachable(url: str, timeout: float = 0.8) -> bool:
    try:
        # For MJPEG base URLs we may need a concrete path, but doing a GET should still return something
        r = requests.get(url, timeout=timeout, stream=True)
        return r.status_code >= 200 and r.status_code < 500
    except Exception:
        return False

def _select_active_profile() -> dict:
    # Env direct overrides take precedence
    env_cam1 = os.getenv("CAM1_URL")
    env_cam2 = os.getenv("CAM2_URL")
    env_pan = os.getenv("ESP_PAN_BASE_URL")
    if env_cam1 or env_cam2 or env_pan:
        cams = {
            "cam1": env_cam1 or NETWORK_PROFILES[0]["cameras"]["cam1"],
            "cam2": env_cam2 or NETWORK_PROFILES[0]["cameras"]["cam2"],
        }
        return {"name": "env_override", "cameras": cams, "esp_pan_base": env_pan or NETWORK_PROFILES[0]["esp_pan_base"]}

    # Probe each profile; consider it valid if at least cam1 or cam2 is reachable
    for profile in NETWORK_PROFILES:
        cam1_url = profile["cameras"].get("cam1")
        cam2_url = profile["cameras"].get("cam2")
        ok1 = _is_reachable(cam1_url) if cam1_url else False
        # For MJPEG streams, hit the base or append a simple param to avoid caching
        ok2 = _is_reachable(cam2_url) if cam2_url else False
        if ok1 or ok2:
            return profile
    # Fallback to first profile if none reachable
    return NETWORK_PROFILES[0]

ACTIVE_PROFILE = _select_active_profile()
CAMERAS = ACTIVE_PROFILE["cameras"].copy()

# Pan (PTZ) controller for Pi Zero mount (ESP8266/ESP32 HTTP endpoints)
# You can override via environment variable ESP_PAN_BASE_URL
ESP_PAN_BASE_URL = os.getenv("ESP_PAN_BASE_URL", ACTIVE_PROFILE.get("esp_pan_base", "http://192.168.31.75"))

# Test mode - set to True to use test images instead of ESP32
TEST_MODE = False

# Fallback mode - set to True if camera has connection issues
FALLBACK_MODE = False

# Home surveillance objects - essential security objects for home surveillance
SURVEILLANCE_OBJECTS = {
    'person',        # People (primary security target)
    'car',          # Cars (vehicles approaching/leaving)
    'truck',        # Trucks (delivery vehicles, suspicious vehicles)
    'bicycle',      # Bicycles (people on bikes)
    'motorcycle',   # Motorcycles (people on motorcycles)
    'dog',          # Dogs (pets, potential intruders)
    'cat'           # Cats (pets, potential intruders)
}

# Camera tampering detection settings
CAMERA_TAMPERING_ENABLED = True
TAMPERING_THRESHOLD = 30  # Average brightness threshold (0-255)
TAMPERING_COOLDOWN = 60   # Seconds between tampering alerts
tampering_detection = {}  # Track tampering state per camera

# Intruder detection settings
INTRUDER_DETECTION_ENABLED = True
NIGHT_TIME_START = 22  # 10 PM
NIGHT_TIME_END = 6     # 6 AM
LINGERING_THRESHOLD = 30  # seconds someone needs to be in frame to trigger lingering alert
SUSPICIOUS_MOVEMENT_THRESHOLD = 5  # rapid movements in short time

# Intruder detection monitoring
person_detection_times = {}  # Track when people are first detected
person_positions = {}  # Track person positions for movement analysis
intruder_alerts_sent = {}  # Track sent alerts to prevent spam

OUTPUT_DIR = "clips"
METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.json")

AWS_BUCKET = "falconeye-clips"
AWS_REGION = "ap-south-1"

CLIP_DURATION = 12
COOLDOWN = 10  # Reduced cooldown for testing
FPS = 10.0

# Recent detections memory for mobile/dashboard overlays
recent_detections = deque(maxlen=25)

# Recording concurrency guard per camera
_recording_active = set()
_recording_lock = threading.Lock()

def start_recording_if_idle(camera_id, camera_url, tags, duration):
    with _recording_lock:
        if camera_id in _recording_active:
            return False
        _recording_active.add(camera_id)

    def _runner():
        try:
            record_clip(camera_id, camera_url, tags, duration)
        finally:
            with _recording_lock:
                _recording_active.discard(camera_id)

    threading.Thread(target=_runner, daemon=True).start()
    return True

# Local Notification Configuration
registered_tokens = set()  # Keep for backward compatibility for ios

# Authentication
USERS = {
    "admin": generate_password_hash("password123")
}

# ---------------- INIT ----------------
os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, "w") as f:
        json.dump({}, f)

# Limit parallelism to reduce native/BLAS pressure on macOS (helps stability on M-series with limited RAM)
os.environ.setdefault("OMP_NUM_THREADS", os.environ.get("OMP_NUM_THREADS", "1"))
os.environ.setdefault("MKL_NUM_THREADS", os.environ.get("MKL_NUM_THREADS", "1"))
try:
    # reduce torch thread usage to avoid oversubscription
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))
    torch.set_num_interop_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))
except Exception:
    pass
# ---------------- Device Selection ----------------
# Allow overriding device via environment variable for stability or testing.
# Supported values: "cuda", "mps", "cpu". If not set, auto-detect.
FALCONEYE_DEVICE_OVERRIDE = os.getenv("FALCONEYE_DEVICE", "auto").lower()
if FALCONEYE_DEVICE_OVERRIDE == "cuda":
    DEVICE = "cuda"
    GPU_NAME = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    print(f"[INFO] Forcing device -> CUDA (requested). GPU: {GPU_NAME}")
elif FALCONEYE_DEVICE_OVERRIDE == "mps":
    DEVICE = "mps"
    GPU_NAME = "Apple Silicon GPU"
    print("[INFO] Forcing device -> MPS (requested)")
elif FALCONEYE_DEVICE_OVERRIDE == "cpu":
    DEVICE = "cpu"
    GPU_NAME = None
    print("[INFO] Forcing device -> CPU (requested)")
else:
    # auto-detect
    if torch.cuda.is_available():
        DEVICE = "cuda"
        GPU_NAME = torch.cuda.get_device_name(0)
        print(f"[INFO] CUDA available ✅ Using GPU: {GPU_NAME}")
    elif torch.backends.mps.is_available():
        DEVICE = "mps"  # Apple Metal Performance Shaders for M1/M2
        GPU_NAME = "Apple Silicon GPU"
        print(f"[INFO] MPS available ✅ Using Apple Silicon GPU")
    else:
        DEVICE = "cpu"
        GPU_NAME = None
        print("[INFO] No GPU acceleration available ⚠️ Falling back to CPU")

# Load YOLO model
# Use separate models for general detection vs. live-streaming
# Defaults can be overridden via env vars for quick tuning
DETECT_MODEL_NAME = os.getenv("FALCONEYE_DETECT_MODEL", "yolov8s.pt")
LIVE_MODEL_NAME = os.getenv("FALCONEYE_LIVE_MODEL", "yolov8n.pt")

def _safe_load_yolo(name: str, device: str):
    """Try to load YOLO model to the requested device. On failure, fall back to CPU.

    Returns (model, actual_device)
    """
    try:
        print(f"[INFO] Loading model {name} -> {device}")
        m = YOLO(name)
        try:
            m = m.to(device)
            print(f"[INFO] Model {name} loaded on {device}")
            return m, device
        except Exception as e:
            print(f"[WARN] moving model {name} to {device} failed: {e}")
            # attempt CPU fallback
            try:
                m = m.to("cpu")
                print(f"[INFO] Model {name} loaded on cpu (fallback)")
                return m, "cpu"
            except Exception as e2:
                print(f"[ERROR] Failed to load model {name} on CPU as fallback: {e2}")
                raise
    except Exception as e:
        print(f"[ERROR] Failed to initialize YOLO model {name}: {e}")
        raise

# Load models with safe fallback to CPU if needed
try:
    model, _actual = _safe_load_yolo(DETECT_MODEL_NAME, DEVICE)
    # If we had to fall back to CPU, update DEVICE to reflect actual runtime
    if _actual != DEVICE:
        print(f"[WARN] Device fallback: requested {DEVICE} but using {_actual}")
        DEVICE = _actual
except Exception:
    print("[ERROR] Unable to load detect model. Exiting.")
    raise

try:
    live_model, _ = _safe_load_yolo(LIVE_MODEL_NAME, DEVICE)
except Exception:
    print("[ERROR] Unable to load live model. Exiting.")
    raise

# ---------------- Face recognition toggle ----------------
# Allow disabling face_recognition (dlib) to keep live stream lightweight.
DISABLE_FACE_RECOGNITION = os.getenv("FALCONEYE_DISABLE_FACE_RECOGNITION", "false").lower() in ("1", "true", "yes")
if DISABLE_FACE_RECOGNITION:
    print("[INFO] Face recognition disabled via FALCONEYE_DISABLE_FACE_RECOGNITION")

# Setup AWS S3 client (only if credentials are available)
try:
    from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_BUCKET
    aws_access_key = AWS_ACCESS_KEY_ID
    aws_secret_key = AWS_SECRET_ACCESS_KEY
    AWS_REGION = AWS_REGION
    S3_BUCKET_NAME = AWS_BUCKET
except ImportError:
    # Fallback to environment variables
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'falconeye-clips')

if aws_access_key and aws_secret_key:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=AWS_REGION,
    )
    print("[S3] AWS credentials configured ✅")
else:
    s3 = None
    print("[S3] AWS credentials not configured ⚠️ S3 uploads disabled")

app = Flask(__name__)

# Security Configuration
# Secret key for session-based auth (override via env FALCONEYE_SECRET)
_secret_key = os.environ.get("FALCONEYE_SECRET")
if not _secret_key or _secret_key == "dev-secret-change-me":
    import secrets
    _secret_key = secrets.token_hex(32)
    if os.environ.get("FALCONEYE_SECRET") != "dev-secret-change-me":
        print("[WARNING] Using generated secret key. Set FALCONEYE_SECRET env var for production!")
app.secret_key = _secret_key

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)  # Default session timeout

# Security headers middleware
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Only add HSTS in production with HTTPS
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Simple login-required decorator
def login_required(view_func):
    def wrapper(*args, **kwargs):
        # Allow health/mobile endpoints without auth
        if request.path.startswith(("/mobile", "/camera", "/clips", "/system", "/fcm", "/auth")):
            return view_func(*args, **kwargs)
        
        # Check if user is already logged in
        if session.get("user"):
            return view_func(*args, **kwargs)
        
        # Only redirect to login for new users/connections
        return redirect(url_for("login_page", next=request.path))
    # Preserve function name for Flask
    wrapper.__name__ = view_func.__name__
    return wrapper
CORS(app)

# ---------------- Helpers ----------------

# Vision settings (overlay controls)
VISION_SETTINGS_FILE = os.path.join(os.getcwd(), "vision_settings.json")
DEFAULT_VISION_SETTINGS = {
    "show_boxes": True,
    "show_labels": True,
    "show_summary": True,
    "min_area": 5000,
    # Face recognition controls
    "faces": {
        "enabled": True,
        "overlay": True,
        "tolerance": 0.6,           # default threshold; for InsightFace typical ~0.35-0.45
        "sample_every": 10,         # run recognition every N frames on live streams
        "hide_person_if_named": True
    },
    "enabled_classes": {
        "person": True,
        "car": True,
        "truck": True,
        "bicycle": True,
        "motorcycle": True,
        "dog": True,
        "cat": True
    },
    "colors": {
        "person": "#00E676",
        "car": "#FFC107",
        "truck": "#FF9800",
        "bicycle": "#03A9F4",
        "motorcycle": "#00BCD4",
        "dog": "#9C27B0",
        "cat": "#E91E63"
    }
}

VISION_SETTINGS = DEFAULT_VISION_SETTINGS.copy()

def _merge_vision_settings(base, override):
    out = json.loads(json.dumps(base))
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out

def load_vision_settings():
    global VISION_SETTINGS
    try:
        if os.path.exists(VISION_SETTINGS_FILE):
            with open(VISION_SETTINGS_FILE, "r") as f:
                data = json.load(f)
            VISION_SETTINGS = _merge_vision_settings(DEFAULT_VISION_SETTINGS, data)
        else:
            VISION_SETTINGS = DEFAULT_VISION_SETTINGS.copy()
        # Optional env override to quickly disable faces without editing file
        env_faces = os.getenv("FALCONEYE_FACES_ENABLED")
        if env_faces is not None:
            val = env_faces.strip().lower() in ("1", "true", "yes", "on")
            VISION_SETTINGS.setdefault("faces", {})["enabled"] = val
    except Exception as e:
        print(f"[VISION] Failed to load settings: {e}")
        VISION_SETTINGS = DEFAULT_VISION_SETTINGS.copy()

def save_vision_settings():
    try:
        with open(VISION_SETTINGS_FILE, "w") as f:
            json.dump(VISION_SETTINGS, f, indent=2)
    except Exception as e:
        print(f"[VISION] Failed to save settings: {e}")

def is_class_enabled(name: str) -> bool:
    return VISION_SETTINGS.get("enabled_classes", {}).get(name, True)

def hex_to_bgr(hex_color: str):
    try:
        hex_color = hex_color.strip()
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (b, g, r)
    except Exception:
        pass
    return (0, 200, 255)

def class_color_bgr(name: str):
    hexc = VISION_SETTINGS.get("colors", {}).get(name)
    if not hexc:
        return (0, 200, 255)
    return hex_to_bgr(hexc)
def load_metadata():
    with open(METADATA_FILE, "r") as f:
        data = json.load(f)
    
    # Filter out AVI files, only return MP4 files for iOS compatibility
    filtered_data = {}
    for filename, metadata in data.items():
        if filename.endswith('.mp4'):
            filtered_data[filename] = metadata
    
    return filtered_data

def save_metadata(data):
    with open(METADATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- Faces DB ----------------
FACES_DIR = os.path.join("faces", "images")
FACES_DB_PATH = os.path.join("faces", "faces_db.json")

# In-memory cache of encodings: { name: [encoding_vectors] }
face_encodings_db = {}
# Runtime safety flag: if face engine misbehaves, disable faces for this session
FACES_RUNTIME_DISABLED = False
# ProcessPoolExecutor used to isolate face-recognition work from the main process
_FR_EXECUTOR = None
_FR_EXECUTOR_LOCK = threading.Lock()


def _get_fr_executor():
    global _FR_EXECUTOR
    with _FR_EXECUTOR_LOCK:
        if _FR_EXECUTOR is not None:
            return _FR_EXECUTOR
        # Use a single-worker ProcessPoolExecutor to run face encoding in a separate process.
        try:
            # On macOS the default start method is 'spawn' which avoids forking issues with libraries.
            try:
                multiprocessing.get_start_method()
            except RuntimeError:
                multiprocessing.set_start_method('spawn')
            _FR_EXECUTOR = concurrent.futures.ProcessPoolExecutor(max_workers=1)
            return _FR_EXECUTOR
        except Exception as e:
            print(f"[FACES] Failed to start face-worker executor: {e}")
            _FR_EXECUTOR = None
            return None

def load_face_db():
    global face_encodings_db
    try:
        if os.path.exists(FACES_DB_PATH):
            with open(FACES_DB_PATH, "r") as f:
                raw = json.load(f) or {}
            # Ensure numpy arrays
            face_encodings_db = {k: [np.array(e, dtype=np.float32) for e in v] for k, v in raw.items()}
        else:
            face_encodings_db = {}
    except Exception as e:
        print(f"[FACES] Failed to load DB: {e}")
        face_encodings_db = {}

def save_face_db():
    try:
        os.makedirs(os.path.dirname(FACES_DB_PATH), exist_ok=True)
        serializable = {k: [e.tolist() for e in v] for k, v in face_encodings_db.items()}
        with open(FACES_DB_PATH, "w") as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"[FACES] Failed to save DB: {e}")

def compute_face_encodings_from_image(image_bgr, timeout: float = 6.0):
    """Compute face encodings from a BGR image using a separate worker process.

    The worker runs code from `faces_worker.py` which prefers InsightFace then falls back
    to `face_recognition`. Running this in a separate process isolates native library
    failures (dlib/libtorch) from the main backend server.

    Returns a list of numpy.float32 vectors.
    """
    global FACES_RUNTIME_DISABLED
    if FACES_RUNTIME_DISABLED:
        return []
    try:
        if not VISION_SETTINGS.get('faces', {}).get('enabled', True):
            return []
    except Exception:
        return []

    # If the user or startup explicitly disabled face recognition, skip
    if DISABLE_FACE_RECOGNITION:
        return []

    # Ensure worker module is available
    if faces_worker is None:
        # No isolation worker available; fall back to in-process (best-effort)
        try:
            if insight_available() and insight_encode is not None:
                encs = insight_encode(image_bgr)
                if encs:
                    return [np.array(e, dtype=np.float32) for e in encs]
        except Exception as e:
            print(f"[FACES] InsightFace encode error (no worker): {e}")
            FACES_RUNTIME_DISABLED = True
            return []
        if face_recognition is None:
            return []
        try:
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(image_rgb, model="hog")
            encs = face_recognition.face_encodings(image_rgb, boxes)
            return [np.array(e, dtype=np.float32) for e in encs]
        except Exception as e:
            print(f"[FACES] Encoding error (no worker): {e}")
            FACES_RUNTIME_DISABLED = True
            return []

    # Use the process-isolated worker
    executor = _get_fr_executor()
    if executor is None:
        # If we couldn't start the worker, fallback to in-process once
        print("[FACES] Worker executor not available; falling back to in-process encoding once.")
        try:
            if insight_available() and insight_encode is not None:
                encs = insight_encode(image_bgr)
                if encs:
                    return [np.array(e, dtype=np.float32) for e in encs]
        except Exception as e:
            print(f"[FACES] InsightFace encode error (fallback): {e}")
            FACES_RUNTIME_DISABLED = True
            return []
        try:
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(image_rgb, model="hog")
            encs = face_recognition.face_encodings(image_rgb, boxes)
            return [np.array(e, dtype=np.float32) for e in encs]
        except Exception as e:
            print(f"[FACES] Encoding error (fallback): {e}")
            FACES_RUNTIME_DISABLED = True
            return []

    # Submit job to worker
    try:
        future = executor.submit(faces_worker.compute_encodings, image_bgr)
        raw = future.result(timeout=timeout)
        if not raw:
            return []
        # raw is a list of lists (floats)
        return [np.array(e, dtype=np.float32) for e in raw]
    except FutureTimeoutError:
        try:
            future.cancel()
        except Exception:
            pass
        print("[FACES] Worker timed out during encoding")
        return []
    except Exception as e:
        print(f"[FACES] Worker failed: {e}")
        # Mark runtime disabled to avoid repeated failures; the executor may be broken
        try:
            FACES_RUNTIME_DISABLED = True
            if _FR_EXECUTOR:
                try:
                    _FR_EXECUTOR.shutdown(wait=False)
                except Exception:
                    pass
            _FR_EXECUTOR = None
        except Exception:
            pass
        return []

def register_face_encoding(name: str, encoding_vec):
    name = name.strip()
    if not name:
        return False, "Invalid name"
    face_encodings_db.setdefault(name, []).append(np.array(encoding_vec, dtype=np.float32))
    save_face_db()
    return True, "registered"

def recognize_faces_in_frame(frame_bgr, person_boxes_xyxy=None, tolerance=0.6):
    if DISABLE_FACE_RECOGNITION:
        return []
    if FACES_RUNTIME_DISABLED or not VISION_SETTINGS.get('faces', {}).get('enabled', True):
        return []
    if not face_encodings_db:
        return []
    recognized = []
    try:
        if person_boxes_xyxy is None or len(person_boxes_xyxy) == 0:
            encs = compute_face_encodings_from_image(frame_bgr)
            enc_to_compare = encs
        else:
            enc_to_compare = []
            for (x1, y1, x2, y2) in person_boxes_xyxy:
                x1i, y1i, x2i, y2i = map(lambda v: max(0, int(v)), [x1, y1, x2, y2])
                crop = frame_bgr[y1i:y2i, x1i:x2i]
                if crop.size == 0:
                    continue
                # Upscale very small crops to help the encoder
                h, w = crop.shape[:2]
                if min(h, w) < 80:
                    scale = 160.0 / max(1, min(h, w))
                    crop = cv2.resize(crop, (max(1, int(w*scale)), max(1, int(h*scale))))
                crop_encs = compute_face_encodings_from_image(crop)
                enc_to_compare.extend(crop_encs)
        if not enc_to_compare:
            return []
        # For each computed encoding, compare with compatible known encodings
        for enc in enc_to_compare:
            best_name = None
            best_dist = 1e9
            # decide metric based on length (128 => face_recognition; 512 => InsightFace common)
            enc_vec = np.array(enc, dtype=np.float32).reshape(-1)
            enc_len = enc_vec.shape[0]
            use_fr = (face_recognition is not None and enc_len == 128)
            # Adaptive threshold: if using cosine distance and default-ish tol, tighten it
            eff_tol = float(tolerance)
            if not use_fr and abs(eff_tol - 0.6) < 1e-6:
                eff_tol = 0.35
            for name, enc_list in face_encodings_db.items():
                for kenc in enc_list:
                    kvec = np.array(kenc, dtype=np.float32).reshape(-1)
                    if kvec.shape[0] != enc_len:
                        continue
                    if use_fr:
                        # Euclidean distance like face_recognition.face_distance
                        dist = np.linalg.norm(kvec - enc_vec)
                    else:
                        # Cosine distance on normalized embeddings (InsightFace produces normed)
                        denom = (np.linalg.norm(kvec) * np.linalg.norm(enc_vec) + 1e-6)
                        cos_sim = float(np.dot(kvec, enc_vec) / denom)
                        dist = 1.0 - cos_sim
                    if dist < best_dist:
                        best_dist = dist
                        best_name = name
            if best_name is not None and best_dist <= eff_tol:
                recognized.append(best_name)
                print(f"[FACES] Recognized {best_name} with distance {best_dist:.3f} (tolerance: {eff_tol:.3f})")
        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for n in recognized:
            if n not in seen:
                seen.add(n)
                ordered.append(n)
        return ordered
    except Exception as e:
        print(f"[FACES] Recognition error: {e}")
        return []

def recognize_faces_for_boxes(frame_bgr, person_boxes_xyxy, tolerance=0.6):
    """Return mapping index->name for given person boxes.
    person_boxes_xyxy: list of (x1,y1,x2,y2) in frame coords.
    """
    mapping = {}
    if DISABLE_FACE_RECOGNITION:
        return mapping
    if FACES_RUNTIME_DISABLED or not VISION_SETTINGS.get('faces', {}).get('enabled', True):
        return mapping
    if not face_encodings_db or not person_boxes_xyxy:
        return mapping
    try:
        for idx, box in enumerate(person_boxes_xyxy):
            x1, y1, x2, y2 = box
            x1i, y1i, x2i, y2i = map(lambda v: max(0, int(v)), [x1, y1, x2, y2])
            crop = frame_bgr[y1i:y2i, x1i:x2i]
            if crop.size == 0:
                continue
            # Upscale very small crops to help the encoder
            h, w = crop.shape[:2]
            if min(h, w) < 80:
                scale = 160.0 / max(1, min(h, w))
                crop = cv2.resize(crop, (max(1, int(w*scale)), max(1, int(h*scale))))
            encs = compute_face_encodings_from_image(crop)
            if not encs:
                continue
            enc_vec = np.array(encs[0], dtype=np.float32).reshape(-1)
            enc_len = enc_vec.shape[0]
            use_fr = (face_recognition is not None and enc_len == 128)
            # Adaptive threshold: if using cosine distance and default-ish tol, tighten it
            eff_tol = float(tolerance)
            if not use_fr and abs(eff_tol - 0.6) < 1e-6:
                eff_tol = 0.35
            best_name, best_dist = None, 1e9
            for name, enc_list in face_encodings_db.items():
                for kenc in enc_list:
                    kvec = np.array(kenc, dtype=np.float32).reshape(-1)
                    if kvec.shape[0] != enc_len:
                        continue
                    if use_fr:
                        dist = np.linalg.norm(kvec - enc_vec)
                    else:
                        denom = (np.linalg.norm(kvec) * np.linalg.norm(enc_vec) + 1e-6)
                        cos_sim = float(np.dot(kvec, enc_vec) / denom)
                        dist = 1.0 - cos_sim
                    if dist < best_dist:
                        best_dist = dist
                        best_name = name
            if best_name is not None and best_dist <= eff_tol:
                mapping[idx] = best_name
                print(f"[FACES] Box {idx}: Recognized {best_name} with distance {best_dist:.3f} (tolerance: {eff_tol:.3f})")
            elif best_name is not None:
                print(f"[FACES] Box {idx}: {best_name} distance {best_dist:.3f} exceeds tolerance {eff_tol:.3f}")
        return mapping
    except Exception as e:
        print(f"[FACES] Box recognition error: {e}")
        return mapping

def generate_thumbnail(video_filename, frame):
    """Generate a thumbnail from the first frame of the video"""
    try:
        # Create thumbnail filename
        base_name = os.path.splitext(video_filename)[0]
        thumbnail_filename = f"{base_name}_thumb.jpg"
        
        # Resize frame to thumbnail size (320x240)
        height, width = frame.shape[:2]
        aspect_ratio = width / height
        
        if aspect_ratio > 1.33:  # Wider than 4:3
            new_width = 320
            new_height = int(320 / aspect_ratio)
        else:  # Taller than 4:3
            new_height = 240
            new_width = int(240 * aspect_ratio)
        
        thumbnail = cv2.resize(frame, (new_width, new_height))
        
        # Add a border to make it exactly 320x240
        border_height = (240 - new_height) // 2
        border_width = (320 - new_width) // 2
        
        thumbnail = cv2.copyMakeBorder(
            thumbnail, 
            border_height, border_height, 
            border_width, border_width, 
            cv2.BORDER_CONSTANT, 
            value=[0, 0, 0]  # Black border
        )
        
        # Ensure it's exactly 320x240
        thumbnail = cv2.resize(thumbnail, (320, 240))
        
        # Save thumbnail
        cv2.imwrite(thumbnail_filename, thumbnail)
        
        return thumbnail_filename
    except Exception as e:
        print(f"[THUMBNAIL ERROR] Failed to generate thumbnail: {e}")
        return None

def format_clip_name(filename):
    """Convert clip filename to readable format"""
    try:
        # Extract timestamp from filename like "clip_20250909_143022pm.mp4"
        if filename.startswith("clip_") and (filename.endswith(".avi") or filename.endswith(".mp4")):
            timestamp_part = filename[5:-4]  # Remove "clip_" and ".avi" or ".mp4"
            # Parse the timestamp
            dt = datetime.strptime(timestamp_part, "%Y%m%d_%I%M%S%p")
            # Format as readable string
            return dt.strftime("%b %d, %Y at %I:%M %p")
        else:
            return filename
    except:
        return filename

# Global variables for frame sharing
current_frame = None
frame_lock = threading.Lock()
last_frame_time = 0
capture_session = None

def init_capture_session():
    """Initialize session for connection pooling"""
    global capture_session
    capture_session = requests.Session()
    capture_session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'image/jpeg,image/*,*/*',
        'Connection': 'keep-alive'
    })

def capture_frames_background():
    """Background thread to continuously capture frames"""
    global current_frame, last_frame_time, capture_session
    
    if capture_session is None:
        init_capture_session()
    
    print(f"[CAPTURE] Starting high-speed frame capture from ESP32...")
    
    consecutive_failures = 0
    frame_count = 0
    
    while True:
        try:
            # Get frame from ESP32 with shorter timeout
            resp = capture_session.get(CAMERAS["cam1"], timeout=1.5, stream=False)
            if resp.status_code == 200:
                # Convert to OpenCV image
                img_arr = np.frombuffer(resp.content, np.uint8)
                frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    with frame_lock:
                        current_frame = frame.copy()
                        last_frame_time = time.time()
                    
                    consecutive_failures = 0
                    frame_count += 1
                    
                    # Print status every 50 frames
                    if frame_count % 50 == 0:
                        print(f"[CAPTURE] Captured {frame_count} frames successfully")
                else:
                    consecutive_failures += 1
            else:
                consecutive_failures += 1
                
        except Exception as e:
            consecutive_failures += 1
            if consecutive_failures % 20 == 0:  # Print error every 20 failures
                print(f"[CAPTURE] Error (attempt {consecutive_failures}): {e}")
        
        # High-speed capture - 10 FPS
        time.sleep(0.1)

def get_frame(camera_url):
    """Get frame - now uses background captured frames"""
    try:
        if TEST_MODE or camera_url == "test":
            # Test mode - use test image only
            return create_test_image()
        elif ":8081" in camera_url:
            # Pi Zero MJPEG stream - get frame directly
            return get_mjpeg_frame(camera_url)
        else:
            # Use background captured frame for ESP32
            with frame_lock:
                if current_frame is not None and time.time() - last_frame_time < 10:
                    return current_frame.copy()
                else:
                    return None
    except Exception as e:
        print(f"[CAMERA ERROR] {e}")
        return None

def get_mjpeg_frame(mjpeg_url):
    """Get single frame from MJPEG stream - optimized for speed and reliability"""
    try:
        response = requests.get(mjpeg_url, timeout=3, stream=True)
        if response.status_code == 200:
            buffer = b''
            for chunk in response.iter_content(chunk_size=16384):  # Larger chunks for speed
                buffer += chunk
                if b'\xff\xd8' in buffer and b'\xff\xd9' in buffer:
                    start = buffer.find(b'\xff\xd8')
                    end = buffer.find(b'\xff\xd9', start) + 2
                    if end > start:
                        jpeg_data = buffer[start:end]
                        img_arr = np.frombuffer(jpeg_data, np.uint8)
                        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            return frame
                if len(buffer) > 200000:  # Prevent memory buildup
                    buffer = buffer[-100000:]  # Keep last 100KB
        return None
    except Exception as e:
        # Only print MJPEG errors occasionally to reduce log spam
        if not hasattr(get_mjpeg_frame, 'error_count'):
            get_mjpeg_frame.error_count = 0
        get_mjpeg_frame.error_count += 1
        if get_mjpeg_frame.error_count % 50 == 0:  # Print every 50th error
            print(f"[MJPEG ERROR] {e} (error #{get_mjpeg_frame.error_count})")
        return None

def gen_mjpeg_live_stream(cam_id, is_mobile):
    """Generate live MJPEG stream directly from Pi Zero with object detection"""
    try:
        camera_url = CAMERAS[cam_id]
        print(f"[{cam_id}] Starting MJPEG stream from Pi Zero at {camera_url}")
        
        response = requests.get(camera_url, timeout=5, stream=True)
        if response.status_code != 200:
            print(f"[{cam_id}] Failed to connect to Pi Zero camera: {response.status_code}")
            return
        
        print(f"[{cam_id}] Connected to Pi Zero successfully")
        
        buffer = b''
        frame_count = 0
        last_detection = 0
        frame_times = []
        last_face_check = 0
        faces_overlay_text = ""
        
        for chunk in response.iter_content(chunk_size=16384):
            buffer += chunk
            
            # Look for JPEG frame boundaries
            while b'\xff\xd8' in buffer and b'\xff\xd9' in buffer:
                start = buffer.find(b'\xff\xd8')
                end = buffer.find(b'\xff\xd9', start) + 2
                
                if end > start:
                    # Extract complete JPEG frame
                    jpeg_data = buffer[start:end]
                    buffer = buffer[end:]
                    
                    try:
                        # Decode JPEG to OpenCV frame
                        img_arr = np.frombuffer(jpeg_data, np.uint8)
                        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            # Fast path: optional lightweight mode (skip heavy detection most frames)
                            mode = request.args.get('mode', 'full') if request else 'full'
                            # Increase default detection interval to reduce CPU/GPU load.
                            detect_every = int(request.args.get('detect_every', 20)) if request else 20
                            do_detect = (mode == 'full') or ((mode == 'lite') and (frame_count % max(1, detect_every) == 0))

                            # Resize for mobile if needed
                            if is_mobile:
                                height, width = frame.shape[:2]
                                if width > 640:
                                    new_width = 640
                                    new_height = int((height * new_width) / width)
                                    frame = cv2.resize(frame, (new_width, new_height))
                            
                            # Check for camera tampering first
                            detect_camera_tampering(frame, cam_id)
                            
                            # Perform object detection with balanced confidence (gated for performance)
                            results = None
                            if do_detect:
                                results = live_model(frame, conf=0.5, verbose=False)
                            if results[0].boxes and time.time() - last_detection > COOLDOWN:
                                all_tags = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
                                boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes.xyxy is not None else None
                                filtered_list = filter_surveillance_objects(all_tags, boxes, min_area=10000)
                                tags = set(filtered_list)
                                if tags:
                                    # Try face recognition to append face:Name and optionally hide person
                                    try:
                                        person_boxes = []
                                        if boxes is not None and results[0].boxes is not None:
                                            cls_list = results[0].boxes.cls.tolist()
                                            for i, cls_idx in enumerate(cls_list):
                                                if model.names[int(cls_idx)] == 'person':
                                                    person_boxes.append(boxes[i])
                                        rec_names = recognize_faces_in_frame(frame, person_boxes)
                                        for n in rec_names:
                                            tags.add(f"face:{n}")
                                        if (
                                            rec_names
                                            and VISION_SETTINGS.get('faces', {}).get('hide_person_if_named', True)
                                            and 'person' in tags
                                        ):
                                            tags.discard('person')
                                    except Exception:
                                        pass
                                    print(f"[{cam_id}] MJPEG Stream - SURVEILLANCE DETECTED: {sorted(list(tags))}")
                                    
                                    # Perform intruder detection
                                    intruder_detected = detect_intruder_activity(filtered_list, boxes, cam_id)
                                    
                                    # Send notification for general detection if no specific intruder alert was sent
                                    if not intruder_detected:
                                        ist_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
                                        local_time = ist_time.strftime("%I:%M:%S %p")
                                        send_push_notification(
                                            title=f"FalconEye Alert ({cam_id})",
                                            body=f"Detected: {', '.join(sorted(list(tags)))} at {local_time}",
                                            detected_objects=sorted(list(tags))
                                        )
                                    last_detection = time.time()
                            
                            # Annotate frame with boxes and per-object labels (filtered)
                            annotated = frame.copy()
                            if results is not None and results[0].boxes:
                                boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes.xyxy is not None else []
                                clses = results[0].boxes.cls.tolist() if results[0].boxes.cls is not None else []
                                confs = results[0].boxes.conf.tolist() if results[0].boxes.conf is not None else []
                                names = [model.names[int(c)] for c in clses]
                                # Compute per-box face names if enabled
                                face_names_by_idx = {}
                                if VISION_SETTINGS.get('faces', {}).get('enabled', True):
                                    try:
                                        person_boxes = [boxes[i] for i, nm in enumerate(names) if nm == 'person']
                                        tol = float(VISION_SETTINGS.get('faces', {}).get('tolerance', 0.6))
                                        mapping = recognize_faces_for_boxes(frame, person_boxes, tolerance=tol)
                                        # Map back to full index space
                                        pi = 0
                                        for i, nm in enumerate(names):
                                            if nm == 'person':
                                                if pi in mapping:
                                                    face_names_by_idx[i] = mapping[pi]
                                                pi += 1
                                    except Exception:
                                        face_names_by_idx = {}
                                # Filter to surveillance objects but preserve index mapping
                                for i, name in enumerate(names):
                                    if name not in SURVEILLANCE_OBJECTS or not is_class_enabled(name):
                                        continue
                                    if i >= len(boxes):
                                        continue
                                    x1, y1, x2, y2 = boxes[i]
                                    color = class_color_bgr(name)
                                    if VISION_SETTINGS.get('show_boxes', True):
                                        cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                                    if VISION_SETTINGS.get('show_labels', True):
                                        if name == 'person' and i in face_names_by_idx:
                                            label_text = face_names_by_idx[i]
                                        else:
                                            label_text = f"{name} {(confs[i]*100):.0f}%" if i < len(confs) else name
                                        label = label_text
                                        # Background for text for readability
                                        (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5 if is_mobile else 0.6, 1 if is_mobile else 2)
                                        ty1 = max(int(y1) - th - 6, 0)
                                        cv2.rectangle(annotated, (int(x1), ty1), (int(x1)+tw+6, ty1+th+6), (0, 0, 0), -1)
                                        cv2.putText(annotated, label, (int(x1)+3, ty1+th+2), cv2.FONT_HERSHEY_SIMPLEX, 0.5 if is_mobile else 0.6, (255, 255, 255), 1 if is_mobile else 2)

                            # Faces overlay (sampled)
                            # Only run faces overlay sampling on frames where detection ran to avoid double work
                            if VISION_SETTINGS.get('faces', {}).get('enabled', True) and do_detect:
                                every = int(VISION_SETTINGS.get('faces', {}).get('sample_every', 10) or 10)
                                if frame_count % max(1, every) == 0:
                                    try:
                                        person_boxes = []
                                        if results and results[0].boxes is not None:
                                            bxyxy = results[0].boxes.xyxy.cpu().numpy()
                                            cl = results[0].boxes.cls.tolist()
                                            for i, ci in enumerate(cl):
                                                if model.names[int(ci)] == 'person':
                                                    person_boxes.append(bxyxy[i])
                                        tol = float(VISION_SETTINGS.get('faces', {}).get('tolerance', 0.6))
                                        # If no person boxes, skip to avoid scanning whole frame repeatedly
                                        names = []
                                        if person_boxes:
                                            names = recognize_faces_in_frame(frame, person_boxes, tolerance=tol)
                                        faces_overlay_text = ", ".join(names[:3]) if names else ""
                                    except Exception:
                                        faces_overlay_text = ""
                            
                            # Add camera info and FPS overlay
                            current_time = time.time()
                            frame_times.append(current_time)
                            if len(frame_times) > 30:  # Keep last 30 frames
                                frame_times.pop(0)
                            
                            font_scale = 0.6 if is_mobile else 0.8
                            thickness = 1 if is_mobile else 2
                            
                            if len(frame_times) > 1:
                                fps = len(frame_times) / (frame_times[-1] - frame_times[0])
                                fps_text = f"Pi Zero Live - FPS: {fps:.1f} - Frame: {frame_count}"
                            else:
                                fps_text = f"Pi Zero Live - Frame: {frame_count}"
                            
                            cv2.putText(annotated, fps_text, (10, 25), 
                                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                            cv2.putText(annotated, "FalconEye AI Detection", (10, 45), 
                                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                            
                            # Show filtered objects summary line
                            if results is not None and results[0].boxes and VISION_SETTINGS.get('show_summary', True):
                                all_objects = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
                                objects = filter_surveillance_objects(all_objects)
                                if objects:
                                    cv2.putText(annotated, f"Detected: {', '.join(objects)}", (10, 65),
                                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)
                            # Show faces overlay line
                            if faces_overlay_text and VISION_SETTINGS.get('faces', {}).get('overlay', True):
                                cv2.putText(annotated, f"Faces: {faces_overlay_text}", (10, 85),
                                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 200, 0), thickness)
                            
                            # Encode back to JPEG
                            quality = 70 if is_mobile else 85
                            _, buffer_encoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, quality])
                            frame_bytes = buffer_encoded.tobytes()
                            
                            # Send frame
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                            
                            frame_count += 1
                            if frame_count % 10 == 0:  # Print every 10th frame
                                print(f"[{cam_id}] Streamed {frame_count} frames")
                            
                    except Exception as e:
                        print(f"[{cam_id}] Error processing MJPEG frame: {e}")
                        continue
                        
    except Exception as e:
        print(f"[{cam_id}] MJPEG live stream error: {e}")
        # Return a placeholder frame
        placeholder = create_test_image()
        cv2.putText(placeholder, "Pi Zero Camera Offline", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, buffer = cv2.imencode('.jpg', placeholder)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def create_test_image():
    # Create a test image with some shapes for object detection
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (50, 50, 50)  # Dark gray background
    
    # Draw some rectangles and circles to simulate objects
    cv2.rectangle(img, (100, 100), (200, 200), (0, 255, 0), -1)  # Green rectangle
    cv2.circle(img, (400, 150), 50, (0, 0, 255), -1)  # Red circle
    cv2.rectangle(img, (300, 300), (500, 400), (255, 0, 0), -1)  # Blue rectangle
    
    # Add some text
    cv2.putText(img, "FalconEye Test Mode", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(img, "No camera connected", (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    
    return img

# --- Simple camera/test-mode helpers ---
@app.route("/camera/test-mode", methods=["GET", "POST"])
def camera_test_mode():
    global TEST_MODE
    if request.method == "POST":
        try:
            data = request.json or {}
            TEST_MODE = bool(data.get("enabled", False))
        except Exception:
            return jsonify({"status": "error", "message": "invalid payload"}), 400
    return jsonify({"test_mode": TEST_MODE})

@app.route("/camera/status", methods=["GET"])
def camera_status():
    status = {}
    for cam_id, url in CAMERAS.items():
        ok = _is_reachable(url)
        status[cam_id] = {"url": url, "reachable": ok}
    return jsonify({
        "test_mode": TEST_MODE,
        "active_profile": ACTIVE_PROFILE.get("name"),
        "status": status
    })

def upload_to_s3(file_path, object_name=None, tags=None):
    if object_name is None:
        object_name = os.path.basename(file_path)
    
    # Check if S3 client is available
    if s3 is None:
        print(f"[S3] S3 client not available - skipping upload for {file_path}")
        meta = load_metadata()
        filename = os.path.basename(file_path)
        if filename in meta:
            meta[filename]["uploaded_to_s3"] = False
            meta[filename]["s3_error"] = "AWS credentials not configured"
            save_metadata(meta)
        return
    
    try:
        s3.upload_file(file_path, AWS_BUCKET, object_name)
        if tags:
            meta_name = object_name.replace(".avi", ".json").replace(".mp4", ".json")
            tmp_meta = file_path.replace(".avi", ".json").replace(".mp4", ".json")
            with open(tmp_meta, "w") as f:
                json.dump({"tags": tags}, f)
            s3.upload_file(tmp_meta, AWS_BUCKET, meta_name)
        
        # Update metadata with upload status
        meta = load_metadata()
        filename = os.path.basename(file_path)
        if filename in meta:
            meta[filename]["uploaded_to_s3"] = True
            meta[filename]["s3_upload_time"] = datetime.now(timezone.utc).isoformat()
            save_metadata(meta)
        
        print(f"[S3] Uploaded {file_path}")
    except Exception as e:
        print(f"[S3 ERROR] {e}")
        
        # Update metadata with upload failure
        try:
            meta = load_metadata()
            filename = os.path.basename(file_path)
            if filename in meta:
                meta[filename]["uploaded_to_s3"] = False
            meta[filename]["s3_error"] = str(e)
            save_metadata(meta)
        except Exception as meta_error:
            print(f"[S3 ERROR] Failed to update metadata: {meta_error}")

def filter_surveillance_objects(detected_objects, boxes=None, min_area=5000):
    """Filter detected objects to only include home surveillance relevant ones"""
    # Respect user settings: enabled classes and min_area override
    eff_min_area = VISION_SETTINGS.get("min_area", min_area)
    if boxes is None:
        return [obj for obj in detected_objects if obj in SURVEILLANCE_OBJECTS and is_class_enabled(obj)]
    
    filtered_objects = []
    
    for i, obj in enumerate(detected_objects):
        if obj in SURVEILLANCE_OBJECTS:
            if boxes is not None and i < len(boxes):
                x1, y1, x2, y2 = boxes[i]
                area = (x2 - x1) * (y2 - y1)
                
                if area >= eff_min_area and is_class_enabled(obj):
                    filtered_objects.append(obj)
                else:
                    print(f"[{obj}] Box {i}: area={area:.0f} - TOO SMALL")
            else:
                # No boxes available, include the object
                if is_class_enabled(obj):
                    filtered_objects.append(obj)
    
    # Only print message if we had surveillance objects that were filtered out
    if not filtered_objects and detected_objects:
        surveillance_detected = [obj for obj in detected_objects if obj in SURVEILLANCE_OBJECTS]
        if surveillance_detected:
            print(f"[{surveillance_detected[0]}] ❌ No surveillance objects found after filtering")
        # Don't print anything for non-surveillance objects like airplane, scissors, toilet, etc.
    
    return filtered_objects

def detect_camera_tampering(frame, camera_id):
    """Detect if camera is being tampered with (covered/blocked)"""
    if not CAMERA_TAMPERING_ENABLED:
        return False
    
    current_time = time.time()
    
    # Convert frame to grayscale and calculate average brightness
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    avg_brightness = np.mean(gray)
    
    # Check if frame is too dark (camera covered)
    if avg_brightness < TAMPERING_THRESHOLD:
        if camera_id not in tampering_detection:
            tampering_detection[camera_id] = {
                'start_time': current_time,
                'alert_sent': False
            }
        else:
            # Check if we've been in tampering state long enough
            if (current_time - tampering_detection[camera_id]['start_time']) >= 5:  # 5 seconds of darkness
                if not tampering_detection[camera_id]['alert_sent']:
                    # Send tampering alert
                    ist_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
                    local_time = ist_time.strftime("%I:%M:%S %p")
                    
                    print(f"[{camera_id}] 🚨 CAMERA TAMPERING DETECTED! Average brightness: {avg_brightness:.1f}")
                    send_push_notification(
                        title=f"🚨 Camera Tampering Alert ({camera_id})",
                        body=f"Camera appears to be covered/blocked at {local_time}",
                        detected_objects=["tampering", "camera_blocked"]
                    )
                    
                    tampering_detection[camera_id]['alert_sent'] = True
                    tampering_detection[camera_id]['last_alert'] = current_time
                return True
    else:
        # Camera is working normally, reset tampering detection
        if camera_id in tampering_detection:
            del tampering_detection[camera_id]
    
    return False

def detect_intruder_activity(detected_objects, boxes, camera_id):
    """Enhanced intruder detection with time-based and behavioral analysis"""
    if not INTRUDER_DETECTION_ENABLED or not detected_objects:
        return False
    
    current_time = time.time()
    ist_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
    local_time = ist_time.strftime("%I:%M:%S %p")
    current_hour = ist_time.hour
    
    # Check if it's night time (more suspicious)
    is_night_time = current_hour >= NIGHT_TIME_START or current_hour < NIGHT_TIME_END
    
    intruder_detected = False
    alert_type = ""
    
    for i, obj in enumerate(detected_objects):
        if obj == "person" and i < len(boxes):
            x1, y1, x2, y2 = boxes[i]
            person_key = f"{camera_id}_person_{i}"
            
            # Start tracking if not already tracked
            if person_key not in person_detection_times:
                person_detection_times[person_key] = current_time
                person_positions[person_key] = []
            
            # Lingering detection
            if (current_time - person_detection_times[person_key]) >= LINGERING_THRESHOLD:
                if (camera_id, "lingering") not in intruder_alerts_sent or \
                   (current_time - intruder_alerts_sent[(camera_id, "lingering")]) >= TAMPERING_COOLDOWN:
                    alert_type = "LINGERING PERSON"
                    intruder_detected = True
                    intruder_alerts_sent[(camera_id, "lingering")] = current_time
                    print(f"[{camera_id}] 🚨 INTRUDER ALERT: {alert_type} detected at {local_time}")
                    send_push_notification(
                        title=f"🚨 Intruder Alert ({camera_id})",
                        body=f"{alert_type} detected at {local_time}",
                        detected_objects=["intruder", "lingering"]
                    )
            
            # Suspicious movement (simple heuristic: rapid change in position)
            person_positions[person_key].append((x1, y1, x2, y2, current_time))
            # Keep only recent positions for movement analysis
            person_positions[person_key] = [p for p in person_positions[person_key] if current_time - p[4] < 5] # Last 5 seconds
            
            if len(person_positions[person_key]) > 2:
                # Calculate average movement speed/distance
                first_pos = person_positions[person_key][0]
                last_pos = person_positions[person_key][-1]
                
                # Simple distance metric (center point movement)
                center_x_first = (first_pos[0] + first_pos[2]) / 2
                center_y_first = (first_pos[1] + first_pos[3]) / 2
                center_x_last = (last_pos[0] + last_pos[2]) / 2
                center_y_last = (last_pos[1] + last_pos[3]) / 2
                
                movement_distance = ((center_x_last - center_x_first)**2 + (center_y_last - center_y_first)**2)**0.5
                time_diff = last_pos[4] - first_pos[4]
                
                if time_diff > 0 and (movement_distance / time_diff) > SUSPICIOUS_MOVEMENT_THRESHOLD:
                    if (camera_id, "suspicious_movement") not in intruder_alerts_sent or \
                       (current_time - intruder_alerts_sent[(camera_id, "suspicious_movement")]) >= TAMPERING_COOLDOWN:
                        alert_type = "SUSPICIOUS MOVEMENT"
                        intruder_detected = True
                        intruder_alerts_sent[(camera_id, "suspicious_movement")] = current_time
                        print(f"[{camera_id}] 🚨 INTRUDER ALERT: {alert_type} detected at {local_time}")
                        send_push_notification(
                            title=f"🚨 Intruder Alert ({camera_id})",
                            body=f"{alert_type} detected at {local_time}",
                            detected_objects=["intruder", "movement"]
                        )
            
            # Night time detection
            if is_night_time:
                if (camera_id, "night_intruder") not in intruder_alerts_sent or \
                   (current_time - intruder_alerts_sent[(camera_id, "night_intruder")]) >= TAMPERING_COOLDOWN:
                    alert_type = "NIGHT INTRUDER"
                    intruder_detected = True
                    intruder_alerts_sent[(camera_id, "night_intruder")] = current_time
                    print(f"[{camera_id}] 🚨 INTRUDER ALERT: {alert_type} detected at {local_time}")
                    send_push_notification(
                        title=f"🚨 Night Intruder Alert ({camera_id})",
                        body=f"{alert_type} detected at {local_time}",
                        detected_objects=["intruder", "night"]
                    )
    
    # Clean up old person tracking data
    for key in list(person_detection_times.keys()):
        if current_time - person_detection_times[key] > LINGERING_THRESHOLD * 2: # Clear after double the lingering threshold
            del person_detection_times[key]
            if key in person_positions:
                del person_positions[key]
    
    return intruder_detected

# Removed Firebase access token function - using local notifications now

def send_simple_notification(title, body, detected_objects=None):
    """Send simple notification to all registered device tokens"""
    print(f"[NOTIFICATION] Sending to devices: {title}")
    
    # Use the new notification service
    success = send_push_notification(title, body, detected_objects=detected_objects)
    
    if success:
        print(f"[NOTIFICATION] ✅ Notification sent successfully")
    else:
        print(f"[NOTIFICATION] ❌ Failed to send notification")

def send_push_notification_legacy(title, body, token=None, detected_objects=None):
    """Legacy FCM function - now uses new notification service"""
    print(f"[NOTIFICATION] Using new notification service: {title}")
    
    # Use the new notification service
    success = send_push_notification(title, body, token, detected_objects)
    
    if success:
        print(f"[NOTIFICATION] ✅ Notification sent successfully")
    else:
        print(f"[NOTIFICATION] ❌ Failed to send notification")

def register_fcm_token(token):
    """Register a new device token for local notifications"""
    # Use the local notification service
    success = notification_service.register_device(token)
    
    # Also add to legacy set for backward compatibility
    registered_tokens.add(token)
    
    if success:
        print(f"[LOCAL] ✅ Registered device: {token[:20]}...")
    else:
        print(f"[LOCAL] ❌ Failed to register device: {token[:20]}...")
    return {"status": "success", "message": "Device registered"}

def unregister_fcm_token(token):
    """Unregister a device token"""
    # Use the local notification service
    success = notification_service.unregister_device(token)
    
    # Also remove from legacy set for backward compatibility
    registered_tokens.discard(token)
    
    if success:
        print(f"[LOCAL] ✅ Unregistered device: {token[:20]}...")
        return {"status": "success", "message": "Device unregistered"}
    else:
        print(f"[LOCAL] ❌ Failed to unregister device: {token[:20]}...")
        return {"status": "error", "message": "Failed to unregister device"}

def register_device_token_simple(token):
    """Register a device token for simple APNs notifications"""
    registered_tokens.add(token)
    print(f"[DEVICE] Registered APNs token: {token[:20]}...")
    return {"status": "success", "message": "Device token registered"}

# ---------------- Recording ----------------
def record_clip(camera_id, camera_url, tags=None, duration=CLIP_DURATION):
    # Create filename with IST timestamp in 12-hour format
    ist_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
    timestamp_str = ist_time.strftime("%Y%m%d_%I%M%S%p").lower()
    filename = os.path.join(OUTPUT_DIR, f"clip_{timestamp_str}.mp4")

    print(f"[RECORD] Starting {duration}s recording for {camera_id}...")
    
    # Initialize video writer
    out = None
    frames_captured = 0
    start_time = time.time()
    all_tags = set(tags or [])
    
    # Use a dedicated stream for recording to avoid conflicts with live view
    # For MJPEG, we need to continuously read from the stream
    if camera_id == "cam2": # Pi Zero MJPEG stream
        try:
            # Tuple timeout: (connect, read)
            stream_response = requests.get(camera_url, stream=True, timeout=(3, 3))
        except Exception as e:
            print(f"[RECORD ERROR] Failed to open Pi Zero stream: {e}")
            return None
        if stream_response.status_code != 200:
            print(f"[RECORD ERROR] Failed to connect to Pi Zero stream for recording: {camera_url}")
            try:
                stream_response.close()
            except Exception:
                pass
            return None

        bytes_buffer = b''
        last_data_time = time.time()
        try:
            for chunk in stream_response.iter_content(chunk_size=16384):
                # Handle stalls: empty chunk or no progress
                if not chunk:
                    if time.time() - last_data_time > 2.0:
                        print("[RECORD WARNING] MJPEG stalled >2s, ending clip early.")
                        break
                    continue
                last_data_time = time.time()
                bytes_buffer += chunk
                a = bytes_buffer.find(b'\xff\xd8') # Start of JPEG
                b = bytes_buffer.find(b'\xff\xd9') # End of JPEG
                
                if a != -1 and b != -1:
                    jpeg_data = bytes_buffer[a:b+2]
                    bytes_buffer = bytes_buffer[b+2:]
                    
                    img_arr = np.frombuffer(jpeg_data, np.uint8)
                    frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        if out is None:
                            height, width, _ = frame.shape
                            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                            out = cv2.VideoWriter(filename, fourcc, FPS, (width, height))
                            if not out.isOpened():
                                print(f"[RECORD ERROR] Could not open video writer for {filename}")
                                return None
                        
                        # Perform object detection; annotate only filtered tags
                        results = model(frame, conf=0.9, verbose=False)
                        annotated = frame.copy()
                        if results[0].boxes:
                            frame_tags = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
                            boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes.xyxy is not None else None
                            # Filter for surveillance objects only with size constraints
                            filtered_tags = filter_surveillance_objects(frame_tags, boxes, min_area=1000)
                            all_tags.update(filtered_tags)
                        
                        out.write(annotated)
                        frames_captured += 1
                        
                        if time.time() - start_time > duration:
                            break
                    else:
                        print(f"[RECORD WARNING] Failed to decode frame from Pi Zero stream during recording.")
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
            print(f"[RECORD WARNING] MJPEG read interrupted: {e}")
        finally:
            try:
                stream_response.close()
            except Exception:
                pass
    else: # ESP32 camera (or other non-MJPEG)
        while time.time() - start_time < duration:
            frame = get_frame(camera_url)
            if frame is None:
                print(f"[RECORD WARNING] Failed to get frame from {camera_id} during recording.")
                time.sleep(0.1) # Avoid busy-waiting
                continue
            
            if out is None:
                height, width, _ = frame.shape
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(filename, fourcc, FPS, (width, height))
                if not out.isOpened():
                    print(f"[RECORD ERROR] Could not open video writer for {filename}")
                    return None
            
            # Perform object detection; annotate only filtered tags
            results = model(frame, conf=0.9, verbose=False)
            annotated = frame.copy()
            if results[0].boxes:
                frame_tags = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
                boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes.xyxy is not None else None
                # Filter for surveillance objects only with size constraints
                filtered_tags = filter_surveillance_objects(frame_tags, boxes, min_area=1000)
                all_tags.update(filtered_tags)
            
            out.write(annotated)
            frames_captured += 1

    if out is not None:
        out.release()

    if frames_captured > 0:
        print(f"[RECORD] Captured {frames_captured} frames successfully for {camera_id}.")
        # Save metadata
        meta = load_metadata()
        meta[os.path.basename(filename)] = {
            "id": timestamp_str,
            "camera": camera_id,
            "tags": list(all_tags),
            "timestamp": ist_time.isoformat(),
            "duration": duration
        }
        save_metadata(meta)

        # Generate thumbnail
        thumbnail_filename = generate_thumbnail(filename, frame)
        if thumbnail_filename:
            print(f"[THUMBNAIL] Generated thumbnail: {thumbnail_filename}")

        # Start S3 upload in a separate thread
        try:
            from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
            aws_configured = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_ACCESS_KEY_ID != "your_access_key_here")
        except ImportError:
            aws_configured = bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))
        
        if aws_configured:
            threading.Thread(target=upload_to_s3, args=(filename,)).start()
        else:
            print("[S3] AWS S3 not configured, skipping upload.")
        
        return filename
    else:
        print(f"[RECORD ERROR] No frames captured for {camera_id}.")
        return None

# Replace detect_and_record with this
def detect_and_record(camera_id, camera_url):
    last_detection = 0
    frame_count = 0
    camera_type = "Pi Zero MJPEG" if ":8081" in camera_url else "ESP32"
    
    print(f"[{camera_id}] Starting detection loop with {camera_type} camera at {camera_url}")
    
    while True:
        frame = get_frame(camera_url)
        if frame is None:
            time.sleep(0.5)
            continue
        
        frame_count += 1
        
        # Print status every 50 frames
        if frame_count % 50 == 0:
            print(f"[{camera_id}] Processing frame {frame_count} - {camera_type} camera working")
        
        # Check for camera tampering first
        detect_camera_tampering(frame, camera_id)
        
        # Perform object detection on raw frame (no compression)
        results = model(frame, conf=0.5, verbose=False)
        if results[0].boxes and time.time() - last_detection > COOLDOWN:
            all_tags = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
            boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes.xyxy is not None else None
            
            # Filter for surveillance objects only with size constraints
            filtered_list = filter_surveillance_objects(all_tags, boxes, min_area=500)  # Lowered min_area
            tags = set(filtered_list)
            
            # Only proceed if we have relevant surveillance objects
            if tags:
                print(f"[{camera_id}] ✅ SURVEILLANCE DETECTED: {sorted(list(tags))}")
                if boxes is not None:
                    for i, box in enumerate(boxes):
                        x1, y1, x2, y2 = box
                        area = (x2 - x1) * (y2 - y1)
                        # Only print box info for surveillance objects
                        if all_tags[i] in SURVEILLANCE_OBJECTS:
                            print(f"[{camera_id}] Box {i}: area={area:.0f}, coords=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})")
                
                # Only proceed if we have relevant surveillance objects
                if tags:
                    # Face recognition for people
                    person_boxes = []
                    try:
                        if boxes is not None and results[0].boxes is not None:
                            cls_list = results[0].boxes.cls.tolist()
                            for i, cls_idx in enumerate(cls_list):
                                if model.names[int(cls_idx)] == 'person':
                                    person_boxes.append(boxes[i])
                    except Exception:
                        person_boxes = []
                    recognized_names = recognize_faces_in_frame(frame, person_boxes)
                    if recognized_names:
                        for n in recognized_names:
                            tags.add(f"face:{n}")
                        # Hide generic person if any known face is present and setting enabled
                        if VISION_SETTINGS.get('faces', {}).get('hide_person_if_named', True) and 'person' in tags:
                            tags.discard('person')
                        print(f"[{camera_id}] 👤 Recognized: {recognized_names}")
                    print(f"[{camera_id}] ✅ TRIGGERING RECORDING! Detected: {sorted(list(tags))}")
                    last_detection = time.time()
                    
                    # Perform intruder detection
                    intruder_detected = detect_intruder_activity(filtered_list, boxes, camera_id)
                    
                    # Send notification for general detection if no specific intruder alert was sent
                    if not intruder_detected:
                        ist_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
                        local_time = ist_time.strftime("%I:%M:%S %p")
                        send_push_notification(
                            title=f"FalconEye Alert ({camera_id})",
                            body=f"Detected: {', '.join(sorted(list(tags)))} at {local_time}",
                            detected_objects=sorted(list(tags))
                        )
                    
                    # Record clip with 15-second duration (guard against overlap)
                    start_recording_if_idle(camera_id, camera_url, sorted(list(tags)), CLIP_DURATION)

                    # Persist last detections for dashboards
                    recent_detections.append({
                        "camera": camera_id,
                        "tags": sorted(list(tags)),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                    # Push notification to all registered devices
                    local_time = datetime.now().strftime('%I:%M:%S %p')
                    send_push_notification(
                        title=f"FalconEye Alert ({camera_id})",
                        body=f"Detected: {', '.join(sorted(list(tags)))} at {local_time}",
                        detected_objects=sorted(list(tags))
                    )
            # Don't print anything for non-surveillance objects - they are completely ignored
        
        # Check for new frames every 0.5 seconds
        time.sleep(0.5)


# ---------------- Local Preview ----------------
def local_preview(camera_id, camera_url):
    while True:
        frame = get_frame(camera_url)
        if frame is None:
            continue
        results = model(frame, conf=0.9, verbose=False)
        annotated = results[0].plot()
        cv2.imshow(f"FalconEye - {camera_id}", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()

# Load faces DB at startup
load_face_db()
load_vision_settings()

# ---------------- Dashboard ----------------
dashboard_html = """
<!DOCTYPE html>
<html>
<head>
    <title>FalconEye Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <!-- Version: 2025-09-11-21:25 - ASPECT RATIO FIXED - object-fit: contain -->
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * { 
            box-sizing: border-box; 
            margin: 0;
            padding: 0;
        }
        
        body { 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: var(--bg-primary);
            color: var(--text-primary); 
            margin: 0; 
            padding: 0; 
            overflow-x: hidden;
            min-height: 100vh;
            position: relative;
            transition: background-color 0.3s ease, color 0.3s ease;
            -webkit-text-size-adjust: 100%;
        }
        
        /* Animated background particles */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(15, 157, 88, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(33, 150, 243, 0.05) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(156, 39, 176, 0.05) 0%, transparent 50%);
            animation: backgroundShift 30s ease-in-out infinite;
            z-index: -1;
        }
        
        @keyframes backgroundShift {
            0%, 100% { transform: translateX(0) translateY(0); }
            25% { transform: translateX(-30px) translateY(-15px); }
            50% { transform: translateX(30px) translateY(15px); }
            75% { transform: translateX(-15px) translateY(30px); }
        }
        header { 
            background: var(--accent-primary);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border-color);
            padding: 20px; 
            position: sticky; 
            top: 0; 
            z-index: 100;
            box-shadow: 
                0 8px 32px var(--shadow-light),
                0 0 0 1px var(--glass-border),
                inset 0 1px 0 var(--glass-border);
            width: 100%;
            text-align: center;
            animation: slideDown 0.6s ease-out;
        }
        
        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .header-content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 24px;
            width: 100%;
            margin: 0 auto;
            position: relative;
        }
        
        .app-logo {
            width: 60px;
            height: 60px;
            border-radius: 16px;
            box-shadow: 
                0 8px 32px rgba(0, 0, 0, 0.3);
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: transparent;
            border: none;
            font-size: 28px;
            transition: all 0.3s ease;
            animation: logoFloat 3s ease-in-out infinite;
            overflow: hidden;
        }
        
        .app-logo:hover {
            transform: scale(1.05);
            box-shadow: 
                0 12px 40px rgba(0, 0, 0, 0.4);
        }
        
        @keyframes logoFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-3px); }
        }
        
        .app-logo img {
            width: 100%;
            height: 100%;
            border-radius: 14px;
            object-fit: contain;
            display: block;
            background: transparent;
            transition: all 0.3s ease;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3)) 
                    drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2))
                    brightness(1.1) 
                    contrast(1.05);
            border: none;
            outline: none;
        }
        
        .app-logo img:hover {
            transform: scale(1.05) rotate(2deg);
            filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.4)) 
                    drop-shadow(0 3px 6px rgba(0, 0, 0, 0.3))
                    brightness(1.2) 
                    contrast(1.1);
            animation: logoGlow 2s ease-in-out infinite alternate;
        }
        
        @keyframes logoGlow {
            0% {
                filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.4)) 
                        drop-shadow(0 3px 6px rgba(0, 0, 0, 0.3))
                        brightness(1.2) 
                        contrast(1.1);
            }
            100% {
                filter: drop-shadow(0 8px 16px rgba(15, 157, 88, 0.6)) 
                        drop-shadow(0 4px 8px rgba(15, 157, 88, 0.4))
                        brightness(1.3) 
                        contrast(1.15);
            }
        }
        
        /* Logo theme switching animation */
        .app-logo img.theme-switching {
            animation: themeSwitch 0.6s ease-in-out;
        }
        
        @keyframes themeSwitch {
            0% {
                transform: scale(1) rotate(0deg);
                opacity: 1;
            }
            50% {
                transform: scale(0.8) rotate(180deg);
                opacity: 0.7;
            }
            100% {
                transform: scale(1) rotate(360deg);
                opacity: 1;
            }
        }
        
        .header-text {
            text-align: center;
            color: #fff;
        }
        
        .header-text h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 700;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            background: linear-gradient(135deg, #fff, #e8f5e8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }
        
        .header-text p {
            margin: 6px 0 0 0;
            font-size: 15px;
            opacity: 0.9;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.8);
        }
        
        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-left: auto;
        }
        
        .logout-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 20px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
            color: white;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(20px);
            position: relative;
            overflow: hidden;
        }
        
        .logout-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }
        
        .logout-btn:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        }
        
        .logout-btn:hover::before {
            left: 100%;
        }
        
        .logout-icon {
            font-size: 16px;
        }
        
        .logout-text {
            font-size: 13px;
        }
        .container { 
            padding: 20px; 
            max-width: 100%; 
            animation: fadeInUp 0.8s ease-out;
            background: var(--bg-primary);
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        h2 { 
            color: var(--accent-primary); 
            margin: 20px 0 15px 0; 
            font-size: 22px; 
            font-weight: 600;
            text-shadow: 0 2px 4px var(--shadow-light);
            letter-spacing: -0.3px;
        }
        
        .section { 
            margin: 25px 0; 
            background: var(--glass-bg);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(10px);
        }
        
        /* Enhanced camera feeds */
        .camera-feed {
            background: var(--bg-tertiary);
            border-radius: 16px;
            overflow: hidden;
            position: relative;
            box-shadow: 
                0 8px 32px var(--shadow-light),
                0 0 0 1px var(--glass-border);
            transition: all 0.3s ease;
            animation: slideInUp 0.6s ease-out;
            aspect-ratio: 16/9; /* Maintain 16:9 aspect ratio */
            height: 400px; /* Reduced height to prevent black bars */
            width: 100%;
            flex: 1;
            max-width: 100%;
        }
        
        .camera-content {
            height: 360px; /* Fixed height to match camera feed minus header */
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .camera-content img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        
        .cctv-grid {
            display: flex;
            gap: 20px;
            width: 100%;
            position: relative;
            margin-bottom: 20px;
        }
        
        .camera-feed {
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            position: relative;
            box-shadow: 
                0 8px 32px var(--shadow-light),
                0 0 0 1px var(--glass-border);
            transition: all 0.3s ease;
            animation: slideInUp 0.6s ease-out;
            aspect-ratio: 16/9;
            height: 400px;
            width: 100%;
            flex: 1;
            max-width: 100%;
        }
        
        .camera-header {
            background: linear-gradient(135deg, #0f9d58, #0a7d47);
            padding: 12px 16px;
            color: white;
            font-weight: 500;
            font-size: 14px;
            display: flex;
            align-items: center;
        }
        
        .camera-content {
            height: calc(100% - 48px);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }
        
        .camera-content img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        
        .camera-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
        }
        
        .camera-status {
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0,0,0,0.7);
            color: #0f9d58;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .camera-controls {
            position: absolute;
            bottom: 10px;
            left: 10px;
            right: 10px;
            display: flex;
            gap: 8px;
            z-index: 30;
            pointer-events: auto;
            background: rgba(0,0,0,0.8);
            padding: 8px;
            border-radius: 8px;
        }
        
        .control-btn {
            background: rgba(0,0,0,0.8);
            border: 1px solid #0f9d58;
            color: #0f9d58;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }
        
        .control-btn:hover {
            background: rgba(15, 157, 88, 0.1);
            border-color: #0f9d58;
        }
        
        .control-btn svg {
            flex-shrink: 0;
        }
        
        .control-btn span {
            white-space: nowrap;
        }
        
        /* Hide text on smaller screens, show only icons */
        @media (max-width: 1600px) {
            .control-btn span {
                display: none !important;
            }
            
            .control-btn {
                padding: 8px !important;
                min-width: 40px !important;
                justify-content: center !important;
            }
        }
        
        
        /* Mobile responsive for live page */
        @media (max-width: 768px) {
            .cctv-grid {
                flex-direction: column !important;
                height: auto !important;
                gap: 15px !important;
                padding: 0 10px !important;
            }
            
            .camera-feed {
                height: 250px !important;
                min-height: 250px !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
                width: 100% !important;
                margin: 0 !important;
            }
            
            .camera-content {
                height: 210px !important;
            }
            
            
            .camera-content img {
                width: 100% !important;
                height: 100% !important;
                object-fit: cover !important;
                border-radius: 8px !important;
            }
            
            .camera-overlay {
                border-radius: 8px !important;
            }
            
            .camera-status {
                font-size: 11px !important;
                padding: 3px 6px !important;
                border-radius: 6px !important;
            }
            
            .camera-controls {
                position: absolute !important;
                bottom: 8px !important;
                left: 8px !important;
                right: 8px !important;
                background: rgba(0, 0, 0, 0.85) !important;
                border-radius: 8px !important;
                padding: 6px !important;
                display: flex !important;
                gap: 6px !important;
                justify-content: space-between !important;
            }
            
            .control-btn {
                padding: 6px !important;
                font-size: 11px !important;
                min-height: 32px !important;
                min-width: 32px !important;
                flex: 1 !important;
                border-radius: 6px !important;
                justify-content: center !important;
            }
            
            .control-btn span {
                display: none !important;
            }
        }
        
        @media (max-width: 480px) {
            .cctv-grid {
                gap: 12px !important;
                padding: 0 8px !important;
            }
            
            .camera-feed {
                height: 220px !important;
                min-height: 220px !important;
                padding-bottom: 50px !important;
            }
            
            .camera-header {
                font-size: 12px !important;
                padding: 5px 8px !important;
            }
            
            .camera-content {
                height: 170px !important;
            }
            
            .camera-controls {
                position: absolute !important;
                bottom: 6px !important;
                left: 6px !important;
                right: 6px !important;
                display: flex !important;
                gap: 4px !important;
                background: rgba(0, 0, 0, 0.9) !important;
                padding: 4px !important;
                border-radius: 6px !important;
                z-index: 50 !important;
            }
            
            .control-btn {
                padding: 4px !important;
                font-size: 9px !important;
                flex: 1 !important;
                min-height: 28px !important;
                min-width: 28px !important;
                border-radius: 4px !important;
                justify-content: center !important;
            }
            
            .control-btn span {
                display: none !important;
            }
            
            .control-btn svg {
                margin: 0 !important;
                width: 14px !important;
                height: 14px !important;
            }
            
            /* Ensure controls are always visible in portrait */
            .camera-content {
                padding-bottom: 60px !important;
            }
        }
        
        /* Portrait mode specific fixes */
        @media (max-width: 480px) and (orientation: portrait) {
            .camera-feed {
                height: 320px !important;
                min-height: 320px !important;
            }
            
            .camera-controls {
                position: sticky !important;
                bottom: 0 !important;
                margin-top: 10px !important;
                position: relative !important;
                background: rgba(0, 0, 0, 0.9) !important;
                border-radius: 12px !important;
            }
            
            .control-btn {
                padding: 10px 8px !important;
                font-size: 12px !important;
                min-height: 40px !important;
            }
            
            /* Hide text on very small screens, show only icons */
            .control-btn span {
                display: none !important;
            }
            
            .control-btn svg {
                margin: 0 !important;
            }
        }
        
        /* Show text on slightly larger mobile screens */
        @media (max-width: 480px) and (min-width: 360px) {
            .control-btn span {
                display: inline !important;
            }
        }
        
        .cctv-grid > * {
            position: relative !important;
            z-index: 1 !important;
        }
        
        .camera-feed:hover {
            transform: translateY(-4px);
            box-shadow: 
                0 12px 40px rgba(0, 0, 0, 0.5),
                0 0 0 1px rgba(255, 255, 255, 0.1);
        }
        
        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .camera-header {
            background: linear-gradient(135deg, #0f9d58, #0a7d47);
            padding: 12px 16px;
            color: white;
            font-weight: 600;
            font-size: 15px;
            position: relative;
            overflow: hidden;
        }
        
        .camera-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        /* Mobile-optimized video and images */
        video, img { 
            border: none;
            border-radius: 0;
            max-width: 100%; 
            height: auto; 
            display: block; 
            margin: 0 auto;
            transition: all 0.3s ease;
        }
        
        /* Responsive grid for clips */
        .clips { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-top: 20px;
        }
        
        .clip-card { 
            background: var(--bg-secondary);
            padding: 16px; 
            border-radius: 16px; 
            box-shadow: 
                0 4px 20px var(--shadow-light),
                0 0 0 1px var(--glass-border);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        .clip-card:hover { 
            transform: translateY(-4px);
            box-shadow: 
                0 8px 30px var(--shadow-medium),
                0 0 0 1px var(--accent-primary);
        }
        
        /* Enhanced controls */
        .controls {
            display: flex; 
            flex-wrap: wrap; 
            gap: 12px; 
            margin: 20px 0; 
            align-items: center;
        }
        
        select { 
            padding: 12px 16px; 
            border-radius: 12px; 
            background: var(--bg-secondary);
            color: var(--text-primary); 
            border: 1px solid var(--border-color);
            font-size: 14px; 
            min-width: 140px;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }
        
        select:hover {
            background: var(--bg-tertiary);
            border-color: var(--accent-primary);
        }
        
        select:focus {
            outline: none;
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 2px var(--accent-primary);
        }
        
        button {
            padding: 12px 20px; 
            border-radius: 12px; 
            background: var(--accent-primary);
            color: white; 
            border: none;
            font-size: 14px; 
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(15, 157, 88, 0.3);
        }
        
        button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }
        
        button:hover { 
            background: var(--accent-secondary);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px var(--shadow-medium);
        }
        
        button:hover::before {
            left: 100%;
        }
        
        button:active { 
            transform: scale(0.98);
        }
        
        /* Enhanced status indicators */
        .status-indicator {
            display: inline-block; 
            width: 10px; 
            height: 10px; 
            border-radius: 50%; 
            margin-right: 10px;
            position: relative;
            animation: pulse 2s infinite;
        }
        
        .status-online { 
            background: var(--accent-primary);
            box-shadow: 0 0 10px var(--accent-primary);
        }
        
        .status-offline { 
            background: var(--accent-red);
            box-shadow: 0 0 10px var(--accent-red);
        }
        
        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.1); opacity: 0.7; }
            100% { transform: scale(1); opacity: 1; }
        }
        
        /* Upload status badges */
        .clip-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }
        .upload-status {
            flex-shrink: 0;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-badge.uploaded {
            background: #0f9d58;
            color: white;
        }
        .status-badge.failed {
            background: #f44336;
            color: white;
        }
        .status-badge.pending {
            background: #ff9800;
            color: white;
        }
        .status-badge.not-configured {
            background: #9e9e9e;
            color: white;
        }
        
        /* Theme toggle - removed conflicting styles */
        
        /* Enhanced Theme System */
        :root {
            /* Dark theme (default) */
            --bg-primary: #0c0c0c;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #222;
            --text-primary: #eee;
            --text-secondary: #ccc;
            --text-muted: #999;
            --accent-primary: #0f9d58;
            --accent-secondary: #0a7d47;
            --accent-blue: #2196f3;
            --accent-red: #f44336;
            --border-color: rgba(255, 255, 255, 0.1);
            --shadow-light: rgba(0, 0, 0, 0.3);
            --shadow-medium: rgba(0, 0, 0, 0.5);
            --shadow-heavy: rgba(0, 0, 0, 0.7);
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
        }
        
        /* Light theme variables */
        body.light-theme {
            --bg-primary: #f8f9fa;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f3f4;
            --text-primary: #1a1a1a;
            --text-secondary: #4a4a4a;
            --text-muted: #6c757d;
            --accent-primary: #0f9d58;
            --accent-secondary: #0a7d47;
            --accent-blue: #1976d2;
            --accent-red: #d32f2f;
            --border-color: rgba(0, 0, 0, 0.1);
            --shadow-light: rgba(0, 0, 0, 0.1);
            --shadow-medium: rgba(0, 0, 0, 0.15);
            --shadow-heavy: rgba(0, 0, 0, 0.25);
            --glass-bg: rgba(255, 255, 255, 0.8);
            --glass-border: rgba(0, 0, 0, 0.1);
        }
        
        /* Apply theme variables */
        body {
            background: var(--bg-primary);
            color: var(--text-primary);
        }
        
        /* Theme Settings Styles */
        .theme-options {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin: 16px 0;
        }
        
        .theme-option {
            cursor: pointer;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            background: var(--bg-secondary);
            transition: all 0.3s ease;
            position: relative;
        }
        
        .theme-option:hover {
            border-color: var(--accent-primary);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px var(--shadow-medium);
        }
        
        .theme-option.selected {
            border-color: var(--accent-primary);
            background: var(--accent-primary);
            color: white;
        }
        
        .theme-option.selected .theme-label {
            color: white;
        }
        
        .theme-option.selected .theme-description {
            color: rgba(255, 255, 255, 0.8);
        }
        
        .theme-preview {
            width: 100%;
            height: 80px;
            border-radius: 8px;
            margin-bottom: 12px;
            position: relative;
            overflow: hidden;
        }
        
        .dark-preview {
            background: #1a1a1a;
        }
        
        .light-preview {
            background: #f8f9fa;
        }
        
        .theme-header {
            height: 20px;
            background: var(--accent-primary);
            margin-bottom: 8px;
        }
        
        .theme-content {
            padding: 0 8px;
        }
        
        .theme-card {
            height: 12px;
            background: var(--bg-secondary);
            margin-bottom: 6px;
            border-radius: 4px;
        }
        
        .theme-card:last-child {
            margin-bottom: 0;
        }
        
        .theme-label {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 4px;
            color: var(--text-primary);
        }
        
        .theme-description {
            font-size: 14px;
            color: var(--text-muted);
            line-height: 1.4;
        }
        
        @media (max-width: 768px) {
            .theme-options {
                grid-template-columns: 1fr;
                gap: 12px;
            }
        }
        
        
        /* Live Stream Enhancements */
        .stream-container {
            position: relative;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        
        
        .stream-btn {
            background: rgba(0,0,0,0.7);
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .stream-btn:hover {
            background: rgba(0,0,0,0.9);
            transform: scale(1.1);
        }
        
        .detection-tags .badge {
            background: rgba(15, 157, 88, 0.9);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .action-btn {
            background: #222;
            border: none;
            border-radius: 12px;
            padding: 15px 10px;
            color: white;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }
        .action-btn:hover {
            background: #333;
            transform: translateY(-2px);
        }
        
        .action-icon {
            font-size: 24px;
        }
        
        .action-icon svg {
            vertical-align: middle;
        }
        
        .action-text {
            font-size: 12px;
            font-weight: 500;
        }
        
        /* Enhanced navigation */
        .nav-tabs {
            display: flex; 
            background: var(--glass-bg);
            border-radius: 16px; 
            margin: 20px 0; 
            overflow: hidden;
            padding: 4px;
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(10px);
        }
        
        .nav-tab {
            flex: 1; 
            padding: 14px 16px; 
            text-align: center; 
            background: transparent; 
            color: #aaa; 
            border: none;
            cursor: pointer; 
            transition: all 0.3s ease;
            border-radius: 12px;
            font-weight: 500;
            font-size: 14px;
            position: relative;
            overflow: hidden;
        }
        
        .nav-tab::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            transition: left 0.5s;
        }
        
        .nav-tab:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
        }
        
        .nav-tab:hover::before {
            left: 100%;
        }
        
        .nav-tab.active { 
            background: var(--accent-primary);
            color: white;
            box-shadow: 0 4px 15px var(--shadow-light);
        }
        
        .nav-tab svg {
            flex-shrink: 0;
            vertical-align: middle;
        }
        
        /* Responsive text */
        .mobile-text { font-size: 14px; line-height: 1.4; }
        .mobile-small { font-size: 12px; color: var(--text-muted); }
        
        /* Touch-friendly elements */
        .touch-target { min-height: 44px; min-width: 44px; }
        
        /* Loading states */
        .loading { opacity: 0.6; pointer-events: none; }
        .loading::after {
            content: ''; position: absolute; top: 50%; left: 50%;
            width: 20px; height: 20px; margin: -10px 0 0 -10px;
            border: 2px solid #0f9d58; border-top: 2px solid transparent;
            border-radius: 50%; animation: spin 1s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        /* Dark mode optimizations */
        @media (prefers-color-scheme: dark) {
            body { background: #000; color: #fff; }
            .clip-card { background: #1a1a1a; }
        }
        
        /* Pagination styles */
        .pagination-controls {
            margin-top: 20px;
            text-align: center;
        }
        
        .pagination-info {
            margin-bottom: 50px;
            color: #aaa;
            font-size: 14px;
        }
        
        .pagination-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .pagination-btn {
            padding: 8px 16px;
            background: #0f9d58;
            color: #fff;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
            font-weight: 500;
        }
        
        .pagination-btn:hover {
            background: #0a7d47;
            transform: translateY(-1px);
        }
        
        .pagination-btn:active {
            transform: scale(0.98);
        }
        
        .page-info {
            padding: 8px 16px;
            background: #333;
            color: #fff;
            border-radius: 6px;
            font-size: 14px;
            display: flex;
            align-items: center;
        }
        
        /* Mobile responsive */
        @media (max-width: 768px) {
            header {
                padding: 15px;
            }
            .header-content {
                gap: 15px;
            }
            .app-logo {
                width: 45px;
                height: 45px;
            }
            .header-text h1 {
                font-size: 20px;
            }
            .header-text p {
                font-size: 12px;
            }
            .logout-text {
                display: none;
            }
            .logout-btn {
                padding: 6px 12px;
            }
            
            .pagination-buttons {
                gap: 8px;
            }
            
            .pagination-btn {
                padding: 6px 12px;
                font-size: 13px;
            }
            
            .page-info {
                padding: 6px 12px;
                font-size: 13px;
            }
        }
        
        @media (max-width: 480px) {
            .header-content {
                gap: 12px;
            }
            .app-logo {
                width: 40px;
                height: 40px;
            }
            .header-text h1 {
                font-size: 18px;
            }
            .header-text p {
                font-size: 11px;
            }
        }
        
        /* Enhanced Mobile Optimizations */
        @media (max-width: 768px) {
            /* Sticky header for mobile */
            header {
                position: sticky;
                top: 0;
                z-index: 1000;
                backdrop-filter: blur(10px);
                background: rgba(15, 23, 42, 0.95);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            /* Mobile navigation tabs */
            .nav-tabs {
                gap: 8px;
                flex-wrap: wrap;
                justify-content: center;
                padding: 10px 0;
            }
            .nav-tab {
                padding: 12px 20px;
                font-size: 14px;
                min-width: 80px;
                text-align: center;
                border-radius: 8px;
                transition: all 0.2s ease;
                flex: 1;
                max-width: 120px;
            }
            .nav-tab:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }
            
            /* Mobile main content */
            .main-content {
                padding: 20px 15px;
                padding-top: 10px;
            }
            
            /* Mobile camera grid */
            .camera-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            .camera-card {
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }
            .camera-title {
                font-size: 18px;
                margin-bottom: 10px;
            }
            .camera-status {
                font-size: 13px;
                padding: 6px 12px;
                border-radius: 20px;
            }
            .camera-stream {
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }
            
            /* Mobile clips */
            .clips {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            .clip-card {
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }
            .clip-header {
                font-size: 15px;
                margin-bottom: 15px;
            }
            .clip-video {
                height: 250px;
                border-radius: 8px;
                width: 100%;
            }
            
            /* Mobile settings */
            .settings-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            .settings-card {
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }
            .settings-title {
                font-size: 18px;
                margin-bottom: 15px;
            }
            .settings-content {
                font-size: 15px;
                line-height: 1.6;
            }
            
            /* Mobile buttons */
            .btn {
                padding: 12px 20px;
                font-size: 15px;
                border-radius: 8px;
                min-height: 44px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                width: 100%;
                margin: 5px 0;
            }
            
            /* Mobile forms */
            .form-group {
                margin-bottom: 20px;
            }
            .form-label {
                font-size: 15px;
                margin-bottom: 8px;
                display: block;
            }
            .form-input, .form-select {
                padding: 12px 16px;
                font-size: 15px;
                border-radius: 8px;
                min-height: 44px;
                width: 100%;
            }
            .form-textarea {
                padding: 12px 16px;
                font-size: 15px;
                min-height: 100px;
                border-radius: 8px;
                width: 100%;
                resize: vertical;
            }
            
            /* Mobile controls */
            .controls {
                margin-bottom: 20px;
            }
            .controls form {
                flex-direction: column;
                gap: 15px;
                align-items: stretch;
            }
            .controls label {
                font-size: 15px;
                margin-bottom: 5px;
            }
            .controls select {
                width: 100%;
                min-height: 44px;
            }
            
            /* Mobile badges and indicators */
            .badge {
                font-size: 12px;
                padding: 6px 12px;
                border-radius: 20px;
            }
            .status-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 12px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                font-size: 13px;
            }
            
            /* Mobile video controls */
            video {
                width: 100% !important;
                height: auto !important;
                max-height: 300px;
                object-fit: contain;
            }
            
            /* Mobile loading states */
            .loading-mobile {
                position: relative;
                overflow: hidden;
            }
            .loading-mobile::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
                animation: loading-shimmer 1.5s infinite;
            }
            
            @keyframes loading-shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }
            
            /* Mobile toast notifications */
            .toast {
                font-size: 15px;
                padding: 16px 20px;
                border-radius: 8px;
                max-width: 90vw;
                left: 50%;
                transform: translateX(-50%);
            }
        }
        
        @media (max-width: 480px) {
            /* Extra small mobile devices */
            .nav-tabs {
                gap: 6px;
                width: 100%;
                justify-content: space-between;
            }
            .nav-tab {
                padding: 8px 12px;
                font-size: 13px;
                flex: 1;
                min-width: 0;
            }
            
            .main-content {
                padding: 15px 12px;
            }
            
            .camera-card, .clip-card, .settings-card {
                padding: 15px;
            }
            
            .camera-title, .settings-title {
                font-size: 16px;
            }
            
            .clip-video {
                height: 200px;
            }
            
            .btn {
                padding: 10px 16px;
                font-size: 14px;
            }
            
            .form-input, .form-select {
                padding: 10px 14px;
                font-size: 14px;
            }
            
            .form-textarea {
                padding: 10px 14px;
                font-size: 14px;
                min-height: 80px;
            }
        }
        
        /* Fullscreen styles */
        .camera-feed:fullscreen {
            background: #000;
            border-radius: 0;
            width: 100vw !important;
            height: 100vh !important;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            z-index: 9999 !important;
        }
        
        .camera-feed:fullscreen .camera-content {
            width: 100vw !important;
            height: 100vh !important;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
        }
        
        .camera-feed:fullscreen img {
            width: 100vw !important;
            height: 100vh !important;
            object-fit: contain !important;
            position: absolute;
            top: 0;
            left: 0;
        }
        
        .camera-feed:fullscreen .camera-header {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            z-index: 20;
            background: linear-gradient(135deg, #0f9d58, #0a7d47);
        }
        
        .camera-feed:fullscreen .camera-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 15;
            pointer-events: none;
        }
        
        .camera-feed:fullscreen .camera-controls {
            position: absolute;
            bottom: 20px;
            left: 20px;
            z-index: 25;
            pointer-events: auto;
        }
    </style>
</head>
<body>
<header>
    <div class="header-content">
        <div class="app-logo">
            <img id="header-logo" src="/static/logo_dark.png" alt="FalconEye Logo" class="header-logo">
        </div>
        <div class="header-text">
            <h1>FalconEye Dashboard</h1>
            <p>Home Security System</p>
        </div>
        <div class="header-actions">
        </div>
    </div>
</header>


<div class="container">
    <!-- Mobile Navigation Tabs -->
    <div class="nav-tabs">
        <button class="nav-tab active" onclick="showTab('live')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
            </svg>
            Live
        </button>
        <button class="nav-tab" onclick="showTab('clips')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
            </svg>
            Clips
        </button>
        <button class="nav-tab" onclick="showTab('status')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            Status
        </button>
        <button class="nav-tab" onclick="showTab('settings')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
            </svg>
            Settings
        </button>
    </div>

    <!-- Live Stream Tab -->
    <div id="live-tab" class="tab-content">
        <div class="section">
            <h2>
                <span class="status-indicator status-online"></span>
                Live Surveillance Feed
            </h2>
            
            
            <!-- Dual Camera Grid -->
            <div class="cctv-grid">
                <!-- Pi Zero Camera (Left) -->
                <div class="camera-feed">
                    <div class="camera-header">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px;">
                            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
                        </svg>
                        Pi Zero Camera (Live Stream)
            </div>
                    <div class="camera-content">
                    <img id="pizero-stream" src="/camera/live/cam2?mode=lite&detect_every=10" 
                             onload="this.style.opacity=1;" 
                             onerror="this.style.opacity=0.5; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ4MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMzMzIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIyNCIgZmlsbD0iI2ZmZiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkxpdmUgU3RyZWFtIExvYWRpbmcuLi48L3RleHQ+PC9zdmc+';"
                             alt="Pi Zero live stream" />
                        
                        <!-- Pi Zero Overlay -->
                        <div class="camera-overlay">
                            <div class="camera-status">
                                <span>LIVE</span>
                            </div>
            </div>
            
                        <!-- Pi Zero Controls -->
                        <div class="camera-controls">
                            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:6px;">
                                <span style="font-size:12px; opacity:0.8;">Pan Controls</span>
                                <span style="font-size:11px; opacity:0.6;">(cam2)</span>
                            </div>
             <button class="control-btn" onclick="panCam('left')" title="Pan Left">
                 <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                     <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                 </svg>
                 <span>Left</span>
             </button>
             <button class="control-btn" onclick="panCam('auto')" title="Pan Auto Mode">
                 <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                     <path d="M8 5v14l11-7z"/>
                 </svg>
                 <span>Pan Auto</span>
             </button>
             <button class="control-btn" onclick="panCam('right')" title="Pan Right">
                 <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                     <path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z"/>
                 </svg>
                 <span>Right</span>
             </button>
                            
                            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:8px 0 6px 0;">
                                <span style="font-size:12px; opacity:0.8;">Tilt Controls</span>
                                <span style="font-size:11px; opacity:0.6;">(cam2)</span>
                            </div>
             <button class="control-btn" onclick="tiltCam('up')" title="Tilt Up">
                 <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                     <path d="M7.41 15.41L12 11l4.59 4.41L18 15l-6-6-6 6 1.41 1.41z"/>
                 </svg>
                 <span>Up</span>
             </button>
             <button class="control-btn" onclick="tiltCam('auto')" title="Tilt Auto Mode">
                 <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                     <path d="M8 5v14l11-7z"/>
                 </svg>
                 <span>Tilt Auto</span>
             </button>
             <button class="control-btn" onclick="tiltCam('down')" title="Tilt Down">
                 <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                     <path d="M7.41 8.41L12 13l4.59-4.59L18 9l-6 6-6-6 1.41-1.41z"/>
                 </svg>
                 <span>Down</span>
             </button>
                            
                            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:8px 0 6px 0;">
                                <span style="font-size:12px; opacity:0.8;">Other Controls</span>
                            </div>
                            <button class="control-btn" onclick="refreshPiZero()" title="Refresh Stream">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
                                </svg>
                                <span>Refresh</span>
                            </button>
                            <button class="control-btn" onclick="takePiZeroSnapshot()" title="Take Picture">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M12 12m-3.2 0a3.2 3.2 0 1 0 6.4 0 3.2 3.2 0 1 0 -6.4 0"/>
                                    <path d="M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z"/>
                                </svg>
                                <span>Picture</span>
                            </button>
                            <button class="control-btn" id="pizero-fullscreen-btn" onclick="togglePiZeroFullscreen()" title="Fullscreen (F11)">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                                </svg>
                                <span>Fullscreen</span>
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- ESP32 Camera (Right) -->
                <div class="camera-feed">
                    <div class="camera-header">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px;">
                            <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L19 5H5L3 7V9H1V20C1 21.1 1.9 22 3 22H21C22.1 22 23 21.1 23 20V9H21ZM12 18C9.79 18 8 16.21 8 14S9.79 10 12 10S16 11.79 16 14S14.21 18 12 18Z"/>
                        </svg>
                        ESP32 Camera (Snapshot)
                </div>
                    <div class="camera-content">
                        <img id="esp32-img" src="/camera/snapshot/cam1" 
                             onload="this.style.opacity=1" 
                             onerror="this.style.opacity=0.5"
                             alt="ESP32 camera feed" />
                        
                        <!-- ESP32 Overlay -->
                        <div class="camera-overlay">
                            <div class="camera-status">
                                <span>ACTIVE</span>
                            </div>
                        </div>
                        
                        <!-- ESP32 Controls -->
                        <div class="camera-controls">
                            <button class="control-btn" onclick="refreshESP32()" title="Take Snapshot">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M12 12m-3.2 0a3.2 3.2 0 1 0 6.4 0 3.2 3.2 0 1 0 -6.4 0"/>
                                    <path d="M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z"/>
                                </svg>
                                <span>Snapshot</span>
                        </button>
                            <button class="control-btn" id="esp32-fullscreen-btn" onclick="toggleESP32Fullscreen()" title="Fullscreen (F11)">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                                </svg>
                                <span>Fullscreen</span>
                        </button>
                    </div>
                    </div>
                </div>
            </div>
            
            <!-- Detection Tags -->
            <div id="detection-tags" class="detection-tags" style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 50px; min-height: 40px; align-items: center; padding: 8px; background: rgba(0,0,0,0.1); border-radius: 8px;">
                <span style="color: #aaa; font-size: 14px;">Recent Detections:</span>
            </div>
        </div>

        <!-- Quick Actions -->
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M7 2v11h3v9l7-12h-4l4-8z"/>
                </svg>
                Quick Actions
            </h2>
            <div class="quick-actions">
                <button class="action-btn" onclick="refreshSnapshot()">
                    <div class="action-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L19 5H5L3 7V9H1V20C1 21.1 1.9 22 3 22H21C22.1 22 23 21.1 23 20V9H21ZM12 18C9.79 18 8 16.21 8 14S9.79 10 12 10S16 11.79 16 14S14.21 18 12 18Z"/>
                        </svg>
                    </div>
                    <div class="action-text">Snapshot</div>
                </button>
                <button class="action-btn" onclick="testNotification()">
                    <div class="action-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
                        </svg>
                    </div>
                    <div class="action-text">Test Alert</div>
                </button>
                <button class="action-btn" onclick="showTab('clips')">
                    <div class="action-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
                        </svg>
                    </div>
                    <div class="action-text">View Clips</div>
                </button>
                <button class="action-btn" onclick="showTab('settings')">
                    <div class="action-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
                        </svg>
                    </div>
                    <div class="action-text">Settings</div>
                </button>
            </div>
        </div>
    </div>

    <!-- Clips Tab -->
    <div id="clips-tab" class="tab-content" style="display: none;">
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
                </svg>
                Recorded Clips
            </h2>
            
            <div class="controls">
                <form method="get" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                    <label for="date" class="mobile-text">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                            <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/>
                        </svg>
                        Date:
                    </label>
                    <select name="date" id="date" onchange="changeDate(this.value)" class="touch-target">
                        {% for d in all_dates %}
                            <option value="{{ d }}" {% if d == selected_date %}selected{% endif %}>{{ d }}</option>
                        {% endfor %}
                    </select>
                </form>
            </div>

            <h3 class="mobile-text" style="display: flex; align-items: center; gap: 8px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/>
                </svg>
                {{ selected_date }} 
                {% if total_clips > 0 %}
                    <span class="mobile-small">({{ total_clips }} clips)</span>
                {% endif %}
            </h3>

            {% if day_clips %}
                <div class="clips">
                    {% for name, data in day_clips %}
                    <div class="clip-card" data-filename="{{ name }}">
                        <div class="clip-header">
                            <div class="mobile-text">
                                <strong>🔍 Detected:</strong>
                                {% if data["tags"] %}
                                  {% for t in data["tags"] %}<span class="badge" style="margin-right:6px">{{ t }}</span>{% endfor %}
                                {% else %}Unknown{% endif %}
                                <br>
                                <strong>
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                                        <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
                                    </svg>
                                    Camera:
                                </strong>
                                <span class="badge" style="background: {% if data.get('camera') == 'cam1' %}#2196f3{% else %}#0f9d58{% endif %}; margin-left: 6px;">
                                    {% if data.get('camera') == 'cam1' %}
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                                            <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L19 5H5L3 7V9H1V20C1 21.1 1.9 22 3 22H21C22.1 22 23 21.1 23 20V9H21ZM12 18C9.79 18 8 16.21 8 14S9.79 10 12 10S16 11.79 16 14S14.21 18 12 18Z"/>
                                        </svg>
                                        ESP32
                                    {% else %}
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                                            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
                                        </svg>
                                        Pi Zero
                                    {% endif %}
                                </span>
                            </div>
                <div class="upload-status">
                    {% if data.get("uploaded_to_s3") == True %}
                        <span class="status-badge uploaded">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
                            </svg>
                            Uploaded
                        </span>
                    {% elif data.get("uploaded_to_s3") == False %}
                        {% if data.get("s3_error") == "AWS credentials not configured" %}
                            <span class="status-badge not-configured">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                                    <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
                                </svg>
                                Not Configured
                            </span>
                        {% else %}
                            <span class="status-badge failed">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                </svg>
                                Upload Failed
                            </span>
                        {% endif %}
                    {% else %}
                        <span class="status-badge pending">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                                <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6l5.25 3.15-.75 1.23L11 13V7z"/>
                            </svg>
                            Uploading...
                        </span>
                    {% endif %}
                </div>
                        </div>
                        <div class="mobile-small">{{ format_clip_name(name) }} • {{ data.get("duration", 15) }}s</div>
                        
                        <video style="width: 100%;" controls preload="metadata" playsinline webkit-playsinline>
                            <source src="/clips/{{ name }}" type="video/mp4">
                            Your browser doesn't support video playback.
                        </video>
                        
                        <div style="margin-top: 10px; text-align: center;">
                            <a href="/clips/{{ name }}" download class="touch-target" 
                               style="display: inline-block; padding: 8px 16px; background: #0f9d58; 
                                      color: white; text-decoration: none; border-radius: 6px;">
                                ⬇ Download
                            </a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                
                <!-- Pagination Controls -->
                {% if total_pages > 1 %}
                <div class="pagination-controls" style="margin-top: 20px; text-align: center;">
                    <div class="pagination-info" style="margin-bottom: 50px; color: #aaa; font-size: 14px;">
                        Showing {{ ((page - 1) * 10) + 1 }}-{{ ((page - 1) * 10) + day_clips|length }} of {{ total_clips }} clips
                    </div>
                    
                    <div class="pagination-buttons" style="display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                        {% if has_prev %}
                        <button onclick="loadPage({{ page - 1 }})" class="pagination-btn" style="padding: 8px 16px; background: #222; color: #fff; border: 1px solid #444; border-radius: 6px; cursor: pointer;">
                            ← Previous
                        </button>
                        {% endif %}
                        
                        <span class="page-info" style="padding: 8px 16px; background: #333; color: #fff; border-radius: 6px; font-size: 14px;">
                            Page {{ page }} of {{ total_pages }}
                        </span>
                        
                        {% if has_more %}
                        <button onclick="loadPage({{ page + 1 }})" class="pagination-btn" style="padding: 8px 16px; background: #0f9d58; color: #fff; border: none; border-radius: 6px; cursor: pointer;">
                            View More →
                        </button>
                        {% endif %}
                    </div>
                </div>
                {% endif %}
            {% else %}
                <div style="text-align: center; padding: 40px 20px; color: #aaa;">
                    <div style="font-size: 48px; margin-bottom: 16px;">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" style="opacity: 0.3;">
                            <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4zM14 13h-3v3H9v-3H6v-2h3V8h2v3h3v2z"/>
                        </svg>
                    </div>
                    <div class="mobile-text">No recorded clips yet</div>
                    <div class="mobile-small">Clips will appear here when motion is detected</div>
                </div>
            {% endif %}
        </div>
    </div>

    <!-- Status Tab -->
    <div id="status-tab" class="tab-content" style="display: none;">
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                System Status
            </h2>
            
            <div class="clip-card">
                <div class="mobile-text">
                    <strong>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                            <path d="M4 6c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2H4zm0 2h16v8H4V8zm2 2v4h2v-4H6zm4 0v4h2v-4h-2zm4 0v4h2v-4h-2z"/>
                        </svg>
                        Device:
                    </strong> {{ status.device|upper }}<br>
                    {% if status.gpu %}
                    <strong>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                            <path d="M21 16V8c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v8c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM7 10h2v4H7v-4zm4 0h2v4h-2v-4zm4 0h2v4h-2v-4z"/>
                        </svg>
                        GPU:
                    </strong> {{ status.gpu }}<br>
                    {% endif %}
                    <strong>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                        Status:
                    </strong> 
                    <span class="status-indicator status-online"></span>Online
                </div>
            </div>

            <div class="clip-card">
                <h3 class="mobile-text">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 6px; vertical-align: middle;">
                        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                    </svg>
                    System Performance
                </h3>
                <div class="mobile-small">
                    • Dual Camera System: ESP32 + Pi Zero<br>
                    • AI Detection: YOLOv8s with Apple Silicon GPU<br>
                    • Video Codec: XVID/AVI (Cross-platform compatible)<br>
                    • Storage: Local + AWS S3 Auto-backup<br>
                    • Cloudflare Tunnel: Secure remote access<br>
                    • Frame Rate: 10 FPS capture, 5 FPS live stream
                </div>
            </div>

            <div class="clip-card">
                <h3 class="mobile-text">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 6px; vertical-align: middle;">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    Security Features
                </h3>
                <div class="mobile-small">
                    • Password Protection with Visibility Toggle<br>
                    • Session Management with "Remember Me"<br>
                    • Secure Login with Error Handling<br>
                    • HTTPS via Cloudflare Tunnel<br>
                    • Encrypted Video Storage<br>
                    • Real-time Detection Alerts
                </div>
            </div>

            <div class="clip-card">
                <h3 class="mobile-text">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 6px; vertical-align: middle;">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    Mobile Experience
                </h3>
                <div class="mobile-small">
                    • Fully Responsive Design<br>
                    • Touch-Optimized Controls<br>
                    • Portrait/Landscape Support<br>
                    • Pull-to-Refresh Gestures<br>
                    • Native Sharing Integration<br>
                    • Progressive Web App Features<br>
                    • Optimized Video Playback
        </div>
    </div>

            <div class="clip-card">
                <h3 class="mobile-text">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 6px; vertical-align: middle;">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    Recent Enhancements
                </h3>
                <div class="mobile-small">
                    • Smart Date Selection (No Auto-redirect)<br>
                    • Cross-Platform Video Compatibility<br>
                    • Enhanced Mobile UI/UX<br>
                    • Improved Login Experience<br>
                    • Better Error Handling<br>
                    • Optimized Live Stream Layout<br>
                    • Clean Password Toggle Design
                </div>
                </div>
            </div>
        </div>

    <!-- Settings Tab -->
    <div id="settings-tab" class="tab-content" style="display:none;">
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
                </svg>
                Cloud Storage
            </h2>
            <div class="clip-card">
                <div class="mobile-text">Cloud Storage Backup</div>
                <div class="mobile-small" id="aws-status">
                    {% if not aws_configured %}
                        <div style="color: #dc3545; margin-bottom: 10px;">
                            ⚠️ AWS S3 not configured. Clips stored locally only.
                        </div>
                        <div style="color: #666;">
                            • Local storage: ✅ Available (fast viewing)<br>
                            • Cloud backup: ❌ Not available<br>
                            • Auto-upload: ❌ Disabled
                        </div>
                    {% else %}
                        <div style="color: #28a745; margin-bottom: 10px;">
                            ✅ Cloud backup system active!
                        </div>
                        <div style="color: #666;">
                            • Local storage: ✅ Available (fast viewing)<br>
                            • Cloud backup: ✅ Auto-uploading to S3<br>
                            • Backup mode: ✅ Enabled<br>
                            • Viewing: Local only (fast)
                        </div>
                    {% endif %}
                </div>
                <div class="controls">
                    <button onclick="retryS3Uploads()">Retry Failed Uploads</button>
                    <button onclick="testS3Connection()">Test S3 Connection</button>
                </div>
            </div>
        </div>
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
                </svg>
                Notifications
            </h2>
            <div class="clip-card">
                <div class="mobile-text">Register/Unregister FCM Token</div>
                <input id="fcm-token" placeholder="Token" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border-color);background:var(--bg-secondary);color:var(--text-primary);margin:8px 0"/>
                <div class="controls">
                    <button onclick="registerToken()">Register</button>
                    <button onclick="unregisterToken()">Unregister</button>
                    <button onclick="testPush()">Send Test</button>
                </div>
                <div id="fcm-status" class="mobile-small"></div>
            </div>
        </div>
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                Faces Management
            </h2>
            <div class="clip-card">
                <div class="mobile-text">Register Faces</div>
                <div class="form-group">
                    <label class="form-label" for="face-name">Name</label>
                    <input id="face-name" class="form-input" placeholder="e.g. Paul" />
                </div>
                <div class="controls" style="gap:10px; align-items:center;">
                    <input id="face-file" type="file" accept="image/*" style="padding:8px; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 8px;" />
                    <button onclick="registerFaceFromFile()">Register from File</button>
                    <button onclick="registerFaceFromESP32()">Register from ESP32 Frame</button>
                </div>
                <div id="face-register-status" class="mobile-small" style="margin-top:8px;"></div>
            </div>
            <div class="clip-card" style="margin-top:12px;">
                <div class="mobile-text" style="display:flex;justify-content:space-between;align-items:center;">
                    <span>Known Faces</span>
                    <button onclick="loadFaces()" style="background:#333;">Refresh</button>
                </div>
                <div id="faces-list" class="mobile-small" style="margin-top:8px; display:flex; gap:8px; flex-wrap:wrap;"></div>
            </div>
        </div>
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M3 5h18v2H3V5zm0 6h18v2H3v-2zm0 6h18v2H3v-2z"/>
                </svg>
                Vision Settings
            </h2>
            <div class="settings-card">
                <div class="settings-title">Overlays</div>
                <div class="settings-content">
                    <label><input type="checkbox" id="vs-show-boxes"> Show boxes</label><br/>
                    <label><input type="checkbox" id="vs-show-labels"> Show labels</label><br/>
                    <label><input type="checkbox" id="vs-show-summary"> Show summary line</label><br/>
                    <label>Min area: <input type="number" id="vs-min-area" min="0" step="500" style="width:120px"></label>
                </div>
            </div>
            <div class="settings-card" style="margin-top:12px;">
                <div class="settings-title">Face Recognition</div>
                <div class="settings-content">
                    <label><input type="checkbox" id="vs-faces-enabled"> Enable</label><br/>
                    <label><input type="checkbox" id="vs-faces-overlay"> Show overlay</label><br/>
                    <label><input type="checkbox" id="vs-faces-hide-person"> Hide generic "person" when name recognized</label><br/>
                    <label>Tolerance: <input type="number" id="vs-faces-tol" min="0.1" max="1.0" step="0.05" style="width:120px"></label><br/>
                    <label>Sample every N frames: <input type="number" id="vs-faces-every" min="1" max="60" step="1" style="width:120px"></label>
                </div>
            </div>
            <div class="settings-card" style="margin-top:12px;">
                <div class="settings-title">Classes</div>
                <div class="settings-content" id="vs-classes">
                    <!-- Populated by JS from settings -->
                </div>
                <div class="controls" style="margin-top:10px;">
                    <button onclick="saveVisionSettings()">Save</button>
                    <button onclick="loadVisionSettings()">Reset</button>
                </div>
                <div id="vs-status" class="mobile-small" style="margin-top:8px;"></div>
            </div>
        </div>
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                Account
            </h2>
            <div class="clip-card">
                <div class="mobile-text">Account Management</div>
                <div class="controls">
                    <button class="logout-btn" onclick="logout()" title="Logout">
                        <span class="logout-icon">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
                            </svg>
                        </span>
                        <span class="logout-text">Logout</span>
                    </button>
                </div>
            </div>
        </div>
        <div class="section">
            <h2>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                    <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z"/>
                </svg>
                Theme Settings
            </h2>
            <div class="clip-card">
                <div class="mobile-text">Choose your preferred theme</div>
                <div class="theme-options">
                    <div class="theme-option" onclick="setTheme('dark')" id="theme-dark">
                        <div class="theme-preview dark-preview">
                            <div class="theme-header"></div>
                            <div class="theme-content">
                                <div class="theme-card"></div>
                                <div class="theme-card"></div>
                            </div>
                        </div>
                        <div class="theme-label">Dark Theme</div>
                        <div class="theme-description">Easy on the eyes, perfect for low light</div>
                    </div>
                    <div class="theme-option" onclick="setTheme('light')" id="theme-light">
                        <div class="theme-preview light-preview">
                            <div class="theme-header"></div>
                            <div class="theme-content">
                                <div class="theme-card"></div>
                                <div class="theme-card"></div>
                            </div>
                        </div>
                        <div class="theme-label">Light Theme</div>
                        <div class="theme-description">Clean and bright, great for daytime use</div>
                    </div>
                </div>
                <div id="theme-status" class="mobile-small"></div>
            </div>
        </div>
    </div>
</div>

<script>
// Mobile-optimized JavaScript
function showTab(tabName) {
    try {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.style.display = 'none';
        });
        
        // Remove active class from all nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Show selected tab
        const targetTab = document.getElementById(tabName + '-tab');
        if (targetTab) {
            targetTab.style.display = 'block';
        }
        
        // Add active class to clicked tab
        if (event && event.target) {
            event.target.classList.add('active');
        }
        
        // Update URL with tab parameter
        const urlParams = new URLSearchParams(window.location.search);
        if (tabName !== 'live') {
            urlParams.set('tab', tabName);
        } else {
            urlParams.delete('tab');
        }
        
        // Update URL without reloading
        const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
        window.history.replaceState({}, '', newUrl);
    } catch (error) {
        console.log('Tab switch error:', error);
    }
}

// Pagination function
function loadPage(pageNumber) {
    try {
        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const currentDate = urlParams.get('date') || new Date().toISOString().split('T')[0];
        
        // Update page parameter
        urlParams.set('page', pageNumber);
        // Add tab parameter to stay on clips tab
        urlParams.set('tab', 'clips');
        
        // Build new URL
        const newUrl = window.location.pathname + '?' + urlParams.toString();
        
        // Show loading state
        const clipsContainer = document.querySelector('.clips');
        if (clipsContainer) {
            clipsContainer.style.opacity = '0.6';
            clipsContainer.style.pointerEvents = 'none';
        }
        
        // Navigate to new page
        window.location.href = newUrl;
    } catch (error) {
        console.log('Pagination error:', error);
        showToast('Error loading page', 'error');
    }
}

function refreshSnapshot() {
    refreshESP32();
}
    
function refreshESP32() {
    const img = document.getElementById('esp32-img');
    if (img) {
        img.style.opacity = '0.5';
        img.src = `/camera/snapshot/cam1?t=` + new Date().getTime();
        img.onload = function() {
            this.style.opacity = '1';
        };
    }
}

function refreshPiZero() {
    const img = document.getElementById('pizero-stream');
    if (img) {
        img.style.opacity = '0.5';
        img.src = `/camera/live/cam2?mode=lite&detect_every=10&t=` + new Date().getTime();
                    img.onload = function() {
                        this.style.opacity = '1';
                    };
    }
}

async function panCam(direction) {
    try {
        const res = await fetch('/camera/pan/' + direction, { method: 'POST' });
        if (!res.ok) {
            showToast('Pan ' + direction + ' failed', 'error');
        } else {
            showToast('Pan ' + direction + ' sent', 'success');
        }
    } catch (e) {
        showToast('Pan command error', 'error');
    }
}

async function tiltCam(direction) {
    try {
        const res = await fetch('/camera/tilt/' + direction, { method: 'POST' });
        if (!res.ok) {
            showToast('Tilt ' + direction + ' failed', 'error');
        } else {
            showToast('Tilt ' + direction + ' sent', 'success');
        }
    } catch (e) {
        showToast('Tilt command error', 'error');
    }
}

function takePiZeroSnapshot() {
    // Create a temporary canvas to capture the current frame
    const img = document.getElementById('pizero-stream');
    if (!img) {
        showToast('Pi Zero stream not found', 'error');
        return;
    }
    
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match image
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    
    // Draw the image to canvas
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    
    // Convert to blob and download
    canvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `pizero-snapshot-${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.jpg`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Pi Zero snapshot saved!', 'success');
    }, 'image/jpeg', 0.9);
}

function switchCamera() {
    const cameraSelect = document.getElementById('camera-select');
    const currentCamera = cameraSelect.value;
    
    const esp32Container = document.getElementById('esp32-container');
    const pizeroContainer = document.getElementById('pizero-container');
    const esp32Img = document.getElementById('esp32-img');
    const pizeroStream = document.getElementById('pizero-stream');
    
    // Reset FPS calculation
    frameTimes = [];
    lastFrameTime = 0;
    piZeroFrameCount = 0;
    piZeroStartTime = 0;
    
    const fpsInfo = document.getElementById('fps-info');
    if (fpsInfo) {
        fpsInfo.textContent = 'FPS: --';
    }
    
    if (currentCamera === 'cam1') {
        // Show ESP32 (Snapshot mode)
        if (esp32Container) esp32Container.style.display = 'block';
        if (pizeroContainer) pizeroContainer.style.display = 'none';
        
        // Start ESP32 auto-refresh
        if (window.autoRefreshInterval) {
            clearInterval(window.autoRefreshInterval);
        }
        startAutoRefresh();
        
    } else if (currentCamera === 'cam2') {
        // Show Pi Zero (Live stream mode)
        if (esp32Container) esp32Container.style.display = 'none';
        if (pizeroContainer) pizeroContainer.style.display = 'block';
        
        // Stop ESP32 auto-refresh
        if (window.autoRefreshInterval) {
            clearInterval(window.autoRefreshInterval);
        }
        
        // Start Pi Zero live stream (use lite mode for smoother playback)
        if (pizeroStream) {
            pizeroStream.src = `/camera/live/cam2?mode=lite&detect_every=10&t=` + new Date().getTime();
            piZeroStartTime = Date.now();
            piZeroFrameCount = 0;
        }
    }
    
    // Update the stream info
    const streamInfo = document.getElementById('stream-info');
    if (streamInfo) {
        const cameraName = currentCamera === 'cam1' ? 'ESP32' : 'Pi Zero';
        const modeText = currentCamera === 'cam1' ? 'Snapshot' : 'Live Stream';
        const fpsText = currentCamera === 'cam2' ? ' • 15+ FPS' : '';
        streamInfo.textContent = `📡 ${cameraName} ${modeText}${fpsText}`;
    }
    
    // Restart the auto-refresh with new camera
    if (window.autoRefreshInterval) {
        clearInterval(window.autoRefreshInterval);
    }
    
    window.autoRefreshInterval = setInterval(function() {
        try {
            const liveImg = document.getElementById('liveimg');
            const cameraSelect = document.getElementById('camera-select');
            const currentCamera = cameraSelect ? cameraSelect.value : 'cam1';
            
            if (liveImg) {
                // Calculate FPS
                const currentTime = Date.now();
                if (lastFrameTime > 0) {
                    const frameTime = currentTime - lastFrameTime;
                    frameTimes.push(frameTime);
                    
                    // Keep only last 30 frame times
                    if (frameTimes.length > 30) {
                        frameTimes.shift();
                    }
                    
                    // Calculate average FPS
                    if (frameTimes.length > 1) {
                        const avgFrameTime = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
                        const fps = 1000 / avgFrameTime;
                        
                        // Update FPS display
                        const fpsInfo = document.getElementById('fps-info');
                        if (fpsInfo) {
                            fpsInfo.textContent = `FPS: ${fps.toFixed(1)}`;
                        }
                    }
                }
                lastFrameTime = currentTime;
                
                liveImg.src = `/camera/snapshot/${currentCamera}?t=` + currentTime;
            }
            
            // Fetch recent detections overlay
            fetch('/mobile/detections/recent').then(r=>r.json()).then(list => {
                const tags = document.getElementById('detection-tags');
                if (!tags) return;
                
                // Clear existing tags except the label
                const label = tags.querySelector('span');
                tags.innerHTML = '';
                if (label) tags.appendChild(label);
                
                if (list && list.length) {
                    const last = list[list.length-1];
                    (last.tags||[]).slice(0,6).forEach(t=>{
                        const b=document.createElement('span');
                        b.className='badge';
                        b.textContent=t;
                        b.style.marginLeft = '8px';
                        tags.appendChild(b);
                    });
                }
            }).catch(()=>{});
        } catch (error) {
            console.log('Auto-refresh error:', error);
        }
    }, 1500);
}

// Vision settings
async function loadVisionSettings() {
    try {
        const res = await fetch('/vision/settings');
        const s = await res.json();
        document.getElementById('vs-show-boxes').checked = !!s.show_boxes;
        document.getElementById('vs-show-labels').checked = !!s.show_labels;
        document.getElementById('vs-show-summary').checked = !!s.show_summary;
        document.getElementById('vs-min-area').value = s.min_area ?? 5000;
    // faces
    const fs = s.faces||{};
    document.getElementById('vs-faces-enabled').checked = !!fs.enabled;
    document.getElementById('vs-faces-overlay').checked = !!fs.overlay;
    document.getElementById('vs-faces-tol').value = fs.tolerance ?? 0.6;
    document.getElementById('vs-faces-every').value = fs.sample_every ?? 10;
    document.getElementById('vs-faces-hide-person').checked = !!(fs.hide_person_if_named ?? true);
        const container = document.getElementById('vs-classes');
        container.innerHTML = '';
        const classes = s.enabled_classes || {};
        const colors = s.colors || {};
        Object.keys(classes).forEach(name => {
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.alignItems = 'center';
            wrapper.style.gap = '8px';
            wrapper.style.marginBottom = '8px';
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.id = `vs-class-${name}`;
            cb.checked = !!classes[name];
            const label = document.createElement('label');
            label.htmlFor = cb.id;
            label.textContent = name;
            const color = document.createElement('input');
            color.type = 'color';
            const hex = (colors[name] || '#00c8ff');
            // normalize 3/6 char hex
            color.value = /^#/.test(hex) ? hex : ('#' + hex);
            color.id = `vs-color-${name}`;
            wrapper.appendChild(cb);
            wrapper.appendChild(label);
            wrapper.appendChild(color);
            container.appendChild(wrapper);
        });
        document.getElementById('vs-status').textContent = '';
    } catch (e) {
        document.getElementById('vs-status').textContent = 'Failed to load';
    }
}

async function saveVisionSettings() {
    try {
        const show_boxes = document.getElementById('vs-show-boxes').checked;
        const show_labels = document.getElementById('vs-show-labels').checked;
        const show_summary = document.getElementById('vs-show-summary').checked;
        const min_area = parseInt(document.getElementById('vs-min-area').value || '5000', 10);
    const faces_enabled = document.getElementById('vs-faces-enabled').checked;
    const faces_overlay = document.getElementById('vs-faces-overlay').checked;
    const faces_tol = parseFloat(document.getElementById('vs-faces-tol').value || '0.6');
    const faces_every = parseInt(document.getElementById('vs-faces-every').value || '10', 10);
    const faces_hide_person = document.getElementById('vs-faces-hide-person').checked;
        const container = document.getElementById('vs-classes');
        const enabled = {};
        const colors = {};
        container.querySelectorAll('div').forEach(row => {
            const label = row.querySelector('label');
            const name = label ? label.textContent : null;
            if (!name) return;
            const cb = row.querySelector('input[type="checkbox"]');
            const color = row.querySelector('input[type="color"]');
            enabled[name] = !!(cb && cb.checked);
            colors[name] = color ? color.value : '#00c8ff';
        });
    const res = await fetch('/vision/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ show_boxes, show_labels, show_summary, min_area, faces: { enabled: faces_enabled, overlay: faces_overlay, tolerance: faces_tol, sample_every: faces_every, hide_person_if_named: faces_hide_person }, enabled_classes: enabled, colors }) });
        const js = await res.json();
        if (js.status === 'ok') {
            document.getElementById('vs-status').textContent = 'Saved. Refresh live feed to apply.';
        } else {
            document.getElementById('vs-status').textContent = 'Save failed.';
        }
    } catch (e) {
        document.getElementById('vs-status').textContent = 'Save failed.';
    }
}

// Load on settings tab show and on page load
document.addEventListener('DOMContentLoaded', () => {
    try { loadVisionSettings(); } catch(e){}
});

// Camera status variables
let frameTimes = [];
let lastFrameTime = 0;

// Camera monitoring functions (simplified)

// Auto-refresh snapshot every 1500ms (only for ESP32)
function startAutoRefresh() {
    if (window.autoRefreshInterval) {
        clearInterval(window.autoRefreshInterval);
    }
    
    window.autoRefreshInterval = setInterval(function() {
        try {
            const cameraSelect = document.getElementById('camera-select');
            const currentCamera = cameraSelect ? cameraSelect.value : 'cam1';
            
            // Only refresh ESP32 camera (snapshot mode)
            if (currentCamera === 'cam1') {
                const esp32Img = document.getElementById('esp32-img');
                if (esp32Img) {
                    // Calculate FPS
                    const currentTime = Date.now();
                    if (lastFrameTime > 0) {
                        const frameTime = currentTime - lastFrameTime;
                        frameTimes.push(frameTime);
                        
                        // Keep only last 30 frame times
                        if (frameTimes.length > 30) {
                            frameTimes.shift();
                        }
                        
                        // Calculate average FPS
                        if (frameTimes.length > 1) {
                            const avgFrameTime = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
                            const fps = 1000 / avgFrameTime;
                            
                            // Update FPS display
                            const fpsInfo = document.getElementById('fps-info');
                            if (fpsInfo) {
                                fpsInfo.textContent = `FPS: ${fps.toFixed(1)}`;
                            }
                        }
                    }
                    lastFrameTime = currentTime;
                    
                    esp32Img.src = `/camera/snapshot/cam1?t=` + currentTime;
                }
            }
            
            // Fetch recent detections overlay
            fetch('/mobile/detections/recent').then(r=>r.json()).then(list => {
                const tags = document.getElementById('detection-tags');
                if (!tags) return;
                
                // Clear existing tags except the label
                const label = tags.querySelector('span');
                tags.innerHTML = '';
                if (label) tags.appendChild(label);
                
                if (list && list.length) {
                    const last = list[list.length-1];
                    (last.tags||[]).slice(0,6).forEach(t=>{
                        const b=document.createElement('span');
                        b.className='badge';
                        b.textContent=t;
                        b.style.marginLeft = '8px';
                        tags.appendChild(b);
                    });
                }
            }).catch(()=>{});
        } catch (error) {
            console.log('Auto-refresh error:', error);
        }
    }, 1500);
}

// Start auto-refresh on page load
startAutoRefresh();

async function registerToken(){
  const t=document.getElementById('fcm-token').value.trim();
  if(!t) return; 
  const r=await fetch('/fcm/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:t})});
  document.getElementById('fcm-status').textContent = (await r.json()).status||'ok';
}
async function unregisterToken(){
  const t=document.getElementById('fcm-token').value.trim();
  if(!t) return; 
  const r=await fetch('/fcm/unregister',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:t})});
  document.getElementById('fcm-status').textContent = (await r.json()).status||'ok';
}

// Faces Management JS
async function loadFaces(){
  try{
    const res = await fetch('/faces');
    const data = await res.json();
    const list = document.getElementById('faces-list');
    if(!list) return;
    list.innerHTML = '';
    (data.faces||[]).forEach(name=>{
      const item = document.createElement('span');
      item.className = 'badge';
      item.style.display = 'inline-flex';
      item.style.alignItems = 'center';
      item.style.gap = '6px';
      item.textContent = name;
      const del = document.createElement('button');
      del.textContent = '✕';
      del.style.marginLeft = '6px';
      del.style.background = '#444';
      del.style.padding = '4px 8px';
      del.style.borderRadius = '10px';
      del.onclick = async ()=>{ await deleteFace(name); };
      item.appendChild(del);
      list.appendChild(item);
    });
    if(!data.faces || !data.faces.length){
      list.textContent = 'No faces registered yet';
    }
  }catch(e){
    console.log('loadFaces error', e);
  }
}

function fileToBase64(file){
  return new Promise((resolve,reject)=>{
    const reader = new FileReader();
    reader.onload = ()=> resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function registerFaceFromFile(){
  const name = (document.getElementById('face-name').value||'').trim();
  const fileInput = document.getElementById('face-file');
  const status = document.getElementById('face-register-status');
  if(!name){ status.textContent = 'Please enter a name'; return; }
  if(!fileInput.files || !fileInput.files[0]){ status.textContent = 'Select an image file'; return; }
  try{
    status.textContent = 'Registering...';
    const b64 = await fileToBase64(fileInput.files[0]);
    const res = await fetch('/faces/register',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name:name, image_base64:b64})});
    const data = await res.json();
    if(res.ok && data.success){
      status.textContent = `Registered ${name}`;
      loadFaces();
    }else{
      status.textContent = data.error || 'Registration failed';
    }
  }catch(e){
    status.textContent = 'Error registering face';
  }
}

async function registerFaceFromESP32(){
  const name = (document.getElementById('face-name').value||'').trim();
  const status = document.getElementById('face-register-status');
  if(!name){ status.textContent = 'Please enter a name'; return; }
  try{
    const img = document.getElementById('esp32-img');
    if(!img){ status.textContent = 'ESP32 frame not available'; return; }
    // Draw current image to canvas
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    const b64 = dataUrl.split(',')[1];
    status.textContent = 'Registering from frame...';
    const res = await fetch('/faces/register',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name:name, image_base64:b64})});
    const data = await res.json();
    if(res.ok && data.success){
      status.textContent = `Registered ${name} from ESP32 frame`;
      loadFaces();
    }else{
      status.textContent = data.error || 'Registration failed';
    }
  }catch(e){
    status.textContent = 'Error registering from frame';
  }
}

async function deleteFace(name){
  try{
    const res = await fetch('/faces/delete',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name})});
    if(res.ok){
      loadFaces();
    }
  }catch(e){
    console.log('deleteFace error', e);
  }
}

// Load faces on settings tab open and on page load
document.addEventListener('DOMContentLoaded', ()=>{
  loadFaces();
});
async function testPush(){
  const t=document.getElementById('fcm-token').value.trim();
  if(!t) return; 
  const r=await fetch('/fcm/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:t})});
  const j=await r.json();
  document.getElementById('fcm-status').textContent = j.message||j.status;
}

// Touch gestures for mobile
let startX, startY;
document.addEventListener('touchstart', function(e) {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
});

document.addEventListener('touchend', function(e) {
    if (!startX || !startY) return;
    
    let endX = e.changedTouches[0].clientX;
    let endY = e.changedTouches[0].clientY;
    
    let diffX = startX - endX;
    let diffY = startY - endY;
    
    // Horizontal swipe
    if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
        const tabs = ['live', 'clips', 'status'];
        const currentTab = document.querySelector('.nav-tab.active').textContent.toLowerCase();
        const currentIndex = tabs.indexOf(currentTab);
        
        if (diffX > 0 && currentIndex < tabs.length - 1) {
            // Swipe left - next tab
            showTab(tabs[currentIndex + 1]);
        } else if (diffX < 0 && currentIndex > 0) {
            // Swipe right - previous tab
            showTab(tabs[currentIndex - 1]);
        }
    }
    
    startX = startY = null;
});

// Theme switching functionality
function setTheme(theme) {
    const body = document.body;
    const statusDiv = document.getElementById('theme-status');
    const headerLogo = document.getElementById('header-logo');
    
    // Remove existing theme classes
        body.classList.remove('light-theme');
    
    // Apply new theme
    if (theme === 'light') {
        body.classList.add('light-theme');
        // Switch to light theme logo with animation
        if (headerLogo) {
            headerLogo.classList.add('theme-switching');
            setTimeout(() => {
                headerLogo.src = '/static/logo_light.png';
                setTimeout(() => {
                    headerLogo.classList.remove('theme-switching');
                }, 100);
            }, 300);
        }
    } else {
        // Switch to dark theme logo with animation
        if (headerLogo) {
            headerLogo.classList.add('theme-switching');
            setTimeout(() => {
                headerLogo.src = '/static/logo_dark.png';
                setTimeout(() => {
                    headerLogo.classList.remove('theme-switching');
                }, 100);
            }, 300);
        }
    }
    
    // Update theme option selection
    document.querySelectorAll('.theme-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    const selectedOption = document.getElementById(`theme-${theme}`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
    }
    
    // Save theme preference
    localStorage.setItem('theme', theme);
    
    // Show status message
    if (statusDiv) {
        statusDiv.innerHTML = `<div style="color: var(--accent-primary); margin-top: 8px;">✅ Theme switched to ${theme === 'light' ? 'Light' : 'Dark'} mode</div>`;
        setTimeout(() => {
            statusDiv.innerHTML = '';
        }, 3000);
    }
}

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    
    
    // Check if we need to switch to a specific tab
    const urlParams = new URLSearchParams(window.location.search);
    const tab = urlParams.get('tab');
    const page = urlParams.get('page');
    const currentDate = urlParams.get('date');
    
    if (tab === 'clips' || (page && page !== '1')) {
        // Switch to clips tab if tab=clips or if we're on a paginated page
        showTab('clips');
    }
    
    // Don't auto-update date - let user select their own date
});


// Stream control functions
let streamInterval = null;
let isStreaming = false;

function toggleStream() {
    const toggleBtn = document.getElementById('stream-toggle');
    
    if (isStreaming) {
        // Stop streaming
        clearInterval(streamInterval);
        toggleBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
        toggleBtn.title = 'Start Stream';
        isStreaming = false;
        document.getElementById('stream-info').innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>Paused';
    } else {
        // Start streaming
        streamInterval = setInterval(() => {
            const liveImg = document.getElementById('liveimg');
            const currentSrc = liveImg.src.split('?')[0];
            liveImg.src = `${currentSrc}?t=${Date.now()}`;
        }, 2000); // Update every 2 seconds
        
        toggleBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';
        toggleBtn.title = 'Stop Stream';
        isStreaming = true;
        document.getElementById('stream-info').innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>Live';
    }
}

function toggleFullscreen() {
    // This function is now handled by individual camera fullscreen functions
}

function togglePiZeroFullscreen() {
    const cameraFeed = document.querySelector('.camera-feed:first-child');
    const fullscreenBtn = document.getElementById('pizero-fullscreen-btn');
    if (!cameraFeed) {
        showToast('Pi Zero camera not found', 'error');
        return;
    }
    
    try {
        if (document.fullscreenElement) {
            document.exitFullscreen();
            showToast('Exited fullscreen', 'success');
            // Update button text
            if (fullscreenBtn) {
                fullscreenBtn.innerHTML = '⛶ Fullscreen';
                fullscreenBtn.title = 'Fullscreen (F11)';
            }
    } else {
            cameraFeed.requestFullscreen();
            showToast('Pi Zero fullscreen activated', 'success');
            // Update button text
            if (fullscreenBtn) {
                fullscreenBtn.innerHTML = '⛶ Minimize';
                fullscreenBtn.title = 'Minimize (ESC)';
            }
        }
    } catch (err) {
        console.log('Fullscreen error:', err);
        showToast('Fullscreen not supported', 'error');
    }
}

function toggleESP32Fullscreen() {
    const cameraFeed = document.querySelector('.camera-feed:last-child');
    const fullscreenBtn = document.getElementById('esp32-fullscreen-btn');
    if (!cameraFeed) {
        showToast('ESP32 camera not found', 'error');
        return;
    }
    
    try {
        if (document.fullscreenElement) {
        document.exitFullscreen();
            showToast('Exited fullscreen', 'success');
            // Update button text
            if (fullscreenBtn) {
                fullscreenBtn.innerHTML = '⛶ Fullscreen';
                fullscreenBtn.title = 'Fullscreen (F11)';
            }
        } else {
            cameraFeed.requestFullscreen();
            showToast('ESP32 fullscreen activated', 'success');
            // Update button text
            if (fullscreenBtn) {
                fullscreenBtn.innerHTML = '⛶ Minimize';
                fullscreenBtn.title = 'Minimize (ESC)';
            }
        }
    } catch (err) {
        console.log('Fullscreen error:', err);
        showToast('Fullscreen not supported', 'error');
    }
}

// Test notification function
function testNotification() {
    // Show a toast notification
    showToast('<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 4px; vertical-align: middle;"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg>Test notification sent!', 'success');
    
    // Send test push notification
    fetch('/mobile/test-push', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({test: true})
    }).then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('✅ Push notification sent successfully!', 'success');
        } else {
            showToast('❌ Failed to send push notification', 'error');
        }
    }).catch(error => {
        showToast('❌ Error sending notification', 'error');
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // F11 key for fullscreen
    if (event.key === 'F11') {
        event.preventDefault();
        // Toggle fullscreen for the currently focused camera
        const activeElement = document.activeElement;
        if (activeElement && activeElement.closest('.camera-feed:first-child')) {
            togglePiZeroFullscreen();
        } else if (activeElement && activeElement.closest('.camera-feed:last-child')) {
            toggleESP32Fullscreen();
        } else {
            // Default to Pi Zero camera
            togglePiZeroFullscreen();
        }
    }
    
    // ESC key to exit fullscreen
    if (event.key === 'Escape' && document.fullscreenElement) {
        document.exitFullscreen().catch(err => {
            console.log('Error exiting fullscreen:', err);
        });
    }
});

// Debug function to test fullscreen
function testFullscreen() {
    console.log('Testing fullscreen functionality...');
    console.log('Pi Zero camera feed:', document.querySelector('.camera-feed:first-child'));
    console.log('ESP32 camera feed:', document.querySelector('.camera-feed:last-child'));
    console.log('Fullscreen supported:', !!document.documentElement.requestFullscreen);
    console.log('Currently in fullscreen:', !!document.fullscreenElement);
}

// Listen for fullscreen changes to update button text
document.addEventListener('fullscreenchange', function() {
    const pizeroBtn = document.getElementById('pizero-fullscreen-btn');
    const esp32Btn = document.getElementById('esp32-fullscreen-btn');
    
    if (!document.fullscreenElement) {
        // Exited fullscreen - reset both buttons
        if (pizeroBtn) {
            pizeroBtn.innerHTML = '⛶ Fullscreen';
            pizeroBtn.title = 'Fullscreen (F11)';
        }
        if (esp32Btn) {
            esp32Btn.innerHTML = '⛶ Fullscreen';
            esp32Btn.title = 'Fullscreen (F11)';
        }
    }
});

// Toast notification system
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Add toast styles
    Object.assign(toast.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        background: type === 'success' ? '#0f9d58' : type === 'error' ? '#f44336' : '#2196f3',
        color: 'white',
        padding: '12px 20px',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
        zIndex: '10000',
        fontSize: '14px',
        fontWeight: '500',
        transform: 'translateX(100%)',
        transition: 'transform 0.3s ease'
    });
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Logo management functions

// Logout function
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        showToast('Logging out...', 'info');
        // Redirect to logout endpoint
        window.location.href = '/logout';
    }
}

// S3 management functions
function retryS3Uploads() {
    showToast('Retrying failed S3 uploads...', 'info');
    fetch('/retry-s3-uploads', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(`Retried ${data.count} uploads`, 'success');
            // Refresh the page to show updated status
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast('Retry failed: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showToast('Retry failed: ' + error.message, 'error');
    });
}

function testS3Connection() {
    showToast('Testing S3 connection...', 'info');
    fetch('/test-s3-connection', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('S3 connection successful!', 'success');
        } else {
            showToast('S3 connection failed: ' + data.error, 'error');
        }
    })
    .catch(error => {
        showToast('S3 test failed: ' + error.message, 'error');
    });
}

// Date change functionality for clips page
function changeDate(selectedDate) {
    // Update URL with new date while staying on clips tab
    const url = new URL(window.location);
    url.searchParams.set('tab', 'clips');
    url.searchParams.set('date', selectedDate);
    url.searchParams.delete('page'); // Reset to page 1 when changing date
    
    // Navigate to the new URL
    window.location.href = url.toString();
}

// Mobile-specific enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Detect mobile device
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 768;
    
    if (isMobile) {
        // Add mobile class to body
        document.body.classList.add('mobile-device');
        
        // Enhance touch interactions
        enhanceTouchInteractions();
        
        // Add mobile-specific event listeners
        addMobileEventListeners();
        
        // Optimize video players for mobile
        optimizeMobileVideos();
        
        // Add pull-to-refresh functionality
        addPullToRefresh();
    }
    
    // Add loading states for mobile
    addMobileLoadingStates();
});

function enhanceTouchInteractions() {
    // Add touch feedback to buttons
    const buttons = document.querySelectorAll('.btn, .nav-tab, .touch-target');
    buttons.forEach(button => {
        button.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.95)';
            this.style.transition = 'transform 0.1s ease';
        });
        
        button.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // Add swipe gestures for navigation tabs
    const navTabs = document.querySelector('.nav-tabs');
    if (navTabs) {
        let startX = 0;
        let startY = 0;
        
        navTabs.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });
        
        navTabs.addEventListener('touchmove', function(e) {
            if (!startX || !startY) return;
            
            const diffX = startX - e.touches[0].clientX;
            const diffY = startY - e.touches[0].clientY;
            
            // Only handle horizontal swipes
            if (Math.abs(diffX) > Math.abs(diffY)) {
                e.preventDefault();
                navTabs.scrollLeft += diffX;
            }
            
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });
    }
}

function addMobileEventListeners() {
    // Add double-tap to zoom for camera feeds
    const cameraFeeds = document.querySelectorAll('.camera-feed, video');
    cameraFeeds.forEach(feed => {
        let lastTap = 0;
        feed.addEventListener('touchend', function(e) {
            const currentTime = new Date().getTime();
            const tapLength = currentTime - lastTap;
            
            if (tapLength < 500 && tapLength > 0) {
                // Double tap detected
                e.preventDefault();
                if (feed.requestFullscreen) {
                    feed.requestFullscreen();
                } else if (feed.webkitRequestFullscreen) {
                    feed.webkitRequestFullscreen();
                }
            }
            lastTap = currentTime;
        });
    });
    
    // Add long press for context menu on clips
    const clipCards = document.querySelectorAll('.clip-card');
    clipCards.forEach(card => {
        let pressTimer = null;
        
        card.addEventListener('touchstart', function(e) {
            pressTimer = setTimeout(() => {
                showMobileContextMenu(e, card);
            }, 500);
        });
        
        card.addEventListener('touchend', function() {
            clearTimeout(pressTimer);
        });
        
        card.addEventListener('touchmove', function() {
            clearTimeout(pressTimer);
        });
    });
}

function optimizeMobileVideos() {
    // Add mobile-specific video attributes
    const videos = document.querySelectorAll('video');
    videos.forEach(video => {
        video.setAttribute('playsinline', '');
        video.setAttribute('webkit-playsinline', '');
        video.setAttribute('x5-playsinline', '');
        video.setAttribute('x5-video-player-type', 'h5');
        video.setAttribute('x5-video-player-fullscreen', 'true');
        
        // Add mobile video controls
        video.addEventListener('loadedmetadata', function() {
            this.style.width = '100%';
            this.style.height = 'auto';
            this.style.maxHeight = '300px';
        });
    });
}

function addPullToRefresh() {
    let startY = 0;
    let currentY = 0;
    let pullDistance = 0;
    const pullThreshold = 100;
    
    document.addEventListener('touchstart', function(e) {
        if (window.scrollY === 0) {
            startY = e.touches[0].clientY;
        }
    });
    
    document.addEventListener('touchmove', function(e) {
        if (window.scrollY === 0 && startY > 0) {
            currentY = e.touches[0].clientY;
            pullDistance = currentY - startY;
            
            if (pullDistance > 0) {
                e.preventDefault();
                document.body.style.transform = `translateY(${Math.min(pullDistance * 0.5, 50)}px)`;
            }
        }
    });
    
    document.addEventListener('touchend', function() {
        if (pullDistance > pullThreshold) {
            // Trigger refresh
            window.location.reload();
        } else {
            // Reset position
            document.body.style.transform = 'translateY(0)';
        }
        
        startY = 0;
        currentY = 0;
        pullDistance = 0;
    });
}

function addMobileLoadingStates() {
    // Add loading states for mobile
    const loadingElements = document.querySelectorAll('.loading-mobile');
    loadingElements.forEach(element => {
        element.addEventListener('click', function() {
            this.classList.add('loading');
            setTimeout(() => {
                this.classList.remove('loading');
            }, 2000);
        });
    });
}

function showMobileContextMenu(e, element) {
    // Create mobile context menu
    const contextMenu = document.createElement('div');
    contextMenu.className = 'mobile-context-menu';
    contextMenu.style.cssText = `
        position: fixed;
        top: ${e.touches ? e.touches[0].clientY : e.clientY}px;
        left: ${e.touches ? e.touches[0].clientX : e.clientX}px;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 10px;
        border-radius: 8px;
        z-index: 10000;
        font-size: 14px;
    `;
    
    contextMenu.innerHTML = `
        <div style="padding: 8px 12px; cursor: pointer;" onclick="downloadClip('${element.dataset.filename || ''}')">⬇ Download</div>
        <div style="padding: 8px 12px; cursor: pointer;" onclick="shareClip('${element.dataset.filename || ''}')">📤 Share</div>
    `;
    
    document.body.appendChild(contextMenu);
    
    // Remove context menu after 3 seconds or on touch
    setTimeout(() => {
        if (contextMenu.parentNode) {
            contextMenu.parentNode.removeChild(contextMenu);
        }
    }, 3000);
    
    document.addEventListener('touchstart', function removeContextMenu() {
        if (contextMenu.parentNode) {
            contextMenu.parentNode.removeChild(contextMenu);
        }
        document.removeEventListener('touchstart', removeContextMenu);
    }, { once: true });
}

function downloadClip(filename) {
    if (filename) {
        window.open(`/clips/${filename}`, '_blank');
    }
}

function shareClip(filename) {
    if (navigator.share && filename) {
        navigator.share({
            title: 'FalconEye Clip',
            text: 'Check out this security clip',
            url: window.location.origin + `/clips/${filename}`
        });
    } else {
        // Fallback to copy link
        const url = window.location.origin + `/clips/${filename}`;
        navigator.clipboard.writeText(url).then(() => {
            showToast('Link copied to clipboard', 'success');
        });
    }
}
</script>
</body>
</html>
"""

@app.route("/")
@login_required
def dashboard():
    clips = load_metadata()
    status = {"device": DEVICE, "gpu": GPU_NAME if DEVICE == "cuda" else None}
    try:
        from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        aws_configured = bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_ACCESS_KEY_ID != "your_access_key_here")
        print(f"[CONFIG] AWS configured: {aws_configured}, Access Key: {AWS_ACCESS_KEY_ID[:10]}...")
    except ImportError:
        aws_configured = bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'))
        print(f"[CONFIG] Using environment variables, AWS configured: {aws_configured}")

    # Group by date
    dates = {}
    for name, data in clips.items():
        try:
            date = datetime.fromisoformat(data["timestamp"]).strftime("%Y-%m-%d")
        except:
            date = "Unknown"
        if date not in dates:
            dates[date] = []
        dates[date].append((name, data))

    # Sort clips within each date by timestamp (latest first)
    for date in dates:
        dates[date].sort(key=lambda x: x[1]["timestamp"], reverse=True)

    # All available dates
    all_dates = sorted(dates.keys(), reverse=True)

    # Default = today
    today = datetime.utcnow().strftime("%Y-%m-%d")
    selected_date = request.args.get("date", today)
    all_day_clips = dates.get(selected_date, [])
    
    # Pagination
    page = int(request.args.get("page", 1))
    clips_per_page = 10
    start_idx = (page - 1) * clips_per_page
    end_idx = start_idx + clips_per_page
    
    day_clips = all_day_clips[start_idx:end_idx]
    total_clips = len(all_day_clips)
    total_pages = (total_clips + clips_per_page - 1) // clips_per_page
    has_more = page < total_pages
    has_prev = page > 1

    return render_template_string(dashboard_html,
                                  status=status,
                                  all_dates=all_dates,
                                  selected_date=selected_date,
                                  day_clips=day_clips,
                                  aws_configured=aws_configured,
                                  format_clip_name=format_clip_name,
                                  page=page,
                                  total_pages=total_pages,
                                  has_more=has_more,
                                  has_prev=has_prev,
                                  total_clips=total_clips)

@app.route("/favicon.ico")
def favicon():
    """Serve favicon"""
    return send_file("static/favicon.ico", mimetype="image/x-icon")

@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    """Serve Apple touch icon"""
    return send_file("static/apple-touch-icon.png", mimetype="image/png")

@app.route("/apple-touch-icon-precomposed.png")
def apple_touch_icon_precomposed():
    """Serve Apple touch icon precomposed"""
    return send_file("static/apple-touch-icon-precomposed.png", mimetype="image/png")

@app.route("/static/logo_dark.png")
def logo_dark():
    """Serve dark theme logo"""
    return send_file("static/logo_dark.png", mimetype="image/png")

@app.route("/static/logo_light.png")
def logo_light():
    """Serve light theme logo"""
    return send_file("static/logo_light.png", mimetype="image/png")


@app.route("/retry-s3-uploads", methods=["POST"])
@login_required
def retry_s3_uploads():
    """Retry failed S3 uploads"""
    try:
        clips = load_metadata()
        retry_count = 0
        
        for filename, data in clips.items():
            if data.get("uploaded_to_s3") == False:
                file_path = os.path.join("clips", filename)
                if os.path.exists(file_path):
                    # Retry upload in background
                    threading.Thread(target=upload_to_s3, args=(file_path,)).start()
                    retry_count += 1
        
        return jsonify({"success": True, "count": retry_count, "message": f"Retrying {retry_count} uploads"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/test-s3-connection", methods=["POST"])
@login_required
def test_s3_connection():
    """Test S3 connection"""
    try:
        if s3 is None:
            return jsonify({"success": False, "error": "AWS credentials not configured"})
        
        # Test S3 connection by listing buckets
        s3.list_buckets()
        return jsonify({"success": True, "message": "S3 connection successful"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/login", methods=["GET", "POST"])
def login_page():
    error_message = ""
    if request.method == "POST":
        data = request.form or request.json or {}
        user = (data.get("username") or "").strip()
        pwd = data.get("password") or ""
        remember_me = data.get("remember_me", False)
        
        # Input validation
        if not user or not pwd:
            error_message = "Username and password are required."
        elif user in USERS and check_password_hash(USERS[user], pwd):
            session["user"] = user
            # Set session to persist longer if "Remember Me" is checked
            if remember_me:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(hours=12)  # Rest of the day
            else:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(hours=2)  # 2 hours
                
            next_url = request.args.get("next") or url_for("dashboard")
            if request.is_json:
                return jsonify({"status": "ok", "redirect": next_url})
            return redirect(next_url)
        else:
            # Always show same error message to prevent user enumeration
            # Use constant-time comparison to prevent timing attacks
            time.sleep(0.1)  # Small delay to prevent timing attacks
            error_message = "Invalid username or password. Please try again."
        
        if request.is_json:
            return jsonify({"status": "error", "message": error_message}), 401
    # Enhanced modern login form with animations and better UX
    error_html = ""
    if error_message:
        error_html = f"""
        <div class="error-message" style="background: rgba(244, 67, 54, 0.1); border: 1px solid #f44336; color: #f44336; padding: 12px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-size: 14px; animation: shake 0.5s ease-in-out;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="margin-right: 8px; vertical-align: middle;">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            {error_message}
        </div>
        """
    
    return """
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-primary: #0c0c0c;
            --bg-secondary: #1a1a1a;
            --bg-tertiary: #222;
            --text-primary: #eee;
            --text-secondary: #ccc;
            --text-muted: #999;
            --accent-primary: #0f9d58;
            --accent-secondary: #0a7d47;
            --accent-blue: #2196f3;
            --accent-red: #f44336;
            --border-color: rgba(255, 255, 255, 0.1);
            --shadow-light: rgba(0, 0, 0, 0.3);
            --shadow-medium: rgba(0, 0, 0, 0.5);
            --shadow-heavy: rgba(0, 0, 0, 0.7);
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
        }
        
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            overflow: hidden;
            position: relative;
        }
        
        /* Animated background particles */
        body::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(15, 157, 88, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(33, 150, 243, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(156, 39, 176, 0.1) 0%, transparent 50%);
            animation: backgroundShift 20s ease-in-out infinite;
        }
        
        @keyframes backgroundShift {
            0%, 100% { transform: translateX(0) translateY(0); }
            25% { transform: translateX(-20px) translateY(-10px); }
            50% { transform: translateX(20px) translateY(10px); }
            75% { transform: translateX(-10px) translateY(20px); }
        }
        
        .login-container {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            padding: 40px;
            border-radius: 24px;
            width: min(420px, 90vw);
            text-align: center;
            position: relative;
            z-index: 10;
            box-shadow: 
                0 20px 40px rgba(0, 0, 0, 0.4),
                0 0 0 1px rgba(255, 255, 255, 0.05),
                inset 0 1px 0 rgba(255, 255, 255, 0.1);
            animation: slideUp 0.6s ease-out;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .logo-container {
            margin-bottom: 32px;
            position: relative;
        }
        
        .login-logo {
            width: 80px;
            height: 80px;
            border-radius: 20px;
            box-shadow: 
                0 8px 32px rgba(15, 157, 88, 0.3),
                0 0 0 1px rgba(15, 157, 88, 0.2);
            transition: all 0.3s ease;
            animation: logoFloat 3s ease-in-out infinite;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3)) brightness(1.1) contrast(1.1);
            border: none;
            outline: none;
        }
        
        .login-logo:hover {
            transform: scale(1.05) rotate(2deg);
            box-shadow: 
                0 12px 40px rgba(15, 157, 88, 0.4),
                0 0 0 1px rgba(15, 157, 88, 0.3);
            filter: drop-shadow(0 8px 16px rgba(0, 0, 0, 0.4)) brightness(1.2) contrast(1.2);
        }
        
        @keyframes logoFloat {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-5px); }
        }
        
        .no-logo {
            width: 80px;
            height: 80px;
            border: 2px dashed rgba(15, 157, 88, 0.5);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin: 0 auto;
            background: linear-gradient(135deg, rgba(15, 157, 88, 0.1), rgba(15, 157, 88, 0.05));
            animation: logoFloat 3s ease-in-out infinite;
        }
        
        h3 {
            margin: 16px 0 32px 0;
            color: #fff;
            font-size: 28px;
            font-weight: 600;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #0f9d58, #4caf50);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .form-group {
            margin-bottom: 20px;
            position: relative;
        }
        
        .password-toggle-icon {
            position: absolute;
            right: 16px;
            top: 50%;
            transform: translateY(-50%);
            cursor: pointer;
            color: var(--text-secondary);
            transition: all 0.2s ease;
            z-index: 10;
            padding: 4px;
            border-radius: 4px;
        }
        
        .password-toggle-icon:hover {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.1);
        }
        
        #password {
            padding-right: 45px;
        }
        
        input {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            background: var(--bg-secondary);
            color: var(--text-primary);
            font-size: 16px;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        input:focus {
            outline: none;
            border-color: var(--accent-primary);
            background: var(--bg-tertiary);
            box-shadow: 
                0 0 0 3px var(--accent-primary),
                0 4px 20px var(--shadow-light);
            transform: translateY(-2px);
        }
        
        input::placeholder {
            color: var(--text-muted);
            font-weight: 400;
        }
        
        .remember-me {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 24px 0;
            gap: 12px;
        }
        
        .remember-me input[type="checkbox"] {
            width: 20px;
            height: 20px;
            margin: 0;
            accent-color: var(--accent-primary);
            cursor: pointer;
        }
        
        .remember-me label {
            font-size: 15px;
            color: var(--text-secondary);
            cursor: pointer;
            font-weight: 400;
            transition: color 0.3s ease;
        }
        
        .remember-me label:hover {
            color: #0f9d58;
        }
        
        button {
            width: 100%;
            padding: 16px 24px;
            border: none;
            border-radius: 12px;
            background: var(--accent-primary);
            color: #fff;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            margin: 8px 0;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }
        
        button:hover {
            background: var(--accent-secondary);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px var(--shadow-medium);
        }
        
        button:hover::before {
            left: 100%;
        }
        
        button:active {
            transform: translateY(0);
        }
        
        .error {
            color: #ff6b6b;
            margin: 12px 0;
            font-size: 14px;
            font-weight: 500;
            background: rgba(255, 107, 107, 0.1);
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid rgba(255, 107, 107, 0.2);
        }
        
        .success {
            color: #51cf66;
            margin: 12px 0;
            font-size: 14px;
            font-weight: 500;
            background: rgba(81, 207, 102, 0.1);
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid rgba(81, 207, 102, 0.2);
        }
        
        .security-badge {
            margin-top: 24px;
            padding: 12px;
            background: var(--glass-bg);
            border: 1px solid var(--accent-primary);
            border-radius: 8px;
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .security-badge::before {
            content: '🔒 ';
            margin-right: 4px;
        }
        
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        
        /* Mobile responsiveness */
        @media (max-width: 480px) {
            .login-container {
                padding: 32px 24px;
                margin: 20px;
            }
            
            h3 {
                font-size: 24px;
            }
            
            .login-logo {
                width: 64px;
                height: 64px;
            }
        }
    </style>
    <div class='login-container'>
        <div class='logo-container'>
            <img id="login-logo" src='/static/logo_dark.png' alt='FalconEye' class="login-logo">
        </div>
        <h3>FalconEye</h3>
        """ + error_html + """
        <form method='post'>
            <div class="form-group">
                <input type='text' name='username' placeholder='Username' required autocomplete='username'>
            </div>
            <div class="form-group">
                <input type='password' name='password' id='password' placeholder='Password' required autocomplete='current-password' onfocus='showPasswordToggle()' onblur='hidePasswordToggle()'>
                <span class='password-toggle-icon' onclick='togglePassword()' style='display: none;'>
                    <svg class='eye-icon' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'>
                        <path d='M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z'/>
                        <circle cx='12' cy='12' r='3'/>
                    </svg>
                    <svg class='eye-off-icon' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' style='display: none;'>
                        <path d='M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24'/>
                        <line x1='1' y1='1' x2='23' y2='23'/>
                    </svg>
                </span>
            </div>
            <div class="remember-me">
                <input type='checkbox' name='remember_me' id='remember_me' />
                <label for='remember_me'>Remember me for this session</label>
            </div>
            <button type='submit'>Access Dashboard</button>
        </form>
        <div class="security-badge">
            Secure surveillance system • Encrypted connection
    </div>
    </div>
    
    <script>
    function showPasswordToggle() {
        const toggleIcon = document.querySelector('.password-toggle-icon');
        if (toggleIcon) {
            toggleIcon.style.display = 'block';
        }
    }
    
    function hidePasswordToggle() {
        const toggleIcon = document.querySelector('.password-toggle-icon');
        const passwordInput = document.getElementById('password');
        // Only hide if password field is empty
        if (passwordInput && passwordInput.value === '') {
            toggleIcon.style.display = 'none';
        }
    }
    
    function togglePassword() {
        const passwordInput = document.getElementById('password');
        const eyeIcon = document.querySelector('.eye-icon');
        const eyeOffIcon = document.querySelector('.eye-off-icon');
        
        if (passwordInput && eyeIcon && eyeOffIcon) {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeIcon.style.display = 'none';
                eyeOffIcon.style.display = 'block';
            } else {
                passwordInput.type = 'password';
                eyeIcon.style.display = 'block';
                eyeOffIcon.style.display = 'none';
            }
        }
    }
    
    // Add event listeners when the page loads
    document.addEventListener('DOMContentLoaded', function() {
        const passwordInput = document.getElementById('password');
        const toggleIcon = document.querySelector('.password-toggle-icon');
        
        if (passwordInput && toggleIcon) {
            // Show toggle when typing in password field
            passwordInput.addEventListener('input', function() {
                if (this.value.length > 0) {
                    toggleIcon.style.display = 'block';
                } else {
                    toggleIcon.style.display = 'none';
                }
            });
            
            // Ensure toggle is visible when password field has focus
            passwordInput.addEventListener('focus', function() {
                toggleIcon.style.display = 'block';
            });
            
            // Hide toggle when password field loses focus and is empty
            passwordInput.addEventListener('blur', function() {
                if (this.value === '') {
                    toggleIcon.style.display = 'none';
                }
            });
        }
    });
    </script>
    """

@app.route("/logout")
def logout_page():
    session.pop("user", None)
    return redirect(url_for("login_page"))

# ---------------- API Endpoints ----------------
@app.route("/auth/login", methods=["POST"])
def login():
    """API endpoint for mobile app login"""
    data = request.json or {}
    user = (data.get("username") or "").strip()
    pwd = data.get("password") or ""
    
    # Input validation
    if not user or not pwd:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400
    
    # Check credentials with timing attack prevention
    if user in USERS and check_password_hash(USERS[user], pwd):
        session["user"] = user
        session.permanent = data.get("remember_me", False)
        if session.permanent:
            app.permanent_session_lifetime = timedelta(hours=12)
        return jsonify({"status": "ok", "device": DEVICE})
    else:
        # Prevent timing attacks
        time.sleep(0.1)
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route("/camera/list")
def list_cameras():
    return jsonify({"cameras": list(CAMERAS.keys())})

@app.route("/vision/settings", methods=["GET", "POST"])
def vision_settings():
    global VISION_SETTINGS
    if request.method == "GET":
        return jsonify(VISION_SETTINGS)
    try:
        data = request.json or {}
        # Merge and clamp keys
        VISION_SETTINGS = _merge_vision_settings(VISION_SETTINGS, data)
        save_vision_settings()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/camera/snapshot/<cam_id>")
def snapshot(cam_id):
    if cam_id not in CAMERAS: return "Invalid camera", 404
    frame = get_frame(CAMERAS[cam_id])
    if frame is None: 
        # Return a placeholder image when camera is not available
        placeholder = create_test_image()
        camera_type = "Pi Zero MJPEG" if ":8081" in CAMERAS[cam_id] else "ESP32"
        cv2.putText(placeholder, f"{camera_type} Camera Offline", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, buffer = cv2.imencode(".jpg", placeholder)
        return Response(buffer.tobytes(), mimetype="image/jpeg")
    
    results = model(frame, verbose=False)
    annotated = frame.copy()
    # Draw boxes + labels (filtered to surveillance classes) on snapshots too
    if results[0].boxes:
        boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes.xyxy is not None else []
        clses = results[0].boxes.cls.tolist() if results[0].boxes.cls is not None else []
        confs = results[0].boxes.conf.tolist() if results[0].boxes.conf is not None else []
        names = [model.names[int(c)] for c in clses]
        # Compute per-box face names if enabled
        face_names_by_idx = {}
        if VISION_SETTINGS.get('faces', {}).get('enabled', True):
            try:
                person_boxes = [boxes[i] for i, nm in enumerate(names) if nm == 'person']
                tol = float(VISION_SETTINGS.get('faces', {}).get('tolerance', 0.6))
                mapping = recognize_faces_for_boxes(frame, person_boxes, tolerance=tol)
                # Map back to full index space
                pi = 0
                for i, nm in enumerate(names):
                    if nm == 'person':
                        if pi in mapping:
                            face_names_by_idx[i] = mapping[pi]
                        pi += 1
            except Exception:
                face_names_by_idx = {}
        for i, name in enumerate(names):
            if name not in SURVEILLANCE_OBJECTS or not is_class_enabled(name):
                continue
            if i >= len(boxes):
                continue
            x1, y1, x2, y2 = boxes[i]
            color = class_color_bgr(name)
            if VISION_SETTINGS.get('show_boxes', True):
                cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            if VISION_SETTINGS.get('show_labels', True):
                if name == 'person' and i in face_names_by_idx:
                    label_text = face_names_by_idx[i]
                else:
                    label_text = f"{name} {(confs[i]*100):.0f}%" if i < len(confs) else name
                (tw, th), bl = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                ty1 = max(int(y1) - th - 6, 0)
                cv2.rectangle(annotated, (int(x1), ty1), (int(x1)+tw+6, ty1+th+6), (0, 0, 0), -1)
                cv2.putText(annotated, label_text, (int(x1)+3, ty1+th+2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    # Show only filtered surveillance objects in overlay text
    if results[0].boxes:
        all_objects = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
        objects = filter_surveillance_objects(all_objects)
        if objects:
            cv2.putText(annotated, f"Detected: {', '.join(objects)}", (10, 65), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    # Add camera info and FPS to snapshot
    camera_type = "Pi Zero MJPEG" if ":8081" in CAMERAS[cam_id] else "ESP32"
    cv2.putText(annotated, f"{camera_type} Snapshot", (10, 25), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(annotated, "FalconEye AI Detection", (10, 45), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    _, buffer = cv2.imencode(".jpg", annotated)
    return Response(buffer.tobytes(), mimetype="image/jpeg")

@app.route("/camera/live/<cam_id>")
def live(cam_id):
    if cam_id not in CAMERAS: return "Invalid camera", 404
    
    # Check if mobile device based on User-Agent
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad', 'ipod'])
    
    # Optional passthrough mode for true MJPEG streams (no re-encode)
    passthrough = request.args.get('mode') == 'passthrough'

    def gen():
        frame_count = 0
        last_sent_frame = None
        camera_url = CAMERAS[cam_id]
        camera_type = "Pi Zero MJPEG" if ":8081" in camera_url else "ESP32"
        
        # For Pi Zero MJPEG, allow passthrough for highest smoothness
        if ":8081" in camera_url:
            print(f"[STREAM] Using MJPEG stream for {cam_id}")
            if passthrough:
                # Raw proxy without decoding/re-encoding
                try:
                    with requests.get(camera_url, timeout=5, stream=True) as r:
                        if r.status_code != 200:
                            raise RuntimeError(f"Upstream status {r.status_code}")
                        boundary = None
                        ctype = r.headers.get('Content-Type', '')
                        if 'boundary=' in ctype:
                            boundary = ctype.split('boundary=')[-1]
                        boundary = boundary or 'frame'
                        yield (b'')
                        for chunk in r.iter_content(chunk_size=16384):
                            if not chunk:
                                continue
                            # We just forward chunks; client expects multipart stream
                            # Ensure boundary framing if upstream omits headers (rare)
                            # Most MJPEG servers include correct multipart headers.
                            yield chunk
                except Exception as e:
                    print(f"[STREAM] Passthrough error: {e}")
                    placeholder = create_test_image()
                    cv2.putText(placeholder, f"Passthrough Error", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    _, buffer = cv2.imencode('.jpg', placeholder)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                return
            else:
                try:
                    for frame_data in gen_mjpeg_live_stream(cam_id, is_mobile):
                        yield frame_data
                except Exception as e:
                    print(f"[STREAM] Error in MJPEG stream: {e}")
                    # Fallback to test image
                    placeholder = create_test_image()
                    cv2.putText(placeholder, f"Pi Zero Stream Error: {str(e)[:30]}", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    _, buffer = cv2.imencode('.jpg', placeholder)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                return
        
        # For faces overlay sampling
        faces_overlay_text = ""
        sample_every = int(VISION_SETTINGS.get('faces', {}).get('sample_every', 10) or 10)
        skip_detection = request.args.get('skip_detection') == '1'
        # Use a higher default detect_every for smoother live streams.
        detect_every = int(request.args.get('detect_every', 20))
        while True:
            frame = get_frame(camera_url)
            
            if frame is None:
                # If no frame available, wait briefly and try again
                time.sleep(0.1)
                continue
            
            # Only process if we have a new frame
            if frame is not last_sent_frame:
                # Resize frame for mobile to reduce bandwidth
                if is_mobile:
                    height, width = frame.shape[:2]
                    # Resize to max 480 width for mobile to improve smoothness
                    if width > 480:
                        scale = 480 / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height))
                
                # Perform object detection on the frame (raw, no compression)
                results = None
                do_detect = not skip_detection or (frame_count % max(1, detect_every) == 0)
                if do_detect:
                    results = live_model(frame, verbose=False)
                # Annotate with boxes and per-object labels (filtered)
                annotated = frame.copy()
                if results is not None and results[0].boxes:
                    boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes.xyxy is not None else []
                    clses = results[0].boxes.cls.tolist() if results[0].boxes.cls is not None else []
                    confs = results[0].boxes.conf.tolist() if results[0].boxes.conf is not None else []
                    names = [model.names[int(c)] for c in clses]
                    # Compute per-box face names if enabled
                    face_names_by_idx = {}
                    if VISION_SETTINGS.get('faces', {}).get('enabled', True):
                        try:
                            if DISABLE_FACE_RECOGNITION:
                                # Skip expensive face recognition when disabled
                                face_names_by_idx = {}
                            else:
                                person_boxes = [boxes[i] for i, nm in enumerate(names) if nm == 'person']
                                tol = float(VISION_SETTINGS.get('faces', {}).get('tolerance', 0.6))
                                mapping = recognize_faces_for_boxes(frame, person_boxes, tolerance=tol)
                                # Map back to full index space
                                pi = 0
                                for i, nm in enumerate(names):
                                    if nm == 'person':
                                        if pi in mapping:
                                            face_names_by_idx[i] = mapping[pi]
                                        pi += 1
                        except Exception:
                            face_names_by_idx = {}
                    for i, name in enumerate(names):
                        if name not in SURVEILLANCE_OBJECTS or not is_class_enabled(name):
                            continue
                        if i >= len(boxes):
                            continue
                        x1, y1, x2, y2 = boxes[i]
                        color = class_color_bgr(name)
                        if VISION_SETTINGS.get('show_boxes', True):
                            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                        if VISION_SETTINGS.get('show_labels', True):
                            if name == 'person' and i in face_names_by_idx:
                                label_text = face_names_by_idx[i]
                            else:
                                label_text = f"{name} {(confs[i]*100):.0f}%" if i < len(confs) else name
                            label = label_text
                            (tw, th), bl = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5 if is_mobile else 0.6, 1 if is_mobile else 2)
                            ty1 = max(int(y1) - th - 6, 0)
                            cv2.rectangle(annotated, (int(x1), ty1), (int(x1)+tw+6, ty1+th+6), (0, 0, 0), -1)
                            cv2.putText(annotated, label, (int(x1)+3, ty1+th+2), cv2.FONT_HERSHEY_SIMPLEX, 0.5 if is_mobile else 0.6, (255, 255, 255), 1 if is_mobile else 2)
                # Faces overlay (sampled)
                if results is not None and VISION_SETTINGS.get('faces', {}).get('enabled', True):
                    if frame_count % max(1, sample_every) == 0:
                        try:
                            if DISABLE_FACE_RECOGNITION:
                                faces_overlay_text = ""
                            else:
                                person_boxes = []
                                if results and results[0].boxes is not None:
                                    bxyxy = results[0].boxes.xyxy.cpu().numpy()
                                    cl = results[0].boxes.cls.tolist()
                                    for i, ci in enumerate(cl):
                                        if model.names[int(ci)] == 'person':
                                            person_boxes.append(bxyxy[i])
                                tol = float(VISION_SETTINGS.get('faces', {}).get('tolerance', 0.6))
                                names = recognize_faces_in_frame(frame, person_boxes, tolerance=tol)
                                faces_overlay_text = ", ".join(names[:3]) if names else ""
                        except Exception:
                            faces_overlay_text = ""
                
                # Add status text to the frame (smaller for mobile)
                font_scale = 0.4 if is_mobile else 0.6
                thickness = 1 if is_mobile else 2
                
                # Calculate FPS
                current_time = time.time()
                if not hasattr(gen, 'last_time'):
                    gen.last_time = current_time
                    gen.frame_times = []
                
                gen.frame_times.append(current_time)
                if len(gen.frame_times) > 30:  # Keep last 30 frames
                    gen.frame_times.pop(0)
                
                if len(gen.frame_times) > 1:
                    fps = len(gen.frame_times) / (gen.frame_times[-1] - gen.frame_times[0])
                    fps_text = f"{camera_type} Live - FPS: {fps:.1f} - Frame: {frame_count}"
                else:
                    fps_text = f"{camera_type} Live - Frame: {frame_count}"
                
                cv2.putText(annotated, fps_text, (10, 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                cv2.putText(annotated, "FalconEye AI Detection", (10, 45), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness)
                
                # Show detected objects (filtered for surveillance) summary line
                if results is not None and results[0].boxes and VISION_SETTINGS.get('show_summary', True):
                    all_objects = [model.names[int(c)] for c in results[0].boxes.cls.tolist()]
                    objects = filter_surveillance_objects(all_objects)
                    if objects:  # Only show if there are relevant objects
                        cv2.putText(annotated, f"Detected: {', '.join(objects)}", (10, 65),
                                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)
                # Faces overlay line
                if faces_overlay_text and VISION_SETTINGS.get('faces', {}).get('overlay', True):
                    cv2.putText(annotated, f"Faces: {faces_overlay_text}", (10, 85),
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 200, 0), thickness)
                
                # Encode as JPEG with different quality for mobile
                quality = 70 if is_mobile else 85
                _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, quality])
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
                
                last_sent_frame = frame
                frame_count += 1
                
                # Print status every 100 frames
                if frame_count % 100 == 0:
                    print(f"[LIVE STREAM] Streamed {frame_count} frames from {camera_type} (Mobile: {is_mobile})")
            
            # Adjust FPS based on device type (allow override)
            try:
                override = float(request.args.get('sleep', '')) if request else None
            except Exception:
                override = None
            sleep_time = override if override is not None else (0.2 if not is_mobile else 0.25)
            time.sleep(max(0.0, sleep_time))
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ---------------- Camera Pan/Tilt Controls (PTZ) ----------------
@app.route("/camera/pan/<action>", methods=["POST"])  # action: left|right|auto
def camera_pan(action):
    """Proxy pan commands to the ESP pan/tilt controller.
    Updated to use new API structure: /move?dir=
    """
    # Fix inverted pan directions - swap left/right
    valid_actions = {"left": "right", "right": "left", "auto": "auto"}
    action = action.lower()
    if action not in valid_actions:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

    try:
        # Forward to ESP pan/tilt unit with new API structure
        target_url = f"{ESP_PAN_BASE_URL}/move?dir={valid_actions[action]}"
        resp = requests.get(target_url, timeout=3)
        ok = 200 <= resp.status_code < 300
        return jsonify({
            "status": "success" if ok else "error",
            "code": resp.status_code,
            "target": target_url
        }), (200 if ok else 502)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 502

@app.route("/camera/tilt/<action>", methods=["POST"])  # action: up|down|auto
def camera_tilt(action):
    """Proxy tilt commands to the ESP pan/tilt controller.
    Updated to use new API structure: /tilt?dir=
    """
    # Use directions directly (no swap needed)
    valid_actions = {"up": "up", "down": "down", "auto": "auto"}
    action = action.lower()
    if action not in valid_actions:
        return jsonify({"status": "error", "message": "Invalid action"}), 400

    try:
        # Forward to ESP pan/tilt unit with new API structure
        target_url = f"{ESP_PAN_BASE_URL}/tilt?dir={valid_actions[action]}"
        resp = requests.get(target_url, timeout=3)
        ok = 200 <= resp.status_code < 300
        return jsonify({
            "status": "success" if ok else "error",
            "code": resp.status_code,
            "target": target_url,
            "direction_sent_to_esp": valid_actions[action],
            "button_pressed": action
        }), (200 if ok else 502)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 502

@app.route("/camera/move", methods=["POST"])
def camera_move():
    """Combined pan/tilt control endpoint for convenience.
    Updated to use new API structure: /move?dir= for pan, /tilt?dir= for tilt
    """
    try:
        data = request.json or {}
        axis = data.get("axis", "").lower()
        direction = data.get("dir", "").lower()
        
        if axis not in ["pan", "tilt"]:
            return jsonify({"status": "error", "message": "Invalid axis. Use 'pan' or 'tilt'"}), 400
            
        if axis == "pan":
            valid_dirs = {"left": "left", "right": "right", "auto": "auto"}
            # Forward to ESP pan/tilt unit with new API structure
            target_url = f"{ESP_PAN_BASE_URL}/move?dir={valid_dirs[direction]}"
        else:  # tilt - fix inverted directions
            valid_dirs = {"up": "down", "down": "up", "auto": "auto"}
            # Forward to ESP pan/tilt unit with new API structure
            target_url = f"{ESP_PAN_BASE_URL}/tilt?dir={valid_dirs[direction]}"
            
        if direction not in valid_dirs:
            return jsonify({"status": "error", "message": f"Invalid direction for {axis}. Use: {list(valid_dirs.keys())}"}), 400

        resp = requests.get(target_url, timeout=3)
        ok = 200 <= resp.status_code < 300
        return jsonify({
            "status": "success" if ok else "error",
            "code": resp.status_code,
            "target": target_url,
            "axis": axis,
            "direction": valid_dirs[direction]
        }), (200 if ok else 502)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 502

@app.route("/camera/controls/status", methods=["GET"])
def camera_controls_status():
    """Get status of camera control system."""
    try:
        # Test if ESP pan/tilt controller is reachable using new API structure
        test_url = f"{ESP_PAN_BASE_URL}/move?dir=auto"
        resp = requests.get(test_url, timeout=2)
        controller_online = 200 <= resp.status_code < 300

        return jsonify({
            "status": "success",
            "controller_online": controller_online,
            "esp_pan_base_url": ESP_PAN_BASE_URL,
            "available_controls": {
                "pan": ["left", "right", "auto"],
                "tilt": ["up", "down", "auto"]
            },
            "endpoints": {
                "pan": "/camera/pan/<action>",
                "tilt": "/camera/tilt/<action>",
                "combined": "/camera/move"
            },
            "esp_api_structure": {
                "pan": "/move?dir=",
                "tilt": "/tilt?dir="
            }
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "controller_online": False,
            "esp_pan_base_url": ESP_PAN_BASE_URL,
            "error": str(e)
        }), 502

@app.route("/clips")
def list_clips():
    clips = load_metadata()
    
    # Add thumbnail URLs to each clip
    for filename, data in clips.items():
        base_name = os.path.splitext(filename)[0]
        thumbnail_filename = f"{base_name}_thumb.jpg"
        thumbnail_path = os.path.join(OUTPUT_DIR, thumbnail_filename)
        
        if os.path.exists(thumbnail_path):
            data["thumbnail_url"] = f"/clips/thumbnails/{thumbnail_filename}"
        else:
            data["thumbnail_url"] = None
    
    return jsonify(clips)

@app.route("/clips/<filename>")
@login_required
def download_clip(filename):
    """Serve recorded clips from local storage"""
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

@app.route("/clips/thumbnails/<filename>")
def serve_thumbnail(filename):
    """Serve thumbnail images"""
    return send_from_directory(OUTPUT_DIR, filename)

@app.route("/notify/test", methods=["POST"])
def notify_test():
    data = request.json
    token = data.get("token")
    send_push_notification("Test Alert", "This is a test", token)
    return jsonify({"status": "sent"})

@app.route("/system/status")
def system_status():
    try:
        faces_enabled = bool(VISION_SETTINGS.get('faces', {}).get('enabled', True))
        faces_info = {
            "enabled": faces_enabled,
            "runtime_disabled": bool(FACES_RUNTIME_DISABLED),
            "insight_available": bool(insight_available()) if 'insight_available' in globals() else False,
            "db_count": len(face_encodings_db or {})
        }
    except Exception:
        faces_info = {"enabled": True, "runtime_disabled": False, "insight_available": False, "db_count": 0}
    return jsonify({
        "device": DEVICE,
        "gpu": GPU_NAME if DEVICE == "cuda" else None,
        "network_profile": {
            "active": ACTIVE_PROFILE.get("name"),
            "cameras": CAMERAS,
            "esp_pan_base": ESP_PAN_BASE_URL
        },
        "faces": faces_info
    })

@app.route("/network/profiles", methods=["GET"])
def network_profiles_list():
    try:
        return jsonify({
            "active": ACTIVE_PROFILE.get("name"),
            "profiles": NETWORK_PROFILES,
            "cameras": CAMERAS,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/network/profile", methods=["POST"])
def network_profile_set():
    try:
        data = request.json or {}
        name = data.get("name")
        cams = data.get("cameras")
        pan = data.get("esp_pan_base")
        global ACTIVE_PROFILE, CAMERAS, ESP_PAN_BASE_URL
        if name:
            # Find by name
            match = None
            for p in NETWORK_PROFILES:
                if p.get("name") == name:
                    match = p
                    break
            if not match:
                return jsonify({"status": "error", "message": f"profile '{name}' not found"}), 404
            ACTIVE_PROFILE = match
            CAMERAS = match.get("cameras", {}).copy()
            ESP_PAN_BASE_URL = match.get("esp_pan_base", ESP_PAN_BASE_URL)
        elif cams:
            # Direct override
            CAMERAS.update(cams)
            ACTIVE_PROFILE = {"name": "runtime_override", "cameras": CAMERAS.copy(), "esp_pan_base": ESP_PAN_BASE_URL}
            if pan:
                ESP_PAN_BASE_URL = pan
        else:
            return jsonify({"status": "error", "message": "provide 'name' or 'cameras'"}), 400
        return jsonify({"status": "ok", "active": ACTIVE_PROFILE.get("name"), "cameras": CAMERAS, "esp_pan_base": ESP_PAN_BASE_URL})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Mobile-specific API endpoints
@app.route("/mobile/status")
def mobile_status():
    """Mobile-optimized status endpoint"""
    return jsonify({
        "status": "online",
        "device": DEVICE,
        "surveillance_objects": list(SURVEILLANCE_OBJECTS),
        "features": {
            "live_stream": True,
            "object_detection": True,
            "video_recording": True,
            "push_notifications": True,
            "mobile_optimized": True
        }
    })

@app.route("/mobile/clips/summary")
def mobile_clips_summary():
    """Mobile-optimized clips summary"""
    clips = load_metadata()
    
    # Group by date and count
    dates = {}
    for name, data in clips.items():
        try:
            date = datetime.fromisoformat(data["timestamp"]).strftime("%Y-%m-%d")
        except:
            date = "Unknown"
        if date not in dates:
            dates[date] = {"count": 0, "objects": set()}
        dates[date]["count"] += 1
        if data.get("tags"):
            dates[date]["objects"].update(data["tags"])
    
    # Convert to mobile-friendly format
    summary = []
    for date, info in sorted(dates.items(), reverse=True):
        summary.append({
            "date": date,
            "count": info["count"],
            "objects": list(info["objects"])[:5]  # Limit to 5 most common objects
        })
    
    return jsonify({"clips_by_date": summary})

@app.route("/mobile/camera/info")
def mobile_camera_info():
    """Mobile camera information"""
    return jsonify({
        "cameras": list(CAMERAS.keys()),
        "live_url": "/camera/live/cam1",
        "snapshot_url": "/camera/snapshot/cam1",
        "mobile_optimized": True,
        "bandwidth_saving": True
    })

@app.route("/mobile/detections/recent")
def mobile_detections_recent():
    """Return a small buffer of recent detections for overlays"""
    return jsonify(list(recent_detections))

@app.route("/mobile/test-push", methods=["POST"])
def mobile_test_push():
    """Send a test push notification"""
    try:
        data = request.json or {}
        test_mode = data.get('test', False)
        
        if test_mode:
            # Send test notification to all registered devices
            send_push_notification(
                "FalconEye Test", 
                "This is a test notification from your security system",
                token=None,  # Send to all registered devices
                detected_objects=["test"]
            )
            return jsonify({"status": "success", "message": "Test notification sent"})
        else:
            return jsonify({"status": "error", "message": "Invalid test request"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# FCM Token Management
@app.route("/fcm/register", methods=["POST"])
def register_token():
    """Register FCM token for push notifications"""
    data = request.json
    token = data.get("token")
    
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 400
    
    result = register_fcm_token(token)
    return jsonify(result)

@app.route("/fcm/unregister", methods=["POST"])
def unregister_token():
    """Unregister FCM token"""
    data = request.json
    token = data.get("token")
    
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 400
    
    result = unregister_fcm_token(token)
    return jsonify(result)

@app.route("/device/register", methods=["POST"])
def register_device_token():
    """Register device token for APNs push notifications"""
    data = request.json
    token = data.get("token")
    
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 400
    
    result = register_device_token_simple(token)
    return jsonify(result)

@app.route("/device/test-notification", methods=["POST"])
def test_device_notification():
    """Send test notification to all registered devices"""
    send_push_notification(
        "FalconEye Test", 
        "This is a test notification from your security system",
        token=None,  # Send to all registered devices
        detected_objects=["test"]
    )
    return jsonify({"status": "success", "message": "Test notification sent"})

@app.route("/fcm/test", methods=["POST"])
def test_notification():
    """Send test notification"""
    data = request.json
    token = data.get("token")
    
    # Use the new notification service
    success = send_test_notification()
    
    # Log the result for debugging
    print(f"🔍 Test notification result: {success}")
    print(f"🔍 Registered devices: {len(notification_service.registered_devices)}")
    
    if success:
        return jsonify({"status": "success", "message": "Test notification sent"})
    else:
        return jsonify({"status": "error", "message": "Failed to send test notification"}), 500

@app.route("/fcm/status")
def fcm_status():
    """Get notification status and registered devices count"""
    status = get_notification_status()
    print(f"🔍 Backend Local notification status: {status}")
    return jsonify(status)

@app.route("/mobile/register", methods=["POST"])
def mobile_register():
    """Register mobile device for notifications"""
    data = request.json
    device_id = data.get("device_id")
    
    if not device_id:
        return jsonify({"error": "device_id required"}), 400
    
    success = notification_service.register_device(device_id)
    
    if success:
        return jsonify({"status": "success", "message": "Device registered"})
    else:
        return jsonify({"status": "error", "message": "Failed to register device"}), 500

@app.route("/mobile/unregister", methods=["POST"])
def mobile_unregister():
    """Unregister mobile device"""
    data = request.json
    device_id = data.get("device_id")
    
    if not device_id:
        return jsonify({"error": "device_id required"}), 400
    
    success = notification_service.unregister_device(device_id)
    
    if success:
        return jsonify({"status": "success", "message": "Device unregistered"})
    else:
        return jsonify({"status": "error", "message": "Failed to unregister device"}), 500

@app.route("/mobile/notifications", methods=["GET"])
def get_notifications():
    """Get pending notifications for a device"""
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({"error": "device_id required"}), 400
    
    # Get notifications from the local notification service
    notifications = []
    
    # Get stored notifications from the local notification service
    stored_notifications = notification_service.get_stored_notifications(device_id)
    for stored_notif in stored_notifications:
        # Only include notifications from the last 2 minutes to avoid spam
        notif_time = datetime.fromtimestamp(stored_notif['timestamp'])
        time_diff = (datetime.now() - notif_time).total_seconds()
        if time_diff < 120:  # 2 minutes instead of 5 minutes
            notifications.append({
                "id": stored_notif['id'] if 'id' in stored_notif else f"stored_{stored_notif['timestamp']}",
                "title": stored_notif['title'],
                "body": stored_notif['body'],
                "data": stored_notif.get('data', {}),
                "sound": stored_notif.get('sound', 'default'),
                "badge": stored_notif.get('badge', 1)
            })
    
    print(f"📱 Returning {len(notifications)} notifications for device {device_id}")
    
    # Clear the stored notifications after returning them (so they don't spam)
    notification_service.clear_stored_notifications(device_id)
    
    return jsonify({
        "notifications": notifications,
        "count": len(notifications)
    })

# ---------------- Faces API ----------------
@app.route("/faces", methods=["GET"])
def faces_list():
    try:
        return jsonify({
            "faces": sorted(list(face_encodings_db.keys())),
            "count": len(face_encodings_db)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/faces/status", methods=["GET"])
def faces_status():
    try:
        return jsonify({
            "enabled": bool(VISION_SETTINGS.get('faces', {}).get('enabled', True)),
            "runtime_disabled": bool(FACES_RUNTIME_DISABLED),
            "insight_available": bool(insight_available()) if 'insight_available' in globals() else False,
            "face_recognition_available": face_recognition is not None,
            "registered_names": sorted(list(face_encodings_db.keys())),
            "registered_count": len(face_encodings_db)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/faces/enable", methods=["POST"])
def faces_enable():
    try:
        data = request.json if request.is_json else {}
        enabled = data.get("enabled")
        if enabled is None:
            q = request.args.get("enabled") or request.args.get("e") or request.args.get("on")
            if q is not None:
                enabled = str(q).strip().lower() in ("1", "true", "yes", "on")
        if enabled is None:
            return jsonify({"error": "'enabled' boolean required"}), 400
        VISION_SETTINGS.setdefault('faces', {})['enabled'] = bool(enabled)
        # Clear runtime disable if explicitly enabling
        global FACES_RUNTIME_DISABLED
        if bool(enabled):
            FACES_RUNTIME_DISABLED = False
        save_vision_settings()
        return jsonify({"status": "ok", "enabled": bool(enabled)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/faces/register", methods=["POST"])
def faces_register():
    if face_recognition is None:
        return jsonify({"error": "face_recognition module not available"}), 500
    data = request.json if request.is_json else None
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    name = (data.get("name") or "").strip()
    image_b64 = data.get("image_base64")
    if not name:
        return jsonify({"error": "name required"}), 400
    if not image_b64:
        return jsonify({"error": "image_base64 required"}), 400
    try:
        # Check if face recognition is disabled
        if DISABLE_FACE_RECOGNITION:
            return jsonify({"error": "Face recognition is disabled. Set FALCONEYE_DISABLE_FACE_RECOGNITION=0 or remove it from environment to enable."}), 400
        if FACES_RUNTIME_DISABLED:
            return jsonify({"error": "Face recognition is currently disabled due to runtime errors. Check server logs for details."}), 400
        
        img_bytes = base64.b64decode(image_b64.split(",")[-1])
        img_arr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if image is None:
            return jsonify({"error": "invalid image"}), 400
        encs = compute_face_encodings_from_image(image)
        if not encs:
            return jsonify({"error": "no face detected in image. Please ensure the image contains a clear, front-facing face."}), 400
        # Use first face
        ok, msg = register_face_encoding(name, encs[0])
        return jsonify({"success": ok, "message": msg, "name": name, "faces": len(face_encodings_db.get(name, []))})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/faces/recognize", methods=["POST"])
def faces_recognize():
    data = request.json if request.is_json else None
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    image_b64 = data.get("image_base64")
    tol = float(data.get("tolerance", VISION_SETTINGS.get('faces', {}).get('tolerance', 0.6)))
    if not image_b64:
        return jsonify({"error": "image_base64 required"}), 400
    try:
        img_bytes = base64.b64decode(image_b64.split(",")[-1])
        img_arr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
        if image is None:
            return jsonify({"error": "invalid image"}), 400
        names = recognize_faces_in_frame(image, person_boxes_xyxy=None, tolerance=tol)
        return jsonify({"recognized": names, "count": len(names)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/faces/delete", methods=["POST"])
def faces_delete():
    data = request.json if request.is_json else None
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    if name not in face_encodings_db:
        return jsonify({"error": "name not found"}), 404
    try:
        del face_encodings_db[name]
        save_face_db()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🚀 Starting FalconEye on http://localhost:3001")
    print("📱 Dashboard: http://localhost:3001")
    print("🔗 Remote access: https://cam.falconeye.website (when Cloudflare tunnel is running)")
    
    # Start background frame capture
    if not TEST_MODE:
        threading.Thread(target=capture_frames_background, daemon=True).start()
        time.sleep(2)  # Wait for first frame
    
    # Start detection loop
    for cam_id, url in CAMERAS.items():
        threading.Thread(target=detect_and_record, args=(cam_id, url), daemon=True).start()
    
    # Comment out local preview for headless operation
    # threading.Thread(target=local_preview, args=("cam1", CAMERAS["cam1"]), daemon=True).start()
    
    app.run(host="0.0.0.0", port=3001)