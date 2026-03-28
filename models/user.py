from datetime import datetime, timezone

from models import db


class User(db.Model):
    __tablename__ = 'users'

    uid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user_info = db.relationship('UserInfo', backref='user', uselist=False, cascade='all, delete-orphan')


class UserInfo(db.Model):
    __tablename__ = 'user_info'

    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), primary_key=True)
    avatar_id = db.Column(db.Integer, db.ForeignKey('files.fid', ondelete='SET NULL'), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    basic_info = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    avatar = db.relationship('File', foreign_keys=[avatar_id], post_update=True)

    __table_args__ = (
        db.Index('idx_user_info_uid', 'uid'),
    )


class File(db.Model):
    __tablename__ = 'files'

    fid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    secure_filename = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_files_uid', 'uid'),
        db.Index('idx_files_secure_filename', 'secure_filename'),
    )
