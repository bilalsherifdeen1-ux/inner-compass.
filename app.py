import os
from flask import Flask, render_template, request
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# This prevents the crash even if the URL is formatted wrong
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')

if CLOUDINARY_URL:
    try:
        cloudinary.config(secure=True)
    except Exception:
        pass

@app.route('/')
def home():
    if not CLOUDINARY_URL:
        return "<h3>Inner Compass: System Missing Keys</h3><p>Please add CLOUDINARY_URL to Railway Variables.</p>"
    return "<h3>Inner Compass is Live!</h3><p>Visit <a href='/upload-page'>/upload-page</a> to upload files.</p>"

@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    file = request.files.get('file_to_upload')
    if file:
        try:
            folder = "inner_compass_docs" if file.filename.endswith('.pdf') else "inner_compass_images"
            result = cloudinary.uploader.upload(file, folder=folder)
            return f"Success! Link: <a href='{result['secure_url']}'>{result['secure_url']}</a>"
        except Exception as e:
            return f"Upload Error: {str(e)}"
    return "No file selected", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
