from flask import Flask
from dotenv import load_dotenv
import os
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configure the app
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'temp')
    app.config['ALLOWED_EXTENSIONS'] = {'zip'}
    app.config['MAX_CONTENT_PATH'] = None  # No path length limit
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for uploaded files
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
    app.config['MAX_CONTENT_PATH'] = None  # No path length limit
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for uploaded files
    
    # Increase buffer size for large file uploads
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Clean up temp_images directory on startup
    temp_images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'temp_images')
    if os.path.exists(temp_images_dir):
        for filename in os.listdir(temp_images_dir):
            file_path = os.path.join(temp_images_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not remove {file_path}: {e}")
    else:
        os.makedirs(temp_images_dir, exist_ok=True)
    
    # Register blueprints
    from app.routes import main, limiter
    limiter.init_app(app)
    app.register_blueprint(main)
    
    return app 