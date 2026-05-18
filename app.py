import os, re, smtplib, secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ICP-Secret-2026-XkQ9mPqR!')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB upload limit

db_url = os.environ.get('DATABASE_URL', 'sqlite:///icp.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CLUB_EMAIL   = 'Innercompassproject25@gmail.com'
GMAIL_APP_PW = os.environ.get('GMAIL_APP_PASSWORD', '')
SITE_URL     = os.environ.get('SITE_URL', 'https://innercompassproject.up.railway.app')

# Configure Cloudinary
    api_key    = os.environ.get('CLOUDINARY_API_KEY', ''),
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', ''),
    secure     = True
)

# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(to_addr, subject, html_body):
    if not GMAIL_APP_PW:
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f'Inner Compass Project <{CLUB_EMAIL}>'
        msg['To']      = to_addr
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as s:
            s.login(CLUB_EMAIL, GMAIL_APP_PW)
            s.sendmail(CLUB_EMAIL, to_addr, msg.as_string())
        return True
    except Exception as e:
        print(f'Email error: {e}')
        return False

def notify_club(subject, body):
    send_email(CLUB_EMAIL, subject, body)

# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(150), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20), default='member')
    bio           = db.Column(db.Text, default='')
    joined_at     = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token      = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False)

class MoodLog(db.Model):
    __tablename__ = 'mood_logs'
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, nullable=True)
    mood      = db.Column(db.String(30), nullable=False)
    note      = db.Column(db.Text, default='')
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(200), nullable=False)
    subject    = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    read       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NewsletterSubscriber(db.Model):
    __tablename__ = 'newsletter_subscribers'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

class OutreachProgram(db.Model):
    __tablename__    = 'outreach_programs'
    id               = db.Column(db.Integer, primary_key=True)
    title            = db.Column(db.String(200), nullable=False)
    location         = db.Column(db.String(200), default='')
    students_reached = db.Column(db.Integer, default=0)
    date             = db.Column(db.DateTime, default=datetime.utcnow)

class Executive(db.Model):
    __tablename__ = 'executives'
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(150), nullable=False)
    role      = db.Column(db.String(200), nullable=False)
    bio       = db.Column(db.Text, default='')
    initials  = db.Column(db.String(5), default='')
    badge     = db.Column(db.String(50), default='')
    photo_url = db.Column(db.Text, default='')  # base64 data URL
    order     = db.Column(db.Integer, default=99)
    active    = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    __tablename__ = 'events'
    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    location    = db.Column(db.String(200), default='')
    event_date  = db.Column(db.DateTime, nullable=True)
    event_type  = db.Column(db.String(50), default='general')
    active      = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    content    = db.Column(db.Text, nullable=False)
    link       = db.Column(db.String(500), default='')
    link_text  = db.Column(db.String(100), default='Learn More')
    active     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ── Helpers ───────────────────────────────────────────────────────────────────

def valid_email(e):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e))

def get_user():
    uid = session.get('uid')
    if not uid: return None
    u = User.query.get(uid)
    if not u: session.clear()
    return u

def ctx():
    u = get_user()
    if u:
        return dict(logged_in=True, username=u.username,
                    is_admin=(u.role == 'admin'), user=u)
    session.clear()
    return dict(logged_in=False, username='', is_admin=False, user=None)

def login_required(f):
    @wraps(f)
    def dec(*a, **k):
        if not get_user(): session.clear(); return redirect(url_for('login_page'))
        return f(*a, **k)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a, **k):
        u = get_user()
        if not u or u.role != 'admin': return redirect(url_for('home'))
        return f(*a, **k)
    return dec

def get_stats():
    reached = db.session.query(db.func.sum(OutreachProgram.students_reached)).scalar() or 0
    return dict(members=max(0, User.query.count()-1),
                programs=OutreachProgram.query.count(), reached=int(reached))

def get_site_content():
    return dict(
        executives    = Executive.query.filter_by(active=True).order_by(Executive.order).all(),
        events        = Event.query.filter_by(active=True).order_by(Event.event_date).all(),
        announcements = Announcement.query.filter_by(active=True)\
                                          .order_by(Announcement.created_at.desc()).all(),
    )

# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('index.html', stats=get_stats(), **get_site_content(), **ctx())

@app.route('/resources')
def resources():
    return render_template('resources.html', **ctx())

@app.route('/signup', methods=['GET','POST'])
def signup_page():
    if get_user(): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form
        name  = (d.get('full_name') or d.get('username') or '').strip()
        email = (d.get('email') or '').strip().lower()
        pw    = (d.get('password') or '').strip()
        def err(msg):
            if request.is_json: return jsonify(success=False, error=msg), 400
            return render_template('signup.html', error=msg, **ctx())
        if not name or not email or not pw: return err('All fields are required.')
        if len(pw) < 8: return err('Password must be at least 8 characters.')
        if not valid_email(email): return err('Please enter a valid email address.')
        if User.query.filter_by(email=email).first(): return err('Email already registered. Please log in.')
        u = User(username=name, email=email,
                 password_hash=generate_password_hash(pw, method='pbkdf2:sha256'))
        db.session.add(u); db.session.commit()
        session.clear(); session['uid'] = u.id
        send_email(email, 'Welcome to Inner Compass Project! 🧭',
            f'<div style="font-family:sans-serif;max-width:600px;margin:0 auto">'
            f'<h2 style="color:#2d9b6a">Welcome, {name}! 🌿</h2>'
            f'<p>You have joined the Inner Compass Project community.</p>'
            f'<p><a href="{SITE_URL}/dashboard">Visit your dashboard →</a></p>'
            f'<p style="color:#5a7080">Inner Compass Project · 08145739207</p></div>')
        notify_club(f'New Member: {name}', f'<p><b>Name:</b> {name}<br><b>Email:</b> {email}</p>')
        if request.is_json: return jsonify(success=True, redirect=url_for('dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('signup.html', **ctx())

@app.route('/login', methods=['GET','POST'])
def login_page():
    if get_user(): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form
        email = (d.get('email') or '').strip().lower()
        pw    = (d.get('password') or '').strip()
        def err(msg):
            if request.is_json: return jsonify(success=False, error=msg), 401
            return render_template('login.html', error=msg, **ctx())
        if not email or not pw: return err('Email and password are required.')
        u = User.query.filter_by(email=email).first()
        if not u or not check_password_hash(u.password_hash, pw):
            return err('Invalid email or password. Please try again.')
        session.clear(); session['uid'] = u.id
        if request.is_json: return jsonify(success=True, redirect=url_for('dashboard'))
        return redirect(url_for('dashboard'))
    return render_template('login.html', **ctx())

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('home'))

# ── Forgot Password ───────────────────────────────────────────────────────────

@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form
        email = (d.get('email') or '').strip().lower()
        if not email or not valid_email(email):
            msg = 'Please enter a valid email address.'
            if request.is_json: return jsonify(success=False, error=msg), 400
            return render_template('forgot_password.html', error=msg, **ctx())
        u = User.query.filter_by(email=email).first()
        if u:
            PasswordResetToken.query.filter_by(user_id=u.id, used=False).delete()
            token = secrets.token_urlsafe(32)
            db.session.add(PasswordResetToken(user_id=u.id, token=token,
                expires_at=datetime.utcnow() + timedelta(hours=1)))
            db.session.commit()
            reset_url = f'{SITE_URL}/reset-password/{token}'
            send_email(email, 'Reset your Inner Compass password',
                f'<div style="font-family:sans-serif;max-width:600px;margin:0 auto">'
                f'<h2 style="color:#2d9b6a">Password Reset Request</h2>'
                f'<p>Hi {u.username}, click below to reset your password. Expires in 1 hour.</p><br>'
                f'<a href="{reset_url}" style="background:#4ead7d;color:white;padding:.8rem 2rem;'
                f'border-radius:100px;text-decoration:none;font-weight:500;display:inline-block">'
                f'Reset My Password →</a><br><br>'
                f'<p style="color:#5a7080;font-size:.85rem">If you did not request this, ignore this email.</p></div>')
        success = 'If an account exists with that email, a reset link has been sent.'
        if request.is_json: return jsonify(success=True, message=success)
        return render_template('forgot_password.html', success=success, **ctx())
    return render_template('forgot_password.html', **ctx())

@app.route('/reset-password/<token>', methods=['GET','POST'])
def reset_password(token):
    record = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not record or record.expires_at < datetime.utcnow():
        return render_template('forgot_password.html',
            error='This reset link has expired. Please request a new one.', **ctx())
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form
        pw = (d.get('password') or '').strip()
        c  = (d.get('confirm') or '').strip()
        def err(msg):
            if request.is_json: return jsonify(success=False, error=msg), 400
            return render_template('reset_password.html', token=token, error=msg, **ctx())
        if not pw or len(pw) < 8: return err('Password must be at least 8 characters.')
        if pw != c: return err('Passwords do not match.')
        u = User.query.get(record.user_id)
        if not u: return err('Account not found.')
        u.password_hash = generate_password_hash(pw, method='pbkdf2:sha256')
        record.used = True; db.session.commit()
        send_email(u.email, 'Your Inner Compass password was changed',
            f'<div style="font-family:sans-serif"><h3 style="color:#2d9b6a">Password Changed</h3>'
            f'<p>Hi {u.username}, your password was successfully updated.</p>'
            f'<p>If you did not make this change, contact us at {CLUB_EMAIL} immediately.</p></div>')
        success = 'Password updated! You can now log in.'
        if request.is_json: return jsonify(success=True, message=success, redirect=url_for('login_page'))
        return render_template('reset_password.html', token=token, success=success, **ctx())
    return render_template('reset_password.html', token=token, **ctx())

# ── Admin Login ───────────────────────────────────────────────────────────────

@app.route('/icp-admin-login', methods=['GET','POST'])
def admin_login():
    u = get_user()
    if u and u.role == 'admin': return redirect(url_for('admin_panel'))
    error = None
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        pw    = request.form.get('password','').strip()
        u = User.query.filter_by(email=email, role='admin').first()
        if u and check_password_hash(u.password_hash, pw):
            session.clear(); session['uid'] = u.id
            return redirect(url_for('admin_panel'))
        error = 'Invalid admin credentials.'
    return render_template('admin_login.html', error=error)

# ── Dashboard & Admin ─────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    u  = get_user()
    ml = MoodLog.query.filter_by(user_id=u.id).order_by(MoodLog.logged_at.desc()).limit(7).all()
    return render_template('dashboard.html', stats=get_stats(), mood_logs=ml, **ctx())

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    return render_template('admin.html',
        users         = User.query.order_by(User.joined_at.desc()).all(),
        messages      = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all(),
        programs      = OutreachProgram.query.order_by(OutreachProgram.date.desc()).all(),
        subscribers   = NewsletterSubscriber.query.order_by(NewsletterSubscriber.subscribed_at.desc()).all(),
        executives    = Executive.query.order_by(Executive.order).all(),
        events        = Event.query.order_by(Event.event_date.desc()).all(),
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).all(),
        stats         = get_stats(),
        unread        = ContactMessage.query.filter_by(read=False).count(),
        **ctx())

