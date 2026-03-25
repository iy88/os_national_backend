from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User, UserInfo, File

__all__ = ['db', 'User', 'UserInfo', 'File']
