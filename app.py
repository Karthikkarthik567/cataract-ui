import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from database import db, User, Detection
from model_utils import load_model, run_inference, draw_boxes_on_image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

# ==========================================
# PATH SETUP
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
PDF_FOLDER = os.path.join(BASE_DIR, 'pdfs')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'best_model.pt')
DB_PATH = os.path.join(BASE_DIR, 'instance', 'app.db')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

# ==========================================
# FLASK APP CONFIG
# ==========================================
app = Flask(__name__)
app.secret_key = 'super_secret_key_here'  # Change before deploying
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER

# Token generator for secure reset links
serializer = URLSafeTimedSerializer(app.secret_key)

# ==========================================
# MAIL CONFIGURATION
# ==========================================
app.config.update(
    MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_PORT=int(os.getenv('MAIL_PORT', 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv('MAIL_USERNAME', 'your_email@gmail.com'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD', 'your_app_password'),
    MAIL_DEFAULT_SENDER=('Cataract Detection AI', os.getenv('MAIL_USERNAME', 'your_email@gmail.com'))
)
mail = Mail(app)

# ==========================================
# INIT DB & LOGIN
# ==========================================
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None


# ==========================================
# LOAD YOLO MODEL
# ==========================================
try:
    model_bundle = load_model(MODEL_PATH)
    print(f"✅ YOLO model loaded from {MODEL_PATH}")
except Exception as e:
    model_bundle = None
    print("❌ Model load failed:", e)


# ==========================================
# PDF GENERATOR
# ==========================================
def generate_pdf_report(report_id, username, label, confidence, uploaded_path, annotated_path):
    pdf_filename = f"report_{report_id}.pdf"
    pdf_path = os.path.join(app.config['PDF_FOLDER'], pdf_filename)

    try:
        c = canvas.Canvas(pdf_path, pagesize=A4)
        w, h = A4
        margin = 60
        line_height = 16

        # Header
        c.setFillColor(colors.HexColor("#004C91"))
        c.rect(0, h - 70, w, 70, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(w / 2, h - 45, "Cataract Detection Report")

        # Meta Info
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 11)
        c.drawString(margin, h - 100, f"Patient Name: {username}")
        c.drawString(margin, h - 115, f"Report ID: {report_id}")
        c.drawRightString(w - margin, h - 100, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        c.drawRightString(w - margin, h - 115, f"Confidence: {round(confidence * 100, 2)}%")

        # Summary
        y = h - 160
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(margin, y, w - margin, y)
        y -= 25
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor("#004C91"))
        c.drawString(margin, y, "Detection Summary")
        y -= 25
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)
        c.drawString(margin + 20, y, f"Result: {label.capitalize()}")
        y -= line_height
        c.drawString(margin + 20, y, f"Confidence Level: {round(confidence * 100, 2)}%")

        # Images
        try:
            img_y = y - 220
            img_h = 180
            img_w = (w - 2 * margin - 20) / 2
            img1 = ImageReader(uploaded_path)
            img2 = ImageReader(annotated_path)
            c.drawImage(img1, margin, img_y, img_w, img_h, preserveAspectRatio=True, mask='auto')
            c.drawImage(img2, margin + img_w + 20, img_y, img_w, img_h, preserveAspectRatio=True, mask='auto')
            c.setFont("Helvetica-Oblique", 9)
            c.setFillColor(colors.grey)
            c.drawCentredString(margin + img_w / 2, img_y - 10, "Original Image")
            c.drawCentredString(margin + img_w + 20 + img_w / 2, img_y - 10, "AI Detection Output")
            y = img_y - 40
        except Exception as e:
            print("⚠️ Image load failed:", e)
            y -= 20

        # Diagnosis
        c.setStrokeColor(colors.HexColor("#cccccc"))
        c.line(margin, y, w - margin, y)
        y -= 25
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.HexColor("#004C91"))
        c.drawString(margin, y, "Diagnostic Notes")
        y -= 25
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)

        if label.lower() == "cataract":
            notes = [
                "Lens opacity consistent with cataract formation has been detected.",
                "Signs indicate a reduction in lens transparency affecting vision clarity.",
            ]
            highlight_color = colors.HexColor("#e74c3c")
        else:
            notes = [
                "No opacity or structural abnormalities detected in the lens region.",
                "The eye appears healthy and within normal parameters."
            ]
            highlight_color = colors.HexColor("#2ecc71")

        c.setFillColor(highlight_color)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin + 10, y, f"Diagnosis: {label.capitalize()}")
        y -= 25
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.black)
        for line in notes:
            c.drawString(margin + 15, y, line)
            y -= line_height

        c.save()
        return pdf_filename
    except Exception as e:
        print("⚠️ PDF generation failed:", e)
        return None


