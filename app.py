import os
import re
from datetime import datetime
from functools import wraps

from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         login_required, logout_user, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

import cloudinary
import cloudinary.uploader

app = Flask(__name__)
CORS(app)

# ── Config ─────────────────────────────────────────────────
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'InnerCompassSecureKey2026')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db            = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ── Cloudinary ─────────────────────────────────────────────
if os.environ.get('CLOUDINARY_URL'):
    try:
        cloudinary.config(secure=True)
    except Exception:
        pass


# ── Models ──────────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(150), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(50), default="member")
    bio           = db.Column(db.Text, default="")
    joined_at     = db.Column(db.DateTime, default=datetime.utcnow)
    last_login    = db.Column(db.DateTime)
    mood_logs     = db.relationship("MoodLog",        backref="user", lazy=True)
    messages      = db.relationship("ContactMessage", backref="user", lazy=True)


class MoodLog(db.Model):
    __tablename__ = "mood_logs"
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    mood      = db.Column(db.String(30), nullable=False)
    note      = db.Column(db.Text, default="")
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(200), nullable=False)
    subject    = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    read       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)


class OutreachProgram(db.Model):
    __tablename__ = "outreach_programs"
    id               = db.Column(db.Integer, primary_key=True)
    title            = db.Column(db.String(200), nullable=False)
    description      = db.Column(db.Text, default="")
    location         = db.Column(db.String(200), default="")
    date             = db.Column(db.DateTime)
    students_reached = db.Column(db.Integer, default=0)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)


# ── Helpers ─────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated

def get_stats():
    return {
        "members":  User.query.count(),
        "programs": OutreachProgram.query.count(),
        "reached":  db.session.query(
                        db.func.sum(OutreachProgram.students_reached)
                    ).scalar() or 0,
    }


# ── Public Page Routes ──────────────────────────────────────

@app.route('/')
def home():
    return render_template('index.html', stats=get_stats())


@app.route('/resources')
def resources():
    return render_template('resources.html')


# ── Member Auth Routes ──────────────────────────────────────

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # JSON (fetch API)
        if request.is_json:
            data     = request.get_json()
            username = (data.get('full_name') or data.get('username') or '').strip()
            email    = (data.get('email') or '').strip().lower()
            password = data.get('password') or ''
        else:
            # fallback form POST
            username = request.form.get('username', '').strip()
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

        if not all([username, email, password]):
            err = {"success": False, "error": "All fields are required."}
            return jsonify(err), 400 if request.is_json else redirect(url_for('signup'))

        if len(password) < 8:
            err = {"success": False, "error": "Password must be at least 8 characters."}
            return jsonify(err), 400 if request.is_json else redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            err = {"success": False, "error": "Email already registered. Please log in."}
            return jsonify(err), 409 if request.is_json else redirect(url_for('login'))

        user = User(
            username=username, email=email,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)

        if request.is_json:
            return jsonify({"success": True, "redirect": url_for('dashboard')})
        return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if request.is_json:
            data     = request.get_json()
            email    = (data.get('email') or '').strip().lower()
            password = data.get('password') or ''
        else:
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            if request.is_json:
                return jsonify({"success": True, "redirect": url_for('dashboard')})
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({"success": False, "error": "Invalid email or password."}), 401
            return render_template('login.html', error="Invalid email or password.")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


# ── Hidden Admin Login (not linked anywhere public) ─────────

@app.route('/icp-admin-login', methods=['GET', 'POST'])
def admin_login():
    # If already logged in as admin, go straight to panel
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect(url_for('admin'))

    error = None
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email, role='admin').first()
        if user and check_password_hash(user.password_hash, password):
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return redirect(url_for('admin'))
        else:
            error = "Invalid admin credentials."

    return render_template('admin_login.html', error=error)


# ── Protected Member Routes ─────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    mood_logs = MoodLog.query.filter_by(user_id=current_user.id)\
                             .order_by(MoodLog.logged_at.desc()).limit(7).all()
    return render_template('dashboard.html',
                           user=current_user,
                           username=current_user.username,
                           stats=get_stats(),
                           mood_logs=mood_logs)


@app.route('/admin')
@login_required
@admin_required
def admin():
    return render_template('admin.html',
        users    = User.query.order_by(User.joined_at.desc()).all(),
        messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all(),
        programs = OutreachProgram.query.order_by(OutreachProgram.date.desc()).all(),
        stats    = get_stats(),
        unread   = ContactMessage.query.filter_by(read=False).count())


# ── Cloudinary Upload (admin only) ─────────────────────────