# ── API: Core ─────────────────────────────────────────────────────────────────

@app.route('/api/contact', methods=['POST'])
def api_contact():
    d = request.get_json(silent=True) or {}
    name,email,subject,message = (d.get('name','').strip(), d.get('email','').strip(),
                                   d.get('subject','').strip(), d.get('message','').strip())
    if not all([name,email,subject,message]):
        return jsonify(success=False, error='All fields are required.'), 400
    if not valid_email(email): return jsonify(success=False, error='Invalid email.'), 400
    db.session.add(ContactMessage(name=name,email=email,subject=subject,message=message))
    db.session.commit()
    notify_club(f'Contact: {subject}',
        f'<p><b>From:</b> {name} &lt;{email}&gt;</p><p>{message}</p><p><a href="mailto:{email}">Reply</a></p>')
    send_email(email, 'We received your message — Inner Compass Project',
        f'<div style="font-family:sans-serif"><h3 style="color:#2d9b6a">Hi {name},</h3>'
        f'<p>We received your message and will reply within 24–48 hours.</p>'
        f'<p style="font-style:italic;background:#f5f5f5;padding:1rem;border-radius:8px">"{message}"</p>'
        f'<p style="color:#5a7080">Inner Compass Project · 08145739207</p></div>')
    return jsonify(success=True, message="Message received! We'll get back to you within 24–48 hours.")