# ==========================================
# DOWNLOAD / VIEW REPORTS
# ==========================================
@app.route('/download_report', methods=['POST'])
@login_required
def download_report():
    """
    Form-based download endpoint used by admin download box and admin table POSTs.
    Allows:
      - Admins to download any report.
      - Normal users to download only their own reports.
    """
    report_id = request.form.get('report_id')
    if not report_id:
        flash("No report ID provided.", "warning")
        return redirect(url_for('index'))

    # If admin, allow any report; otherwise restrict to current user's report
    detection = None
    if getattr(current_user, "is_admin", False):
        detection = Detection.query.filter_by(report_id=report_id).first()
    else:
        detection = Detection.query.filter_by(report_id=report_id, user_id=current_user.id).first()

    if not detection:
        flash("Report not found or you do not have permission to download it.", "danger")
        return redirect(url_for('index'))

    pdf_filename = f"report_{report_id}.pdf"
    pdf_path = os.path.join(app.config['PDF_FOLDER'], pdf_filename)
    if not os.path.exists(pdf_path):
        flash("PDF not generated yet.", "warning")
        return redirect(url_for('index'))

    # Use send_from_directory to deliver file as attachment
    return send_from_directory(app.config['PDF_FOLDER'], pdf_filename, as_attachment=True)


@app.route('/view_report/<report_id>')
@login_required
def view_report(report_id):
    """
    Renders a view page for a given report. Admins can view any report.
    Normal users can view only their own.
    """
    detection = Detection.query.filter_by(report_id=report_id).first()
    if not detection:
        flash("Report not found.", "danger")
        # if admin was viewing, go back to admin, else user's index
        if getattr(current_user, "is_admin", False):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    # Permission check
    if not getattr(current_user, "is_admin", False) and detection.user_id != current_user.id:
        flash("You do not have permission to view this report.", "danger")
        return redirect(url_for('index'))

    # Provide template with detection and constructed file URLs
    pdf_filename = f"report_{report_id}.pdf"
    pdf_exists = os.path.exists(os.path.join(app.config['PDF_FOLDER'], pdf_filename))
    uploaded_url = url_for('uploads_file', fname=detection.filename)
    annotated_url = url_for('outputs_file', fname=detection.annotated)
    pdf_url = url_for('pdfs_file', fname=pdf_filename) if pdf_exists else None

    return render_template('view_report.html', detection=detection, uploaded_url=uploaded_url, annotated_url=annotated_url, pdf_url=pdf_url)


