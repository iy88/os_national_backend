from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User, UserInfo, File
from models.conversation import ConversationSession, Message
from models.route import Route
from models.roleplay import RoleplayCharacter, RoleplayCharacterDetail, RoleplaySession, RoleplayMessage
from models.travel import (
    TravelRecommendation,
    RecommendationPlayer,
    RecommendationHero,
    RecommendationEsportsInfo,
    RecommendationFood,
    RecommendationTravelTip,
    RecommendationTask,
    RecommendationRoute,
)
from models.admin import Admin

__all__ = [
    'db',
    'User', 'UserInfo', 'File',
    'ConversationSession', 'Message',
    'Route',
    'RoleplayCharacter', 'RoleplayCharacterDetail', 'RoleplaySession', 'RoleplayMessage',
    'TravelRecommendation',
    'RecommendationPlayer', 'RecommendationHero',
    'RecommendationEsportsInfo', 'RecommendationFood',
    'RecommendationTravelTip', 'RecommendationTask', 'RecommendationRoute',
    'Admin',
]
