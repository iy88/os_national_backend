from datetime import datetime, timezone

from models import db


class Admin(db.Model):
    """管理员表，仅存储 uid，标识某用户为管理员"""
    __tablename__ = 'admins'

    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
