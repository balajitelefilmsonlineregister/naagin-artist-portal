import os, secrets, string, smtplib
from email.message import EmailMessage
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()
BASE = Path(__file__).resolve().parent
UPLOAD_DIR = BASE / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "CHANGE-ME-before-deployment"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", f"sqlite:///{BASE / 'portal.db'}"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    UPLOAD_FOLDER=str(UPLOAD_DIR),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1",
)
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
ALLOWED = {"jpg", "jpeg", "png", "webp"}
STATUSES = ["Submitted", "Under Review", "Shortlisted", "Approved", "Rejected"]

class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(24), unique=True, nullable=False, index=True)
    tracking_token = db.Column(db.String(64), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.String(10), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(160), nullable=False, index=True)
    city = db.Column(db.String(100), nullable=False)
    experience = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(30), default="Submitted", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapped

def valid_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

def notify_admin(applicant):
    # Configure SMTP_* and ADMIN_NOTIFY_EMAIL in the deployment environment.
    required = ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "ADMIN_NOTIFY_EMAIL"]
    if not all(os.getenv(k) for k in required):
        app.logger.warning("Admin email notification skipped: SMTP settings are incomplete.")
        return
    msg = EmailMessage()
    msg["Subject"] = f"New artist application: {applicant.application_id}"
    msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME"))
    msg["To"] = os.getenv("ADMIN_NOTIFY_EMAIL")
    msg.set_content(
        f"A new artist application was submitted.\\n"
        f"Application ID: {applicant.application_id}\\n"
        f"Name: {applicant.full_name}\\n"
        f"City: {applicant.city}\\n"
        f"Email: {applicant.email}\\n"
        f"Phone: {applicant.phone}\\n"
        f"Log in to the admin dashboard to review the application."
    )
    try:
        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587")), timeout=15) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
            server.send_message(msg)
    except Exception:
        app.logger.exception("Unable to send admin notification email.")

def make_application_id():
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "NS8-" + "".join(secrets.choice(alphabet) for _ in range(8))
        if not Applicant.query.filter_by(application_id=code).first():
            return code

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        required = ["full_name", "dob", "gender", "phone", "email", "city"]
        if any(not request.form.get(k, "").strip() for k in required):
            flash("Please complete all required fields.", "error")
            return redirect(url_for("register"))
        phone = request.form["phone"].strip()
        if not phone.replace("+", "").replace("-", "").replace(" ", "").isdigit() or len(phone) < 10:
            flash("Please enter a valid phone number.", "error")
            return redirect(url_for("register"))
        photo = request.files.get("photo")
        photo_name = None
        if photo and photo.filename:
            if not valid_image(photo.filename):
                flash("Photo must be JPG, JPEG, PNG or WEBP.", "error")
                return redirect(url_for("register"))
            photo_name = secrets.token_hex(16) + "." + secure_filename(photo.filename).rsplit(".", 1)[1].lower()
            photo.save(UPLOAD_DIR / photo_name)
        app_id = make_application_id()
        token = secrets.token_urlsafe(24)
        applicant = Applicant(
            application_id=app_id, tracking_token=token,
            full_name=request.form["full_name"].strip(),
            dob=request.form["dob"], gender=request.form["gender"],
            phone=phone, email=request.form["email"].strip().lower(),
            city=request.form["city"].strip(),
            experience=request.form.get("experience", "").strip(),
            photo=photo_name
        )
        db.session.add(applicant)
        db.session.commit()
        notify_admin(applicant)
        return render_template("success.html", applicant=applicant)
    return render_template("register.html")

@app.route("/track", methods=["GET", "POST"])
def track():
    applicant = None
    if request.method == "POST":
        app_id = request.form.get("application_id", "").strip().upper()
        token = request.form.get("tracking_token", "").strip()
        applicant = Applicant.query.filter_by(application_id=app_id, tracking_token=token).first()
        if not applicant:
            flash("Application ID or private tracking code is incorrect.", "error")
    return render_template("track.html", applicant=applicant)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin = Admin.query.filter_by(username=request.form.get("username", "").strip()).first()
        if admin and check_password_hash(admin.password_hash, request.form.get("password", "")):
            session.clear()
            session["admin_id"] = admin.id
            return redirect(url_for("dashboard"))
        flash("Invalid login details.", "error")
    return render_template("login.html")

@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def dashboard():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = Applicant.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Applicant.full_name.ilike(like), Applicant.application_id.ilike(like), Applicant.email.ilike(like), Applicant.phone.ilike(like)))
    if status in STATUSES:
        query = query.filter_by(status=status)
    applicants = query.order_by(Applicant.created_at.desc()).all()
    counts = {s: Applicant.query.filter_by(status=s).count() for s in STATUSES}
    return render_template("dashboard.html", applicants=applicants, counts=counts, statuses=STATUSES, selected=status, q=q)

@app.route("/admin/applicant/<int:applicant_id>", methods=["GET", "POST"])
@admin_required
def applicant_detail(applicant_id):
    applicant = Applicant.query.get_or_404(applicant_id)
    if request.method == "POST":
        new_status = request.form.get("status")
        if new_status not in STATUSES:
            abort(400)
        applicant.status = new_status
        db.session.commit()
        flash("Application status updated.", "success")
        return redirect(url_for("applicant_detail", applicant_id=applicant.id))
    return render_template("detail.html", applicant=applicant, statuses=STATUSES)

@app.route("/uploads/<path:filename>")
@admin_required
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.errorhandler(413)
def too_large(_):
    return "Upload too large. Maximum size is 5 MB.", 413

with app.app_context():
    db.create_all()
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if username and password and not Admin.query.filter_by(username=username).first():
        db.session.add(Admin(username=username, password_hash=generate_password_hash(password)))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
