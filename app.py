import os, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ICP-Secret-2026-XkQ9mPqR!')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///icp.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ── Email config ──────────────────────────────────────────────────────────────
CLUB_EMAIL    = 'Innercompassproject25@gmail.com'
GMAIL_APP_PW  = os.environ.get('GMAIL_APP_PASSWORD', '')   # Set in Railway variables

def send_email(to_addr, subject, html_body):
    """Send email via Gmail SMTP. Silently fails if not configured."""
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

def notify_club(subject, html_body):
    """Send notification to the club inbox."""
    send_email(CLUB_EMAIL, subject, html_body)


# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__  = 'users'
    id             = db.Column(db.Integer, primary_key=True)
    username       = db.Column(db.String(150), nullable=False)
    email          = db.Column(db.String(150), unique=True, nullable=False)
    password_hash  = db.Column(db.String(256), nullable=False)
    role           = db.Column(db.String(20), default='member')
    bio            = db.Column(db.Text, default='')
    joined_at      = db.Column(db.DateTime, default=datetime.utcnow)

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def valid_email(e):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', e))

def get_user():
    uid = session.get('uid')
    return User.query.get(uid) if uid else None

def ctx():
    u = get_user()
    return dict(logged_in=u is not None,
                username=u.username if u else '',
                is_admin=(u.role == 'admin') if u else False,
                user=u)

def login_required(f):
    @wraps(f)
    def dec(*a, **k):
        if not session.get('uid'):
            return redirect(url_for('login_page'))
        return f(*a, **k)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a, **k):
        u = get_user()
        if not u or u.role != 'admin':
            return redirect(url_for('home'))
        return f(*a, **k)
    return dec

def get_stats():
    reached = db.session.query(
        db.func.sum(OutreachProgram.students_reached)).scalar() or 0
    return dict(members=User.query.filter_by(role='member').count(),
                programs=OutreachProgram.query.count(),
                reached=int(reached))


# ── Public Pages ──────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('index.html', stats=get_stats(), **ctx())

