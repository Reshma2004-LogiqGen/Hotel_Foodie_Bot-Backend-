"""
Food Friend Backend - Flask App Initialization
"""

from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_app():
    """Create and configure the Flask app"""
    app = Flask(__name__)
    
    # Enable CORS for all origins (required for mobile access)
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"]
        }
    })
    
    # Load config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
    
    # Check for GROQ API key
    if not app.config['GROQ_API_KEY']:
        print("⚠️  WARNING: GROQ_API_KEY not found!")
        print("   Create a .env file with: GROQ_API_KEY=your_key_here")
        print("   Get your API key from: https://console.groq.com/keys")
    else:
        print(f"✅ GROQ API key loaded (starts with: {app.config['GROQ_API_KEY'][:10]}...)")
    
    # Register blueprints
    from app.routes.chat import chat_bp
    from app.routes.order import order_bp
    from app.routes.nutrition import nutrition_bp
    
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(order_bp, url_prefix='/api')
    app.register_blueprint(nutrition_bp, url_prefix='/api')
    
    # Health check route
    @app.route('/api/health')
    def health_check():
        return {
            'status': 'healthy',
            'groq_configured': bool(app.config['GROQ_API_KEY']),
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
                'chat': '/api/chat (POST)',
                'orders': '/api/orders (GET)',
                'order': '/api/order (POST)',
                'nutrition': '/api/nutrition/generate (POST)'
            }
        }
    
    print("✅ Food Friend Backend initialized!")
    
    return app