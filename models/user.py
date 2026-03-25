from datetime import datetime

from models import db


class User(db.Model):
    __tablename__ = 'users'

    uid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_info = db.relationship('UserInfo', backref='user', uselist=False, cascade='all, delete-orphan')


class UserInfo(db.Model):
    __tablename__ = 'user_info'

    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), primary_key=True)
    gender = db.Column(db.String(10), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    basic_info = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.String(500), nullable=True)  # 头像存储路径/URL

    __table_args__ = (
        db.Index('idx_user_info_uid', 'uid'),
    )
