# Cataract Detection UI (Flask + Ultralytics YOLO-first)

## Setup
1. Create venv:
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows

2. Install:
   pip install -r requirements.txt

3. Create folders (if not present):
   mkdir uploads outputs models templates static/static

4. Put your trained model at:
   models/best_model.pt

## Run (development)
   python app.py
Then open http://127.0.0.1:5000

## Notes
- The code tries Ultralytics YOLO loader first. If your `best_model.pt` is a raw PyTorch checkpoint, adapt `model_utils.run_inference` to instantiate your model class and preprocess/postprocess.
- The web UI returns JSON and an annotated image (if boxes available).
# from project root
python -m venv venv
# activate:
# Windows:
venv\Scripts\activate
# mac/linux:
source venv/bin/activate

pip install -r requirements.txt

# make folders
mkdir -p uploads outputs models templates static/css static/js

# move your model to models/
# example (adjust if model is at /mnt/data):
mv /mnt/data/best_model.pt models/best_model.pt

# run
python app.py
# open http://127.0.0.1:5000