@app.route('/upload-page')
@login_required
@admin_required
def upload_page():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
@login_required
@admin_required
def handle_upload():
    file = request.files.get('file_to_upload')
    if file:
        try:
            folder = "inner_compass_docs" if file.filename.endswith('.pdf') else "inner_compass_images"
            result = cloudinary.uploader.upload(file, folder=folder)
            return (f"<h3>Upload Successful!</h3><p>Link: {result['secure_url']}</p>"
                    f"<a href='/upload-page'>Upload another</a>")
        except Exception as e:
            return f"Upload Error: {str(e)}"
    return "No file selected", 400


# ── API Routes ──────────────────────────────────────────────

@app.route('/api/contact', methods=['POST'])
def api_contact():
    data    = request.get_json()
    name    = (data.get('name') or '').strip()
    email   = (data.get('email') or '').strip()
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()

    if not all([name, email, subject, message]):
        return jsonify({"success": False, "error": "All fields are required."}), 400
    if not valid_email(email):
        return jsonify({"success": False, "error": "Invalid email."}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    db.session.add(ContactMessage(name=name, email=email, subject=subject,
                                  message=message, user_id=user_id))
    db.session.commit()
    return jsonify({"success": True, "message": "Message received! We'll get back to you soon."})


@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    email = (request.get_json().get('email') or '').strip().lower()
    if not email or not valid_email(email):
        return jsonify({"success": False, "error": "Valid email required."}), 400
    if NewsletterSubscriber.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "Already subscribed!"}), 409
    db.session.add(NewsletterSubscriber(email=email))
    db.session.commit()
    return jsonify({"success": True, "message": "You're now part of our community!"})


@app.route('/api/mood', methods=['POST'])
def api_mood():
    data    = request.get_json()
    mood    = (data.get('mood') or '').strip()
    note    = (data.get('note') or '').strip()
    user_id = current_user.id if current_user.is_authenticated else None

    if mood not in {"happy", "calm", "tired", "sad", "anxious"}:
        return jsonify({"success": False, "error": "Invalid mood."}), 400

    db.session.add(MoodLog(mood=mood, note=note, user_id=user_id))
    db.session.commit()

    responses = {
        "happy":   "That's wonderful! Keep spreading that energy. 🌟",
        "calm":    "Peace is powerful. Stay grounded. 🌿",
        "tired":   "Rest is part of recovery. Be gentle with yourself. 😴",
        "sad":     "It's okay to feel this way. You're not alone. 💙",
        "anxious": "Take a deep breath. This moment will pass. 🤍",
    }
    return jsonify({"success": True, "message": responses[mood]})


@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


@app.route('/api/profile', methods=['POST'])
@login_required
def api_profile():
    data     = request.get_json()
    username = (data.get('full_name') or data.get('username') or '').strip()
    if username:
        current_user.username = username
    current_user.bio = (data.get('bio') or '').strip()
    db.session.commit()
    return jsonify({"success": True, "message": "Profile updated!"})


@app.route('/api/admin/message/<int:msg_id>/read', methods=['POST'])
@login_required
@admin_required
def mark_read(msg_id):
    msg = ContactMessage.query.get_or_404(msg_id)
    msg.read = True
    db.session.commit()
    return jsonify({"success": True})


@app.route('/api/admin/program', methods=['POST'])
@login_required
@admin_required
def add_program():
    data = request.get_json()
    db.session.add(OutreachProgram(
        title            = data.get('title', ''),
        description      = data.get('description', ''),
        location         = data.get('location', ''),
        students_reached = int(data.get('students_reached', 0)),
        date             = datetime.utcnow(),
    ))
    db.session.commit()
    return jsonify({"success": True, "message": "Program added!"})


@app.route('/api/admin/user/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_role(user_id):
    data = request.get_json()
    user = User.query.get_or_404(user_id)
    if data.get('role') in ('member', 'admin'):
        user.role = data['role']
        db.session.commit()
    return jsonify({"success": True})


@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


# ── Init DB ─────────────────────────────────────────────────
with app.app_context():
    db.create_all()

    # Auto-create admin account
    if not User.query.filter_by(role='admin').first():
        admin_user = User(
            username      = 'Mustapha Abdulrasak',
            email         = os.environ.get('ADMIN_EMAIL', 'Innercompassproject25@gmail.com'),
            password_hash = generate_password_hash(
                os.environ.get('ADMIN_PASSWORD', 'ICP@Admin2025!'),
                method='pbkdf2:sha256'),
            role = 'admin'
        )
        db.session.add(admin_user)
        db.session.commit()

    # Seed outreach programs so counters are never 0
    if OutreachProgram.query.count() == 0:
        db.session.add_all([
            OutreachProgram(title="Kwara School Outreach", location="Ilorin",
                            students_reached=240, date=datetime(2025, 3, 15)),
            OutreachProgram(title="Webinar Series — Season 1", location="Online",
                            students_reached=580, date=datetime(2025, 5, 20)),
            OutreachProgram(title="ICP Summit 2025", location="Ilorin",
                            students_reached=350, date=datetime(2025, 11, 10)),
        ])
        db.session.commit()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
