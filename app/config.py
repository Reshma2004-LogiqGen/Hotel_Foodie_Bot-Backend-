"""
Food Friend Backend - Configuration Settings
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'food-friend-secret-key')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # GROQ Model Settings
    GROQ_MODEL = "llama-3.3-70b-versatile"
    MAX_TOKENS = 150
    TEMPERATURE = 0.8
    
    # API Settings
    API_TIMEOUT = 30


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
