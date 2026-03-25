from flask import Blueprint

from routes.user import user_bp
from routes.email import email_bp

__all__ = ['user_bp', 'email_bp']
