# Sample Data

This directory contains sample images and expected outputs for testing and demos.

## Test Image

- `test.jpg` - Sample image for object detection testing

If the test image is not present, the demo script will create a simple test image automatically.

## Expected Output

- `expected_output.json` - Expected detection results from `run_demo.py`

## Usage

```bash
# Run demo on test image
python run_demo.py --image samples/test.jpg

# Compare with expected output
python run_demo.py --image samples/test.jpg --output results.json
diff results.json samples/expected_output.json
```

## Creating Your Own Test Image

You can use any image for testing:

```bash
# Use your own image
python run_demo.py --image path/to/your/image.jpg

# Use different model
python run_demo.py --image samples/test.jpg --model yolov8s.pt
```

