
# Cataract Detection Web App

**Tech Stack:** Flask | Python | Ultralytics YOLO | HTML/CSS/JS

A modern web application to detect cataracts in eye images. Users can upload images and get **annotated images with detection boxes** along with **JSON results**.

---

## **Features**

* Upload eye images and detect cataracts in real-time.
* Returns **annotated images** and JSON results.
* Easy to extend with custom YOLO models.
* **Professional UI** with animations: loading spinner, fade-in results, hover effects.

---

## **Demo**

Open after running the app:
[http://127.0.0.1:5000](http://127.0.0.1:5000)


## **Setup & Installation**

### **1. Clone the repository**

```bash
git clone https://github.com/Karthikkarthik567/cataract-ui.git
cd cataract-ui
```

### **2. Create & activate virtual environment**

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### **3. Install dependencies**

```bash
pip install -r requirements.txt
```

### **4. Prepare project folders**

```bash
mkdir -p uploads outputs models templates static/css static/js
```

### **5. Add trained model**

Place your YOLO model here:

```bash
models/best_model.pt
```

> If using a raw PyTorch checkpoint, update `model_utils.run_inference` to match your model class.

---

## **6. Run the App**

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## **7. UI Enhancements / Animations**

To make the app **professional and interactive**:

* **Loading spinner** while processing:




## **Tech Stack**

* **Backend:** Flask
* **Model:** Ultralytics YOLO / PyTorch
* **Frontend:** HTML, CSS, JavaScript

---

## **Contributing**

1. Fork the repository
2. Create a branch for your feature/fix
3. Submit a pull request

---

## **License**

MIT License

---

