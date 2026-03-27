from datetime import datetime

from models import db


class Route(db.Model):
    """收藏的旅行路线"""
    __tablename__ = 'routes'

    rid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False)
    mid = db.Column(db.Integer, db.ForeignKey('messages.mid', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_routes_uid', 'uid'),
        db.Index('idx_routes_mid', 'mid'),
    )
