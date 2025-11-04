import sys
from model_utils import load_model, run_inference

if len(sys.argv) < 2:
    print("Usage: python inference_cli.py path/to/image.jpg")
    sys.exit(1)

image = sys.argv[1]
model_path = "models/best_model.pt"

mb = load_model(model_path)
res = run_inference(mb, image)
print(res)
