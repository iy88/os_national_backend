from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User, UserInfo, File
from models.conversation import ConversationSession, Message
from models.route import Route
from models.roleplay import RoleplayCharacter, RoleplayCharacterDetail, RoleplaySession, RoleplayMessage
from models.admin import Admin, AdminInfo

__all__ = [
    'db',
    'User', 'UserInfo', 'File',
    'ConversationSession', 'Message',
    'Route',
    'RoleplayCharacter', 'RoleplayCharacterDetail', 'RoleplaySession', 'RoleplayMessage',
    'Admin', 'AdminInfo',
]
