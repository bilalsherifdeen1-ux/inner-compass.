import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# --- CONFIGURATION ---
# The Secret Key encrypts the user's login session
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_development_key')

# Fix Railway's postgres:// to postgresql:// for SQLAlchemy compatibility
db_url = os.environ.get('DATABASE_URL', 'sqlite:///local.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database and Login Manager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirects here if not logged in

# Cloudinary Setup
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
if CLOUDINARY_URL:
    try:
        cloudinary.config(secure=True)
    except Exception:
        pass

# --- DATABASE MODEL ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables before the first request
with app.app_context():
    db.create_all()

# --- PUBLIC ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

# --- AUTHENTICATION ROUTES ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            return "Email already registered. Go back and log in.", 400
            
        # Hash the password for maximum security
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Create new user
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        # Log them in automatically
        login_user(new_user)
        return redirect(url_for('dashboard'))
        
    return render_template('auth.html', action="signup")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # Verify user and password
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            return "Invalid email or password. Go back and try again.", 401
            
    return render_template('auth.html', action="login")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- PROTECTED ROUTES (Members Only) ---
@app.route('/dashboard')
@login_required
def dashboard():
    return f"""
    <div style='font-family: sans-serif; text-align: center; padding: 50px;'>
        <h2 style='color: #195c70;'>Welcome to your True North, {current_user.username}!</h2>
        <p>This is the private member portal. Only logged-in members can see this.</p>
        <a href='/' style='padding: 10px 20px; background: #6bb274; color: white; text-decoration: none; border-radius: 5px;'>Back to Home</a>
        <br><br>
        <a href='/logout' style='color: #e11d48;'>Log Out</a>
    </div>
    """

# --- ADMIN UPLOAD ROUTE ---
@app.route('/upload-page')
def upload_page():
    return render_template('upload.html') # Assuming you kept your upload.html

@app.route('/upload', methods=['POST'])
def handle_upload():
    # ... (Keep your existing Cloudinary upload logic here) ...
    pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
