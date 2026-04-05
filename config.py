import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    FLASK_DEBUG = FLASK_ENV == 'development'

    # MySQL
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD') or None

    # SMTP
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
    SMTP_USE_SSL = os.getenv('SMTP_USE_SSL', 'true').lower() == 'true'
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_SENDER = os.getenv('SMTP_SENDER')
    SMTP_SENDER_NAME = os.getenv('SMTP_SENDER_NAME', '城竞共生')

    # JWT
    JWT_SECRET = os.getenv('JWT_SECRET')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 168))

    # File Upload
    UPLOAD_FOLDER = os.path.join(basedir, os.getenv('UPLOAD_FOLDER', 'uploads/files'))
    MAX_AVATAR_SIZE = int(os.getenv('MAX_AVATAR_SIZE', 2 * 1024 * 1024))  # 2MB
    ALLOWED_AVATAR_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # AI Provider
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'dashscope')
    AI_API_KEY = os.getenv('AI_API_KEY')
    AI_APP_ID = os.getenv('AI_APP_ID')
    AI_TITLE_MODEL = os.getenv('AI_TITLE_MODEL', 'qwen3.5-plus')

    # Roleplay App IDs
    ROLEPLAY_APP_ID_GAME_EXPERT = os.getenv('ROLEPLAY_APP_ID_GAME_EXPERT')
    ROLEPLAY_APP_ID_ESPORTS_PLAYER = os.getenv('ROLEPLAY_APP_ID_ESPORTS_PLAYER')
    ROLEPLAY_APP_ID_GAME_HERO = os.getenv('ROLEPLAY_APP_ID_GAME_HERO')

    # Roleplay type to app_id mapping
    ROLEPLAY_APP_ID_MAP = {
        'game_expert': ROLEPLAY_APP_ID_GAME_EXPERT,
        'esports_player': ROLEPLAY_APP_ID_ESPORTS_PLAYER,
        'game_hero': ROLEPLAY_APP_ID_GAME_HERO,
    }