@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    d = request.get_json(silent=True) or {}
    email = d.get('email','').strip().lower()
    if not email or not valid_email(email): return jsonify(success=False, error='Valid email required.'), 400
    if NewsletterSubscriber.query.filter_by(email=email).first():
        return jsonify(success=False, error='Already subscribed!'), 409
    db.session.add(NewsletterSubscriber(email=email)); db.session.commit()
    send_email(email, "You're subscribed to Inner Compass Project! 🌿",
        f'<div style="font-family:sans-serif"><h2 style="color:#2d9b6a">You\'re in! 🎉</h2>'
        f'<p>Monthly mental health insights coming your way.</p>'
        f'<p><a href="{SITE_URL}/resources">Browse Resources →</a></p>'
        f'<p style="color:#5a7080;font-size:.85rem">Inner Compass Project · Ilorin, Kwara State</p></div>')
    notify_club('New Newsletter Subscriber', f'<p>New: <b>{email}</b></p>')
    return jsonify(success=True, message='Subscribed! Check your email for a welcome message.')

@app.route('/api/mood', methods=['POST'])
def api_mood():
    d = request.get_json(silent=True) or {}
    mood = d.get('mood','').strip(); note = d.get('note','').strip()
    if mood not in {'happy','calm','tired','sad','anxious'}:
        return jsonify(success=False, error='Invalid mood.'), 400
    db.session.add(MoodLog(mood=mood, note=note, user_id=session.get('uid'))); db.session.commit()
    r = {'happy':"That's wonderful! Keep spreading that energy. 🌟",'calm':'Peace is powerful. Stay grounded. 🌿',
         'tired':'Rest is recovery. Be gentle with yourself. 😴','sad':"It's okay to feel this. You are not alone. 💙",
         'anxious':'Take a deep breath. This moment will pass. 🤍'}
    return jsonify(success=True, message=r[mood])

@app.route('/api/stats')
def api_stats(): return jsonify(get_stats())

@app.route('/api/profile', methods=['POST'])
@login_required
def api_profile():
    u = get_user(); d = request.get_json(silent=True) or {}
    name = (d.get('full_name') or d.get('username') or '').strip()
    if name: u.username = name
    u.bio = d.get('bio','').strip(); db.session.commit()
    return jsonify(success=True, message='Profile updated!')

@app.route('/api/admin/message/<int:mid>/read', methods=['POST'])
@login_required
@admin_required
def mark_read(mid):
    m = ContactMessage.query.get_or_404(mid); m.read=True; db.session.commit()
    return jsonify(success=True)

@app.route('/api/admin/program', methods=['POST'])
@login_required
@admin_required
def add_program():
    d = request.get_json(silent=True) or {}
    db.session.add(OutreachProgram(title=d.get('title',''), location=d.get('location',''),
        students_reached=int(d.get('students_reached',0)))); db.session.commit()
    return jsonify(success=True, message='Program added!')

@app.route('/api/admin/user/<int:uid>/role', methods=['POST'])
@login_required
@admin_required
def update_role(uid):
    d = request.get_json(silent=True) or {}; u = User.query.get_or_404(uid)
    if d.get('role') in ('member','admin'): u.role=d['role']; db.session.commit()
    return jsonify(success=True)

# ── API: Executives (with photo upload) ───────────────────────────────────────

