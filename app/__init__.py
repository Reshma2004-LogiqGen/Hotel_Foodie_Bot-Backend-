"""
Food Friend Backend - Flask App Initialization
"""

import os
import secrets

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request, send_from_directory
from flask_cors import CORS
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException

from app.extensions import db

# Load environment variables
load_dotenv()

MAX_UPLOAD_MB = 5
PHOTO_CACHE_SECONDS = 7 * 24 * 60 * 60


@event.listens_for(Engine, 'connect')
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith('sqlite3'):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()


def _load_secret_key(instance_path):
    """Use SECRET_KEY from .env, otherwise a random key kept in the instance folder."""
    key = os.getenv('SECRET_KEY')
    if key:
        return key
    key_path = os.path.join(instance_path, 'secret_key')
    if os.path.exists(key_path):
        with open(key_path, encoding='utf-8') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(key_path, 'w', encoding='utf-8') as f:
        f.write(key)
    return key


def _database_url(instance_path):
    """DATABASE_URL from .env (e.g. a hosted PostgreSQL), otherwise SQLite in the instance folder."""
    url = os.getenv('DATABASE_URL')
    if not url:
        return 'sqlite:///' + os.path.join(instance_path, 'food_friend.db')
    # Hosts hand out postgres:// URLs; SQLAlchemy needs the installed driver (psycopg 3) named.
    for prefix in ('postgres://', 'postgresql://'):
        if url.startswith(prefix):
            return 'postgresql+psycopg://' + url[len(prefix):]
    return url


def _cors_origins():
    """CORS_ORIGINS from .env as a comma-separated list of frontend addresses, or every origin."""
    origins = [o.strip().rstrip('/') for o in os.getenv('CORS_ORIGINS', '').split(',') if o.strip()]
    return origins or '*'


def _register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if not request.path.startswith('/api/'):
            return error
        message = 'Image is too large. Maximum size is 5 MB.' if error.code == 413 else error.description
        return jsonify({'error': message}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception('Unhandled error on %s', request.path)
        db.session.rollback()
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500


def create_app():
    """Create and configure the Flask app"""
    app = Flask(__name__)
    os.makedirs(app.instance_path, exist_ok=True)

    upload_folder = os.path.join(os.path.dirname(app.root_path), 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    CORS(app, resources={
        r"/api/*": {
            "origins": _cors_origins(),
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        }
    })

    # Load config
    app.config['SECRET_KEY'] = _load_secret_key(app.instance_path)
    app.config['SQLALCHEMY_DATABASE_URI'] = _database_url(app.instance_path)
    # Hosted databases drop idle connections; check each one before it is reused.
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
    app.config['UPLOAD_FOLDER'] = upload_folder
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

    db.init_app(app)
    
    from app.services import ai_service
    if ai_service.is_configured():
        print(f"✅ OpenAI ready (model: {ai_service.model_name()})")
    else:
        print("⚠️  OPENAI_API_KEY not found: the chat buddies will not work (nutrition uses the built-in table).")
        print("   Add it to the .env file: OPENAI_API_KEY=your_key_here")
        print("   Get a key from: https://platform.openai.com/api-keys")

    # Register blueprints
    from app.routes.chat import chat_bp
    from app.routes.nutrition import nutrition_bp
    from app.routes.public import public_bp
    from app.routes.admin_auth import admin_auth_bp
    from app.routes.admin_menu import admin_menu_bp
    from app.routes.admin_tables import admin_tables_bp
    from app.routes.admin_staff import admin_staff_bp
    from app.routes.kitchen import kitchen_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(nutrition_bp, url_prefix='/api')
    app.register_blueprint(public_bp, url_prefix='/api')
    app.register_blueprint(admin_auth_bp, url_prefix='/api')
    app.register_blueprint(admin_menu_bp, url_prefix='/api')
    app.register_blueprint(admin_tables_bp, url_prefix='/api')
    app.register_blueprint(admin_staff_bp, url_prefix='/api')
    app.register_blueprint(kitchen_bp, url_prefix='/api')

    _register_error_handlers(app)

    with app.app_context():
        from app import models  # noqa: F401  (registers tables)
        from app.schema_upgrade import upgrade_schema
        db.create_all()
        upgrade_schema()

    from app.models import UploadedImage

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        """Photos live in the database; older ones may still be files in the uploads folder."""
        image = UploadedImage.query.filter_by(filename=filename).first()
        if image is None:
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename, max_age=PHOTO_CACHE_SECONDS)
        response = make_response(image.data)
        response.headers['Content-Type'] = image.content_type
        response.headers['Cache-Control'] = f'public, max-age={PHOTO_CACHE_SECONDS}, immutable'
        return response
    
    # Health check route
    @app.route('/api/health')
    def health_check():
        return {
            'status': 'healthy',
            'ai_configured': ai_service.is_configured(),
            'message': 'Food Friend API is running! 🍕'
        }
    
    # Root route
    @app.route('/')
    def root():
        return {
            'name': 'Food Friend API',
            'version': '1.0.0',
            'endpoints': {
                'health': '/api/health',
                'menu': '/api/menu?code=<table QR code> (GET)',
                'place_order': '/api/orders (POST, with the table QR code)',
                'track_order': '/api/orders/<order number>?code=<table QR code> (GET)',
                'nutrition': '/api/orders/<order number>/nutrition?code=<table QR code> (GET)',
                'chat': '/api/chat (POST, with the table QR code and order number)',
                'staff_auth': '/api/auth/register, /api/auth/login (POST)',
                'kitchen': '/api/kitchen/orders (chef or admin login required)',
                'admin': '/api/admin/... (admin login required)'
            }
        }
    
    print("✅ Food Friend Backend initialized!")
    
    return app
