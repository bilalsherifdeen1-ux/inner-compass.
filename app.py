import os
from flask import Flask, render_template, request
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# This pulls the CLOUDINARY_URL automatically from Railway
cloudinary.config(secure=True)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def is_allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return "Inner Compass Project is Live! Visit /upload-page to upload files."

@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    file = request.files.get('file_to_upload')
    
    if file and is_allowed(file.filename):
        # Sorts files: PDFs to docs folder, Images to images folder
        folder_name = "inner_compass_docs" if file.filename.endswith('.pdf') else "inner_compass_images"
        
        # Uploads the file from your phone to Cloudinary
        result = cloudinary.uploader.upload(file, folder=folder_name)
        
        # Returns the link you need for your website
        return f"""
        <h3>Upload Successful!</h3>
        <p>Copy this link to use in your code:</p>
        <input type="text" value="{result['secure_url']}" style="width:100%;" readonly>
        <br><br>
        <a href="/upload-page">Upload another file</a>
        """
    
    return "Error: Invalid file type. Use PNG, JPG, or PDF.", 400