@app.route('/api/admin/executive', methods=['POST'])
@login_required
@admin_required
def add_executive():
    import base64
    name  = request.form.get('name','').strip()
    role  = request.form.get('role','').strip()
    bio   = request.form.get('bio','').strip()
    badge = request.form.get('badge','').strip()
    order = int(request.form.get('order', 99) or 99)
    photo_url = ''
    file = request.files.get('photo')
    if file and file.filename:
        try:
            data = file.read()
            mime = file.content_type or 'image/jpeg'
            photo_url = f'data:{mime};base64,{base64.b64encode(data).decode()}'
        except Exception as e:
            return jsonify(success=False, error=f'Photo error: {e}'), 500
    if not name or not role:
        return jsonify(success=False, error='Name and role are required.'), 400
    initials = ''.join(w[0].upper() for w in name.split()[:2])
    db.session.add(Executive(name=name, role=role, bio=bio, badge=badge,
                             initials=initials, photo_url=photo_url, order=order))
    db.session.commit()
    return jsonify(success=True, message=f'{name} added to leadership.')

@app.route('/api/admin/executive/<int:eid>/photo', methods=['POST'])
@login_required
@admin_required
def update_executive_photo(eid):
    import base64
    e = Executive.query.get_or_404(eid)
    file = request.files.get('photo')
    if not file or not file.filename:
        return jsonify(success=False, error='No photo provided.'), 400
    try:
        data = file.read()
        mime = file.content_type or 'image/jpeg'
        e.photo_url = f'data:{mime};base64,{base64.b64encode(data).decode()}'
        db.session.commit()
        return jsonify(success=True, photo_url=e.photo_url, message='Photo updated.')
    except Exception as ex:
        return jsonify(success=False, error=f'Upload failed: {ex}'), 500

@app.route('/api/admin/executive/<int:eid>', methods=['POST'])
@login_required
@admin_required
def update_executive(eid):
    d = request.get_json(silent=True) or {}
    e = Executive.query.get_or_404(eid)
    action = d.get('action','')
    if action == 'delete':
        db.session.delete(e); db.session.commit()
        return jsonify(success=True, message='Executive removed.')
    if action == 'toggle':
        e.active = not e.active; db.session.commit()
        return jsonify(success=True, message='Visibility updated.')
    if d.get('name'):
        e.name = d['name'].strip()
        e.initials = ''.join(w[0].upper() for w in e.name.split()[:2])
    if d.get('role')      is not None: e.role  = d['role'].strip()
    if d.get('bio')       is not None: e.bio   = d['bio'].strip()
    if d.get('badge')     is not None: e.badge = d['badge'].strip()
    if d.get('order')     is not None: e.order = int(d['order'])
    if d.get('photo_url') is not None: e.photo_url = d['photo_url'].strip()
    db.session.commit()
    return jsonify(success=True, message='Executive updated.')

# ── API: Events ───────────────────────────────────────────────────────────────

@app.route('/api/admin/event', methods=['POST'])
@login_required
@admin_required
def add_event():
    d = request.get_json(silent=True) or {}
    title = d.get('title','').strip()
    if not title: return jsonify(success=False, error='Title is required.'), 400
    date = None
    if d.get('event_date'):
        try: date = datetime.fromisoformat(d['event_date'])
        except Exception: pass
    db.session.add(Event(title=title, description=d.get('description','').strip(),
        location=d.get('location','').strip(), event_type=d.get('event_type','general'), event_date=date))
    db.session.commit()
    return jsonify(success=True, message=f'Event "{title}" added.')

@app.route('/api/admin/event/<int:eid>', methods=['POST'])
@login_required
@admin_required
def update_event(eid):
    d = request.get_json(silent=True) or {}; e = Event.query.get_or_404(eid)
    action = d.get('action','')
    if action == 'delete': db.session.delete(e); db.session.commit(); return jsonify(success=True, message='Event removed.')
    if action == 'toggle': e.active=not e.active; db.session.commit(); return jsonify(success=True, message='Updated.')
    if d.get('title'):       e.title       = d['title'].strip()
    if d.get('description') is not None: e.description = d['description'].strip()
    if d.get('location')    is not None: e.location    = d['location'].strip()
    if d.get('event_type'):  e.event_type  = d['event_type']
    if d.get('event_date'):
        try: e.event_date = datetime.fromisoformat(d['event_date'])
        except Exception: pass
    db.session.commit(); return jsonify(success=True, message='Event updated.')

