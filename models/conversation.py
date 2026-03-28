from datetime import datetime, timezone

from models import db


class ConversationSession(db.Model):
    """AI 对话会话"""
    __tablename__ = 'conversation_sessions'

    sid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    messages = db.relationship('Message', backref='session', lazy='dynamic', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_conversation_sessions_uid', 'uid'),
    )


class Message(db.Model):
    """AI 对话消息"""
    __tablename__ = 'messages'

    mid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sid = db.Column(db.Integer, db.ForeignKey('conversation_sessions.sid', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_messages_sid', 'sid'),
    )
