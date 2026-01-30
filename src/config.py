import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

    @staticmethod
    def init_app(app):
        # Production Safety Checks
        if not app.debug:
            if Config.SECRET_KEY == 'dev-key-please-change':
                raise ValueError("CRITICAL: You are running in Production with the default SECRET_KEY. Change it in .env")
            if not Config.ENCRYPTION_KEY or Config.ENCRYPTION_KEY == 'GenerateMeAndPutHere========================':
                raise ValueError("CRITICAL: You are running in Production with an invalid ENCRYPTION_KEY. Change it in .env")
