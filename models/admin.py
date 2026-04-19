from datetime import datetime, timezone

from models import db


class Admin(db.Model):
    __tablename__ = 'admins'

    aid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    admin_info = db.relationship('AdminInfo', backref='admin', uselist=False, cascade='all, delete-orphan')


class AdminInfo(db.Model):
    __tablename__ = 'admin_info'

    aid = db.Column(db.Integer, db.ForeignKey('admins.aid', ondelete='CASCADE'), primary_key=True)
    avatar_id = db.Column(db.Integer, db.ForeignKey('files.fid', ondelete='SET NULL'), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    basic_info = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    avatar = db.relationship('File', foreign_keys=[avatar_id], post_update=True)