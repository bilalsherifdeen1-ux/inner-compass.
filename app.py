import os
from flask import Flask, request
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# 1. Pull the Cloudinary URL from Railway's Variables
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')

if CLOUDINARY_URL:
    try:
        cloudinary.config(secure=True)
    except Exception:
        pass

# 2. The Main Home Page
@app.route('/')
def home():
    if not CLOUDINARY_URL:
        return "<h3>System Status: Missing Keys</h3><p>Please add CLOUDINARY_URL to Railway Variables.</p>"
    return "<h3>Inner Compass is Live!</h3><p>Visit <a href='/upload-page'>/upload-page</a> to upload your logo or PDFs.</p>"

# 3. The Upload Page (HTML is included here so you don't need a separate file)
@app.route('/upload-page')
def upload_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Inner Compass Upload</title>
        <style>
            body { font-family: sans-serif; padding: 20px; line-height: 1.6; }
            .card { border: 1px solid #ccc; padding: 20px; border-radius: 10px; max-width: 400px; }
            button { background: #007bff; color: white; border: none; padding: 10px; border-radius: 5px; width: 100%; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Inner Compass Project</h2>
            <p>Select your Logo (PNG/JPG) or Project PDF to upload.</p>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <input type="file" name="file_to_upload" accept=".pdf, .png, .jpg, .jpeg" style="margin-bottom: 20px;">
                <button type="submit">Upload Now</button>
            </form>
        </div>
    </body>
    </html>
    '''

# 4. The Logic that handles the Upload
@app.route('/upload', methods=['POST'])
def handle_upload():
    file = request.files.get('file_to_upload')
    if file:
        try:
            # Sorts files automatically based on the extension
            folder = "inner_compass_docs" if file.filename.endswith('.pdf') else "inner_compass_images"
            result = cloudinary.uploader.upload(file, folder=folder)
            
            return f"""
            <h3>Upload Successful!</h3>
            <p>Your file is safe in the cloud. Copy this link:</p>
            <textarea style="width:100%; height:80px;" readonly>{result['secure_url']}</textarea>
            <br><br>
            <a href="/upload-page">Upload another file</a>
            """
        except Exception as e:
            return f"Upload Error: {str(e)}"
    return "No file selected", 400

if __name__ == "__main__":
    # This part is critical for Railway to stay online
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

