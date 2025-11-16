#!/bin/bash
# Download YOLO models for FalconEye
# Usage: ./scripts/download_models.sh [model_name]

set -e

MODEL_VERSION="v8.2.0"
BASE_URL="https://github.com/ultralytics/assets/releases/download/${MODEL_VERSION}"

# Default models to download
MODELS=("yolov8n.pt" "yolov8s.pt")

# If model name provided, download only that
if [ $# -gt 0 ]; then
    MODELS=("$1")
fi

echo "📥 Downloading YOLO models for FalconEye"
echo "=========================================="

for model in "${MODELS[@]}"; do
    if [ -f "$model" ]; then
        echo "⏭️  $model already exists, skipping..."
    else
        echo "⬇️  Downloading $model..."
        wget -q --show-progress "${BASE_URL}/${model}" -O "$model" || {
            echo "❌ Failed to download $model"
            echo "   Trying alternative method..."
            curl -L "${BASE_URL}/${model}" -o "$model" || {
                echo "❌ Failed to download $model with curl as well"
                exit 1
            }
        }
        echo "✅ Downloaded $model"
    fi
done

echo ""
echo "✅ Model download complete!"
echo ""
echo "Model sizes:"
ls -lh *.pt 2>/dev/null | awk '{print "   " $9 ": " $5}' || echo "   No models found"

