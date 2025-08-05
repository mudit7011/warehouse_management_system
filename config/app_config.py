import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///wms.db'
    
    # Baserow
    BASEROW_API_TOKEN = os.environ.get('BASEROW_API_TOKEN')
    BASEROW_BASE_URL = os.environ.get('BASEROW_BASE_URL') or 'https://api.baserow.io'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}