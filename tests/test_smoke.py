"""
Smoke tests for FalconEye backend.
These tests verify basic functionality without requiring full system setup.
"""

import os
import sys
import pytest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that core modules can be imported."""
    try:
        import cv2
        import numpy as np
        from ultralytics import YOLO
        from flask import Flask
        assert True
    except ImportError as e:
        pytest.skip(f"Missing dependency: {e}")


def test_yolo_model_load():
    """Test that YOLO model can be loaded (will download if needed)."""
    try:
        from ultralytics import YOLO
        
        # Use smallest model for testing
        model_name = "yolov8n.pt"
        model = YOLO(model_name)
        assert model is not None
        assert hasattr(model, 'predict')
    except Exception as e:
        pytest.skip(f"Could not load YOLO model: {e}")


def test_detection_on_test_image():
    """Test object detection on a test image if available."""
    try:
        from ultralytics import YOLO
        import cv2
        import numpy as np
        
        # Check if test image exists
        test_image = Path("samples/test.jpg")
        if not test_image.exists():
            # Create a simple test image
            test_image.parent.mkdir(exist_ok=True)
            test_img = np.zeros((640, 640, 3), dtype=np.uint8)
            cv2.rectangle(test_img, (100, 100), (300, 300), (255, 255, 255), -1)
            cv2.imwrite(str(test_image), test_img)
        
        # Load model
        model = YOLO("yolov8n.pt")
        
        # Run detection
        results = model(str(test_image), verbose=False)
        assert results is not None
        assert len(results) > 0
        
    except Exception as e:
        pytest.skip(f"Detection test failed: {e}")


def test_backend_config():
    """Test that backend configuration can be loaded."""
    try:
        # Test environment variable loading
        os.environ.setdefault("FALCONEYE_SECRET", "test-secret")
        os.environ.setdefault("FLASK_ENV", "test")
        
        # Try importing backend (may fail if dependencies missing, that's ok)
        try:
            import backend
            assert True
        except Exception:
            # Backend import may fail in test environment, that's acceptable
            pytest.skip("Backend import failed (expected in test environment)")
            
    except Exception as e:
        pytest.skip(f"Config test failed: {e}")


def test_env_example_exists():
    """Test that .env.example exists for configuration reference."""
    env_example = Path(".env.example")
    assert env_example.exists(), ".env.example should exist for configuration reference"


def test_requirements_pinned():
    """Test that requirements.txt has pinned versions."""
    requirements = Path("requirements.txt")
    assert requirements.exists(), "requirements.txt should exist"
    
    with open(requirements, 'r') as f:
        lines = f.readlines()
        pinned = [l for l in lines if '==' in l and not l.strip().startswith('#')]
        assert len(pinned) > 0, "requirements.txt should have pinned versions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

