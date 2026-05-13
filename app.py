import os
from flask import Flask, render_template, request
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# SAFE CONFIG: Only configures if the variable exists
cloudinary_url = os.environ.get('CLOUDINARY_URL')
if cloudinary_url:
    cloudinary.config(secure=True)

@app.route('/')
def home():
    return "Inner Compass is running! Cloudinary is " + ("Connected" if cloudinary_url else "Not Connected")

@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    if not cloudinary_url:
        return "System Error: Cloudinary keys are missing in Railway Variables.", 500
        
    file = request.files.get('file_to_upload')
    if file:
        try:
            result = cloudinary.uploader.upload(file, folder="inner_compass")
            return f"Success! Link: {result['secure_url']}"
        except Exception as e:
            return f"Upload Failed: {str(e)}", 500
    return "No file selected", 400

if __name__ == "__main__":
    # Important for Railway: it needs to bind to 0.0.0.0
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