# ==========================================
# ADMIN DELETE ROUTE (NEW)
# ==========================================
@app.route('/admin/delete/<report_id>', methods=['POST'])
@login_required
def admin_delete_report(report_id):
    """
    Admin-only delete route.
    Deletes DB record and associated files (upload, annotated, pdf) if present.
    """
    if not getattr(current_user, "is_admin", False):
        flash("Access denied — Admins only!", "danger")
        return redirect(url_for('index'))

    detection = Detection.query.filter_by(report_id=report_id).first()
    if not detection:
        flash("Record not found.", "warning")
        return redirect(url_for('admin_dashboard'))

    # Files to attempt deletion
    to_delete = []
    # uploaded original
    if detection.filename:
        to_delete.append(os.path.join(app.config['UPLOAD_FOLDER'], detection.filename))
    # annotated output
    if detection.annotated:
        to_delete.append(os.path.join(app.config['OUTPUT_FOLDER'], detection.annotated))
    # pdf
    pdf_name = f"report_{report_id}.pdf"
    to_delete.append(os.path.join(app.config['PDF_FOLDER'], pdf_name))

    # Safely delete files (only inside allowed folders)
    for path in to_delete:
        try:
            if path and os.path.exists(path):
                # ensure the path is inside one of our allowed folders before deleting
                abs_path = os.path.abspath(path)
                if abs_path.startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])) or \
                   abs_path.startswith(os.path.abspath(app.config['OUTPUT_FOLDER'])) or \
                   abs_path.startswith(os.path.abspath(app.config['PDF_FOLDER'])):
                    os.remove(abs_path)
                else:
                    print(f"Skipped deletion of suspicious path: {abs_path}")
        except Exception as e:
            print(f"Error deleting file {path}: {e}")

    # Delete DB record
    try:
        db.session.delete(detection)
        db.session.commit()
        flash("Record and files deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        print("DB deletion error:", e)
        flash("Failed to delete record from database.", "danger")

    return redirect(url_for('admin_dashboard'))


# ==========================================
# FORGOT PASSWORD
# ==========================================
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("❌ No account found with that email.", "danger")
            return redirect(url_for('forgot_password'))

        token = serializer.dumps(email, salt='password-reset-salt')
        reset_url = url_for('reset_password', token=token, _external=True)
        subject = "🔐 Reset Your Password - Cataract Detection AI"
        body = f"Click the link below to reset your password:\n\n{reset_url}\n\nThis link is valid for 30 minutes."

        try:
            if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                msg = Message(subject, sender=app.config['MAIL_USERNAME'], recipients=[email])
                msg.body = body
                mail.send(msg)
                flash("✅ Reset link sent successfully! Please check your inbox.", "success")
            else:
                print("\n📩 Email sending not configured. Reset link printed below:\n", reset_url)
                flash("⚙️ Email not configured — check console for reset link.", "warning")

        except Exception as e:
            print("❌ Email sending failed:", e)
            print("Reset link:", reset_url)
            flash("⚠️ Email sending failed — reset link printed in console.", "danger")

        return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')


# ==========================================
# RESET PASSWORD
# ==========================================
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=1800)
    except Exception:
        flash("❌ Reset link is invalid or expired.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("✅ Password has been reset successfully!", "success")
            return redirect(url_for('login'))
        else:
            flash("❌ User not found.", "danger")

    return render_template('reset_password.html')


# ==========================================
# OTHER ROUTES (Register, Login, Predict, etc.)
# ==========================================
# [keep your other routes below unchanged]

# ==========================================
# ROUTES
# ==========================================
@app.route('/home')
def home():
    return render_template('home.html')

# ---------- Public Home ----------
@app.route('/')
def home_page():
    return render_template('home.html')

# ---------- Dashboard (after login) ----------
@app.route('/dashboard')
@login_required
def index():
    recent = Detection.query.filter_by(user_id=current_user.id).order_by(Detection.timestamp.desc()).limit(3).all()
    return render_template('index.html', user=current_user, recent=recent)

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ---------- About Page ----------
@app.route('/about')
def about():
    return render_template('about.html')

# ---------- Register ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please fill in the required fields (email & password).", "danger")
            return redirect(url_for('register'))

        if username and User.query.filter_by(username=username).first():
            flash("Username already taken! Please choose another.", "warning")
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "warning")
            return redirect(url_for('register'))

        try:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username or None, email=email, password=hashed_pw)
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("DB error during registration:", e)
            flash("Registration failed due to a server error. Please try again.", "danger")
            return redirect(url_for('register'))

        flash("✅ Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# ---------- Login ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_field = request.form.get('email', '').strip()
        username_field = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        lookup_val = email_field or username_field
        if not lookup_val or not password:
            flash("Please enter your email/username and password.", "warning")
            return redirect(url_for('login'))

        user = User.query.filter_by(email=lookup_val).first()
        if user is None:
            user = User.query.filter_by(username=lookup_val).first()

        if not user or not check_password_hash(user.password, password):
            flash("❌ Invalid email/username or password.", "danger")
            return redirect(url_for('login'))

        login_user(user)
        flash(f"Welcome back, {user.username or user.email}!", "success")
        return redirect(url_for('index'))

    return render_template('login.html')

# ---------- Logout ----------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("👋 Logged out successfully.", "info")
    return redirect(url_for('login'))

# ---------- Predict ----------
@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if model_bundle is None:
        flash("Model not loaded.", "danger")
        return redirect(url_for('index'))

    file = request.files.get('image')
    if not file or file.filename == '':
        flash("Please select an image.", "warning")
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    uid = f"{uuid.uuid4().hex}_{filename}"
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], uid)
    file.save(upload_path)

    try:
        result = run_inference(model_bundle, upload_path)
    except Exception as e:
        flash(f"Inference failed: {e}", "danger")
        return redirect(url_for('index'))

    annotated_name = f"annot_{uuid.uuid4().hex}_{filename}"
    annotated_path = os.path.join(app.config['OUTPUT_FOLDER'], annotated_name)
    try:
        draw_boxes_on_image(upload_path, result.get('boxes', []), annotated_path, labels=result.get('names'))
    except Exception as e:
        print("Annotation failed:", e)
        annotated_path = upload_path
        annotated_name = os.path.basename(upload_path)

    label = result.get('label', 'Unknown')
    confidence = float(result.get('confidence', 0.0))
    report_id = str(uuid.uuid4())[:8]

    detection = Detection(
        report_id=report_id,
        filename=uid,
        annotated=annotated_name,
        result=label,
        confidence=confidence,
        user_id=current_user.id
    )
    db.session.add(detection)
    db.session.commit()

    # generate pdf (we generate now)
    pdf_filename = generate_pdf_report(report_id, current_user.username or current_user.email, label, confidence, upload_path, annotated_path)
    pdf_url = url_for('pdfs_file', fname=pdf_filename) if pdf_filename else "#"

    return render_template(
        'result.html',
        label=label,
        confidence=confidence,
        uploaded_url=url_for('uploads_file', fname=uid),
        annotated_url=url_for('outputs_file', fname=annotated_name),
        report_id=report_id,
        pdf_url=pdf_url
    )

