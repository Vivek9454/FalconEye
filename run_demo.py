#!/usr/bin/env python3
"""
Quick demo script to test FalconEye object detection on a single image.
Usage: python run_demo.py --image samples/test.jpg
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from ultralytics import YOLO
    import cv2
    import numpy as np
except ImportError:
    print("❌ Missing dependencies. Install with: pip install -r requirements.txt")
    sys.exit(1)


def run_detection(image_path: str, model_name: str = "yolov8n.pt", confidence: float = 0.25):
    """
    Run object detection on a single image.
    
    Args:
        image_path: Path to input image
        model_name: YOLO model to use (default: yolov8n.pt for speed)
        confidence: Detection confidence threshold
    
    Returns:
        dict: Detection results with bounding boxes and classes
    """
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return None
    
    # Check if model exists, download if not
    if not os.path.exists(model_name):
        print(f"📥 Model {model_name} not found. Downloading...")
        model = YOLO(model_name)  # This will auto-download
    else:
        print(f"✅ Loading model: {model_name}")
        model = YOLO(model_name)
    
    # Load image
    print(f"📸 Processing image: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ Could not load image: {image_path}")
        return None
    
    # Run detection
    print("🔍 Running object detection...")
    results = model(image, conf=confidence, verbose=False)
    
    # Parse results
    detections = []
    result = results[0]
    
    if result.boxes is not None:
        for box in result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            class_name = model.names[cls]
            
            # Get bounding box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            detections.append({
                "class": class_name,
                "confidence": round(conf, 3),
                "bbox": {
                    "x1": round(float(x1), 1),
                    "y1": round(float(y1), 1),
                    "x2": round(float(x2), 1),
                    "y2": round(float(y2), 1)
                }
            })
    
    # Summary
    summary = {
        "image": image_path,
        "model": model_name,
        "total_detections": len(detections),
        "detections": detections
    }
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="FalconEye Quick Demo")
    parser.add_argument(
        "--image",
        type=str,
        default="samples/test.jpg",
        help="Path to test image (default: samples/test.jpg)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        choices=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
        help="YOLO model to use (default: yolov8n.pt)"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.25,
        help="Detection confidence threshold (default: 0.25)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file (optional)"
    )
    
    args = parser.parse_args()
    
    print("🚀 FalconEye Quick Demo")
    print("=" * 50)
    
    # Run detection
    results = run_detection(args.image, args.model, args.confidence)
    
    if results is None:
        sys.exit(1)
    
    # Print results
    print("\n📊 Detection Results:")
    print(f"   Image: {results['image']}")
    print(f"   Model: {results['model']}")
    print(f"   Total detections: {results['total_detections']}")
    
    if results['detections']:
        print("\n   Detected objects:")
        for det in results['detections']:
            print(f"   - {det['class']}: {det['confidence']:.1%} confidence")
    else:
        print("\n   No objects detected.")
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {args.output}")
    
    # Also save expected output for verification
    expected_output = Path("samples/expected_output.json")
    if not expected_output.exists():
        expected_output.parent.mkdir(exist_ok=True)
        with open(expected_output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Expected output saved to: {expected_output}")
    
    print("\n✅ Demo complete!")
    return results


if __name__ == "__main__":
    main()

