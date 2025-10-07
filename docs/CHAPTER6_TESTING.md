# Chapter 6 — Testing

## 6.1 Feasibility Study
The feasibility study validates that FalconEye can be implemented, deployed, and maintained within realistic constraints while delivering value.

- Economic Feasibility: Low-cost ESP32‑CAM and Raspberry Pi; event‑driven clips reduce storage; open‑source stack (YOLOv8, OpenCV, Flask); pay‑as‑you‑go cloud. Suitable for homes, institutions, and SMEs.
- Technical Feasibility: Compatible with ESP32 snapshot and Pi Zero MJPEG; YOLOv8 on Apple Silicon (MPS) or CPU; Cloudflare Tunnel for secure remote access; mature Python libs (OpenCV, requests, boto3).
- Social Feasibility: Simple web UI and mobile access; transparent alerts with annotated snapshots; role‑based access and privacy controls; positive community safety impact.

Conclusion: FalconEye is economically viable, technically sound, and socially acceptable for intended users.

## 6.2 System Testing
End‑to‑end validation confirms the integrated flow works under diverse conditions: camera capture → YOLOv8 inference → event filtering → clip generation → cloud upload → notification.
Goals:
- Find and fix defects before deployment.
- Verify behavior across day/night, indoor/outdoor scenes.
- Validate robustness, scalability, and latency.

## 6.3 Types of Tests
- Unit Testing: Camera capture stability; YOLOv8 class inference; face summary overlay; clip generation (10–15s MP4 + JSON); upload routines.
- Integration Testing: Camera → Edge AI → Event Filter → Clip → Upload → Notify, with synchronized timestamps and camera IDs.
- Functional Testing: Valid vs invalid inputs, event‑driven recording, secure cloud retrieval, alert payloads with snapshot + metadata.
- Acceptance Testing: Real users accessed live views, registered faces, and evaluated alert timeliness and relevance.

## 6.4 Test Objectives
- Stream stability for ESP32 snapshot and Pi Zero MJPEG.
- Detection accuracy and face identification reliability.
- Correct metadata binding for event clips.
- Instant, secure, non‑duplicated notifications.
- Proper login and role‑based access control.
- Graceful behavior during Wi‑Fi interruptions.

## 6.5 Features Tested
- Real‑time capture, object detection (YOLOv8), face summary overlay.
- Event‑driven clip generation and cloud uploads.
- Push notifications with event snapshot.
- Web dashboard and iOS app interactions.
- Data encryption and tamper‑detection paths.

## 6.6 Results and Analysis
Aggregate results from a representative test window are summarized below.

- Class distribution of detections:
  - See Figure 6.1 — Weekly Detections by Class.
- Model performance:
  - See Figure 6.2 — Average Precision/Recall by Class.
- Alert latency trend:
  - See Figure 6.3 — Median Alert Latency Over Time.

Figures

- Figure 6.1: Weekly Detections by Class — `assets/testing_class_distribution.png`
- Figure 6.2: Average Precision/Recall by Class — `assets/testing_precision_recall.png`
- Figure 6.3: Median Alert Latency Over Time — `assets/testing_latency_trend.png`

Conclusion: All key paths operated reliably with low latency and strong accuracy, and no critical defects were found in the evaluated period.
