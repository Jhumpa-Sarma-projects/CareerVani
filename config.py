import os

class Config:
    # Basic Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'

    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///career_vani.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail Config (for sending PDF reports)
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'jhumpasarma53@gmail.com'
    MAIL_PASSWORD = 'iopt pyng wqkw ajcg'  # App password
    MAIL_DEFAULT_SENDER = MAIL_USERNAME
    MAIL_DEBUG = True  
