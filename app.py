import os
from flask import Flask, request, render_template
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# Pull the Cloudinary URL from Railway's Variables
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')

if CLOUDINARY_URL:
    try:
        cloudinary.config(secure=True)
    except Exception:
        pass

# The Main Home Page (Now loads your beautiful index.html)
@app.route('/')
def home():
    if not CLOUDINARY_URL:
        return "<h3>System Status: Missing Keys</h3><p>Please add CLOUDINARY_URL to Railway Variables.</p>"
    return render_template('index.html')

# The Admin Upload Page
@app.route('/upload-page')
def upload_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Upload - Inner Compass</title>
        <style>
            body { font-family: sans-serif; padding: 20px; line-height: 1.6; background: #fdfdfd; }
            .card { border: 1px solid #ccc; padding: 20px; border-radius: 10px; max-width: 400px; margin: 0 auto; background: white; }
            button { background: #0056b3; color: white; border: none; padding: 10px; border-radius: 5px; width: 100%; cursor: pointer; font-weight: bold;}
            a { color: #0056b3; text-decoration: none; display: block; text-align: center; margin-top: 15px;}
        </style>
    </head>
    <body>
        <div class="card">
            <h2 style="text-align: center;">Upload New Files</h2>
            <p>Select a Logo (PNG/JPG) or Document (PDF) to upload to the cloud.</p>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <input type="file" name="file_to_upload" accept=".pdf, .png, .jpg, .jpeg" style="margin-bottom: 20px; width: 100%;">
                <button type="submit">Upload to Cloud</button>
            </form>
            <a href="/">&larr; Back to Home</a>
        </div>
    </body>
    </html>
    '''

# The Logic that handles the Uploads
@app.route('/upload', methods=['POST'])
def handle_upload():
    file = request.files.get('file_to_upload')
    if file:
        try:
            folder = "inner_compass_docs" if file.filename.endswith('.pdf') else "inner_compass_images"
            result = cloudinary.uploader.upload(file, folder=folder)
            
            return f"""
            <div style="font-family: sans-serif; max-width: 500px; margin: 40px auto; padding: 20px; border: 1px solid #ccc; border-radius: 10px;">
                <h3 style="color: green;">Upload Successful!</h3>
                <p>Your file is safe in the cloud. Copy this link to use in your code:</p>
                <textarea style="width:100%; height:80px; padding: 10px; border-radius: 5px; border: 1px solid #aaa;" readonly>{result['secure_url']}</textarea>
                <br><br>
                <a href="/upload-page" style="color: #0056b3; text-decoration: none;">&uarr; Upload another file</a> | 
                <a href="/" style="color: #555; text-decoration: none;">&larr; View Website</a>
            </div>
            """
        except Exception as e:
            return f"Upload Error: {str(e)}"
    return "No file selected", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