@app.route('/resources')
def resources():
    return render_template('resources.html', **ctx())


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    if session.get('uid'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Accept both JSON (fetch) and HTML form
        if request.is_json:
            d = request.get_json(silent=True) or {}
        else:
            d = request.form

        name  = (d.get('full_name') or d.get('username') or '').strip()
        email = (d.get('email') or '').strip().lower()
        pw    = (d.get('password') or '').strip()

        def err(msg):
            if request.is_json:
                return jsonify(success=False, error=msg), 400
            return render_template('signup.html', error=msg, **ctx())

        if not name or not email or not pw:
            return err('All fields are required.')
        if len(pw) < 8:
            return err('Password must be at least 8 characters.')
        if not valid_email(email):
            return err('Please enter a valid email address.')
        if User.query.filter_by(email=email).first():
            return err('An account with this email already exists. Please log in.')

        u = User(username=name, email=email,
                 password_hash=generate_password_hash(pw, method='pbkdf2:sha256'))
        db.session.add(u)
        db.session.commit()

        session['uid']      = u.id
        session['username'] = u.username
        session['is_admin'] = False

        # Welcome email to new member
        send_email(email, 'Welcome to Inner Compass Project! 🧭',
            f'''<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
            <h2 style="color:#2d9b6a">Welcome, {name}! 🌿</h2>
            <p>You've just joined the Inner Compass Project — a community dedicated to mental wellness, 
            growth, and authentic connection.</p>
            <h3>What's next?</h3>
            <ul>
              <li>Access our <a href="https://innercompassproject.up.railway.app/resources">Resource Hub</a></li>
              <li>Track your daily mood on your <a href="https://innercompassproject.up.railway.app/dashboard">Dashboard</a></li>
              <li>Download our <a href="https://drive.google.com/drive/folders/1J3PkAlAbPQRFXikwYcoY3VFdto3Fpi_l">Blueprint & Materials</a></li>
            </ul>
            <p>Together, we are building safer spaces for minds to grow.</p>
            <p style="color:#5a7080;font-size:.9rem">The Inner Compass Project Team<br>
            📞 08145739207 · 07015820935</p></div>''')

        # Notify club of new signup
        notify_club(f'New Member: {name}',
            f'<p>New member signed up:<br><b>Name:</b> {name}<br><b>Email:</b> {email}<br>'
            f'<b>Joined:</b> {datetime.utcnow().strftime("%b %d, %Y %H:%M")}</p>')

        if request.is_json:
            return jsonify(success=True, redirect=url_for('dashboard'))
        return redirect(url_for('dashboard'))

    return render_template('signup.html', **ctx())


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if session.get('uid'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if request.is_json:
            d = request.get_json(silent=True) or {}
        else:
            d = request.form

        email = (d.get('email') or '').strip().lower()
        pw    = (d.get('password') or '').strip()

        def err(msg):
            if request.is_json:
                return jsonify(success=False, error=msg), 401
            return render_template('login.html', error=msg, **ctx())

        if not email or not pw:
            return err('Email and password are required.')

        u = User.query.filter_by(email=email).first()
        if not u or not check_password_hash(u.password_hash, pw):
            return err('Invalid email or password. Please try again.')

        session['uid']      = u.id
        session['username'] = u.username
        session['is_admin'] = (u.role == 'admin')

        if request.is_json:
            return jsonify(success=True, redirect=url_for('dashboard'))
        return redirect(url_for('dashboard'))

    return render_template('login.html', **ctx())


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# ── Hidden Admin Login (not linked anywhere public) ───────────────────────────

@app.route('/icp-admin-login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_panel'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        pw    = request.form.get('password', '').strip()
        u = User.query.filter_by(email=email, role='admin').first()
        if u and check_password_hash(u.password_hash, pw):
            session['uid']      = u.id
            session['username'] = u.username
            session['is_admin'] = True
            return redirect(url_for('admin_panel'))
        error = 'Invalid admin credentials. Check your email and password carefully.'

    return render_template('admin_login.html', error=error)


# ── One-time admin reset (visit once, then delete this route) ─────────────────

@app.route('/icp-reset-admin-now')
def reset_admin():
    email = CLUB_EMAIL.lower()
    pw    = 'ICP@Admin2025!'
    h     = generate_password_hash(pw, method='pbkdf2:sha256')
    u     = User.query.filter_by(email=email).first()
    if u:
        u.password_hash = h
        u.role = 'admin'
        db.session.commit()
        msg = 'Admin password reset!'
    else:
        db.session.add(User(username='Mustapha Abdulrasak',
                            email=email, password_hash=h, role='admin'))
        db.session.commit()
        msg = 'Admin account created!'
    return f'''<div style="font-family:sans-serif;max-width:460px;margin:80px auto;
    text-align:center;padding:2rem;border:2px solid #4ead7d;border-radius:16px">
    <h2 style="color:#2d9b6a">✅ {msg}</h2>
    <p><b>Email:</b> {email}</p><p><b>Password:</b> {pw}</p><br>
    <a href="/icp-admin-login" style="background:#4ead7d;color:white;padding:.75rem 2rem;
    border-radius:100px;text-decoration:none;font-weight:500">Go to Admin Login →</a><br><br>
    <p style="color:#e74c3c;font-size:.82rem">⚠️ Delete this route from app.py after logging in!</p>
    </div>'''


# ── Protected Pages ───────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    u  = get_user()
    ml = MoodLog.query.filter_by(user_id=u.id)\
                      .order_by(MoodLog.logged_at.desc()).limit(7).all()
    return render_template('dashboard.html', stats=get_stats(), mood_logs=ml, **ctx())


@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    return render_template('admin.html',
        users    = User.query.order_by(User.joined_at.desc()).all(),
        messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all(),
        programs = OutreachProgram.query.order_by(OutreachProgram.date.desc()).all(),
        subscribers = NewsletterSubscriber.query.order_by(NewsletterSubscriber.subscribed_at.desc()).all(),
        stats    = get_stats(),
        unread   = ContactMessage.query.filter_by(read=False).count(),
        **ctx())


# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/contact', methods=['POST'])
def api_contact():
    d       = request.get_json(silent=True) or {}
    name    = d.get('name', '').strip()
    email   = d.get('email', '').strip()
    subject = d.get('subject', '').strip()
    message = d.get('message', '').strip()

    if not all([name, email, subject, message]):
        return jsonify(success=False, error='All fields are required.'), 400
    if not valid_email(email):
        return jsonify(success=False, error='Invalid email address.'), 400

    db.session.add(ContactMessage(
        name=name, email=email, subject=subject, message=message))
    db.session.commit()

    # Send to club inbox
    notify_club(f'New Contact Message: {subject}',
        f'''<div style="font-family:sans-serif">
        <h3>New message from {name}</h3>
        <p><b>Email:</b> <a href="mailto:{email}">{email}</a></p>
        <p><b>Subject:</b> {subject}</p>
        <p><b>Message:</b></p>
        <p style="background:#f5f5f5;padding:1rem;border-radius:8px">{message}</p>
        <p><a href="mailto:{email}?subject=Re: {subject}">Reply to {name}</a></p>
        </div>''')

    # Auto-reply to sender
    send_email(email, f'We received your message — Inner Compass Project',
        f'''<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
        <h2 style="color:#2d9b6a">We got your message, {name}! 📬</h2>
        <p>Thank you for reaching out to the Inner Compass Project. 
        We'll get back to you within 24–48 hours.</p>
        <p><b>Your message:</b></p>
        <p style="background:#f5f5f5;padding:1rem;border-radius:8px;font-style:italic">
        "{message}"</p>
        <p>In the meantime, explore our resources at 
        <a href="https://innercompassproject.up.railway.app/resources">innercompassproject.up.railway.app</a></p>
        <p style="color:#5a7080;font-size:.9rem">The Inner Compass Project Team<br>
        📞 08145739207 · 07015820935</p></div>''')

    return jsonify(success=True,
                   message="Message received! We'll get back to you within 24–48 hours.")


@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    d     = request.get_json(silent=True) or {}
    email = d.get('email', '').strip().lower()
    if not email or not valid_email(email):
        return jsonify(success=False, error='A valid email is required.'), 400
    if NewsletterSubscriber.query.filter_by(email=email).first():
        return jsonify(success=False, error='You are already subscribed!'), 409

    db.session.add(NewsletterSubscriber(email=email))
    db.session.commit()

    # Welcome newsletter email
    send_email(email, 'You\'re subscribed to Inner Compass Project! 🌿',
        f'''<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
        <h2 style="color:#2d9b6a">You're in! 🎉</h2>
        <p>You've subscribed to the Inner Compass Project newsletter. 
        Expect monthly mental health insights, program updates, and community stories.</p>
        <p>While you wait for the next issue, explore:</p>
        <ul>
          <li><a href="https://innercompassproject.up.railway.app/resources">Resource Hub</a></li>
          <li><a href="https://drive.google.com/drive/folders/1J3PkAlAbPQRFXikwYcoY3VFdto3Fpi_l">Google Drive Library</a></li>
          <li><a href="https://chatgpt.com/g/g-6960476953a88191b94a38dfe2a9ba0b-inner-compass-guide">AI Wellness Guide</a></li>
        </ul>
        <p style="color:#5a7080;font-size:.85rem">
        To unsubscribe, reply to this email with "unsubscribe".<br>
        Inner Compass Project · Ilorin, Kwara State, Nigeria</p></div>''')

    # Notify club
    notify_club('New Newsletter Subscriber',
        f'<p>New subscriber: <b>{email}</b><br>'
        f'Subscribed: {datetime.utcnow().strftime("%b %d, %Y %H:%M")}</p>')

    return jsonify(success=True,
                   message='Subscribed! Check your email for a welcome message.')


@app.route('/api/mood', methods=['POST'])
def api_mood():
    d    = request.get_json(silent=True) or {}
    mood = d.get('mood', '').strip()
    note = d.get('note', '').strip()
    if mood not in {'happy', 'calm', 'tired', 'sad', 'anxious'}:
        return jsonify(success=False, error='Invalid mood.'), 400
    db.session.add(MoodLog(mood=mood, note=note, user_id=session.get('uid')))
    db.session.commit()
    responses = {
        'happy':   "That's wonderful! Keep spreading that energy. 🌟",
        'calm':    'Peace is powerful. Stay grounded. 🌿',
        'tired':   'Rest is recovery. Be gentle with yourself. 😴',
        'sad':     'It\'s okay to feel this. You are not alone. 💙',
        'anxious': 'Take a deep breath. This moment will pass. 🤍',
    }
    return jsonify(success=True, message=responses[mood])


@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


@app.route('/api/profile', methods=['POST'])
@login_required
def api_profile():
    u    = get_user()
    d    = request.get_json(silent=True) or {}
    name = (d.get('full_name') or d.get('username') or '').strip()
    if name:
        u.username          = name
        session['username'] = name
    u.bio = d.get('bio', '').strip()
    db.session.commit()
    return jsonify(success=True, message='Profile updated!')


@app.route('/api/admin/message/<int:mid>/read', methods=['POST'])
@login_required
@admin_required
def mark_read(mid):
    m = ContactMessage.query.get_or_404(mid)
    m.read = True
    db.session.commit()
    return jsonify(success=True)


@app.route('/api/admin/program', methods=['POST'])
@login_required
@admin_required
def add_program():
    d = request.get_json(silent=True) or {}
    db.session.add(OutreachProgram(
        title=d.get('title', ''),
        location=d.get('location', ''),
        students_reached=int(d.get('students_reached', 0))))
    db.session.commit()
    return jsonify(success=True, message='Program added!')


@app.route('/api/admin/user/<int:uid>/role', methods=['POST'])
@login_required
@admin_required
def update_role(uid):
    d = request.get_json(silent=True) or {}
    u = User.query.get_or_404(uid)
    if d.get('role') in ('member', 'admin'):
        u.role = d['role']
        db.session.commit()
    return jsonify(success=True)


@app.route('/api/health')
def health():
    return jsonify(status='ok', time=datetime.utcnow().isoformat())


@app.errorhandler(404)
def e404(e):
    return render_template('404.html', **ctx()), 404

@app.errorhandler(500)
def e500(e):
    return f'<h2 style="font-family:sans-serif">500 Error</h2><pre>{e}</pre><a href="/">← Home</a>', 500


# ── Init DB ───────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

    ADMIN_EMAIL = CLUB_EMAIL.lower()
    ADMIN_PW    = 'ICP@Admin2025!'

    # Create admin if none exists
    if not User.query.filter_by(role='admin').first():
        db.session.add(User(
            username='Mustapha Abdulrasak',
            email=ADMIN_EMAIL,
            password_hash=generate_password_hash(ADMIN_PW, method='pbkdf2:sha256'),
            role='admin'))
        db.session.commit()

    # Seed programs so counters are never 0
    if OutreachProgram.query.count() == 0:
        db.session.add_all([
            OutreachProgram(title='Kwara School Outreach',
                            location='Ilorin', students_reached=240,
                            date=datetime(2025, 3, 15)),
            OutreachProgram(title='Webinar Series — Season 1',
                            location='Online', students_reached=580,
                            date=datetime(2025, 5, 20)),
            OutreachProgram(title='ICP Summit 2025',
                            location='Ilorin', students_reached=350,
                            date=datetime(2025, 11, 10)),
        ])
        db.session.commit()


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            debug=False)