# ---------- History ----------
@app.route('/history')
@login_required
def history():
    records = Detection.query.filter_by(user_id=current_user.id).order_by(Detection.timestamp.desc()).all()
    return render_template('history.html', history=records, user=current_user)

# ---------- Admin Dashboard ----------
@app.route('/admin')
@login_required
def admin_dashboard():
    if not getattr(current_user, "is_admin", False):
        flash("Access denied — Admins only!", "danger")
        return redirect(url_for('index'))

    # Provide detections and recent (for the template)
    detections = Detection.query.order_by(Detection.timestamp.desc()).all()
    recent = Detection.query.order_by(Detection.timestamp.desc()).limit(5).all()
    return render_template('admin_dashboard.html', detections=detections, recent=recent, user=current_user)

# ---------- Static Serving 
# ----------
@app.route('/uploads/<path:fname>')
def uploads_file(fname):
    # serve uploads (no login requirement so thumbnails can be embedded; if you prefer require login, add @login_required)
    return send_from_directory(app.config['UPLOAD_FOLDER'], fname)

@app.route('/outputs/<path:fname>')
def outputs_file(fname):
    # serve annotated outputs
    return send_from_directory(app.config['OUTPUT_FOLDER'], fname)

@app.route('/pdfs/<path:fname>')
@login_required
def pdfs_file(fname):
    # View-only PDF (no forced download)
    return send_from_directory(app.config['PDF_FOLDER'], fname, as_attachment=False)

# ---------- Initialize DB ----------
with app.app_context():
    db.create_all()

# ---------- Run ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