# ── API: Announcements ────────────────────────────────────────────────────────

@app.route('/api/admin/announcement', methods=['POST'])
@login_required
@admin_required
def add_announcement():
    d = request.get_json(silent=True) or {}
    title=d.get('title','').strip(); content=d.get('content','').strip()
    if not title or not content: return jsonify(success=False, error='Title and content are required.'), 400
    db.session.add(Announcement(title=title, content=content,
        link=d.get('link','').strip(), link_text=d.get('link_text','Learn More').strip() or 'Learn More'))
    db.session.commit(); return jsonify(success=True, message='Announcement published.')

@app.route('/api/admin/announcement/<int:aid>', methods=['POST'])
@login_required
@admin_required
def update_announcement(aid):
    d = request.get_json(silent=True) or {}; a = Announcement.query.get_or_404(aid)
    action = d.get('action','')
    if action == 'delete': db.session.delete(a); db.session.commit(); return jsonify(success=True, message='Removed.')
    if action == 'toggle': a.active=not a.active; db.session.commit(); return jsonify(success=True, message='Updated.')
    if d.get('title')     is not None: a.title     = d['title'].strip()
    if d.get('content')   is not None: a.content   = d['content'].strip()
    if d.get('link')      is not None: a.link      = d['link'].strip()
    if d.get('link_text') is not None: a.link_text = d['link_text'].strip() or 'Learn More'
    db.session.commit(); return jsonify(success=True, message='Announcement updated.')

@app.route('/api/health')
def health(): return jsonify(status='ok', time=datetime.utcnow().isoformat())

@app.errorhandler(404)
def e404(e): return render_template('404.html', **ctx()), 404

@app.errorhandler(500)
def e500(e): return f'<h2 style="font-family:sans-serif;color:#e74c3c">Server Error</h2><pre>{e}</pre><a href="/">← Home</a>', 500

# ── Init DB ───────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    ADMIN_EMAIL = CLUB_EMAIL.lower(); ADMIN_PW = 'ICP@Admin2025!'
    if not User.query.filter_by(role='admin').first():
        db.session.add(User(username='Mustapha Abdulrasak', email=ADMIN_EMAIL,
            password_hash=generate_password_hash(ADMIN_PW, method='pbkdf2:sha256'), role='admin'))
        db.session.commit()
    if OutreachProgram.query.count() == 0:
        db.session.add_all([
            OutreachProgram(title='Kwara School Outreach', location='Ilorin', students_reached=240, date=datetime(2025,3,15)),
            OutreachProgram(title='Webinar Series Season 1', location='Online', students_reached=580, date=datetime(2025,5,20)),
            OutreachProgram(title='ICP Summit 2025', location='Ilorin', students_reached=350, date=datetime(2025,11,10)),
        ]); db.session.commit()
    if Executive.query.count() == 0:
        db.session.add_all([
            Executive(name='Mustapha Abdulrasak O.', role='Founder & Executive Director',
                bio='Leading the global vision, strategy, and overall growth of the movement.',
                initials='MA', badge='Founder', order=1),
            Executive(name='Tijani Shehu Ahmad', role='Co-Founder & Associate Director',
                bio='Oversees core organizational programs and collaborative partnerships.',
                initials='TS', order=2),
            Executive(name='Raheemah Ogeke', role='Director, Programs & Training',
                bio='Executes the master curriculum, peer support training, and webinar series.',
                initials='RO', order=3),
            Executive(name='Korede Taiwo', role='Director, Communications & Outreach',
                bio='Leads public messaging, advocacy campaigns, and school partnerships.',
                initials='KT', order=4),
        ]); db.session.commit()
    if Announcement.query.count() == 0:
        db.session.add(Announcement(title='Welcome to The Inner Compass Project!',
            content='Join our upcoming Webinar Series on mental health awareness.',
            link='/signup', link_text='Register Now')); db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
