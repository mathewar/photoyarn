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
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    return app 