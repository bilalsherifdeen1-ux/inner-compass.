import os
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Enables cross-origin requests

# Database Configuration 
db_url = os.environ.get('DATABASE_URL', 'sqlite:///local_development.db')

# SQLAlchemy requires 'postgresql://' but some providers use 'postgres://'
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Updated Database Model for storing new members and executives
class InnerCompassMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    role = db.Column(db.String(50), nullable=False) # 'Member' or 'Executive'
    message = db.Column(db.Text, nullable=True)     # Optional message field
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# Route to serve the Frontend HTML
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# API Endpoint to handle form submissions
@app.route('/api/join', methods=['POST'])
def join_project():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    role = data.get('role')
    message = data.get('message', '') # Defaults to empty string if not provided

    # Basic Validation
    if not name or not email or not role:
        return jsonify({'error': 'Please fill out all required fields.'}), 400

    if role not in ['Member', 'Executive']:
        return jsonify({'error': 'Invalid role selected.'}), 400

    try:
        # Check if email already registered
        existing_user = InnerCompassMember.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'This email is already registered.'}), 409

        # Save to PostgreSQL
        new_member = InnerCompassMember(
            name=name, 
            email=email, 
            role=role,
            message=message
        )
        db.session.add(new_member)
        db.session.commit()
        
        return jsonify({'message': 'Application recorded successfully.'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Railway passes the PORT env variable automatically
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
