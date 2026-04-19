from datetime import datetime, timezone

from models import db


class RoleplayCharacter(db.Model):
    """角色基础信息"""
    __tablename__ = 'roleplay_characters'

    rid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String(20), nullable=False)  # game_expert / esports_player / game_hero
    name = db.Column(db.String(80), nullable=False)  # 角色显示名
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rc_type', 'type'),
    )

    detail = db.relationship('RoleplayCharacterDetail', backref='character', uselist=False, cascade='all, delete-orphan')


class RoleplayCharacterDetail(db.Model):
    """角色详情"""
    __tablename__ = 'roleplay_character_details'

    rid = db.Column(db.Integer, db.ForeignKey('roleplay_characters.rid', ondelete='CASCADE'), primary_key=True)
    bio = db.Column(db.Text, nullable=True)  # 简介
    phrases = db.Column(db.Text, nullable=True)  # 名人名言/短语，JSON 数组
    avatar_id = db.Column(db.Integer, db.ForeignKey('files.fid', ondelete='SET NULL'), nullable=True)  # 头像
    images_id = db.Column(db.Text, nullable=True)  # 图片 ID 数组，JSON 数组
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class RoleplaySession(db.Model):
    """角色对话会话（uid + rid 唯一确定一个会话）"""
    __tablename__ = 'roleplay_sessions'

    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), primary_key=True)
    rid = db.Column(db.Integer, db.ForeignKey('roleplay_characters.rid', ondelete='CASCADE'), primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.UniqueConstraint('uid', 'rid', name='uq_uid_rid'),
    )


class RoleplayMessage(db.Model):
    """角色对话消息"""
    __tablename__ = 'roleplay_messages'

    mid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.Integer, db.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False)
    rid = db.Column(db.Integer, db.ForeignKey('roleplay_characters.rid', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rm_uid_rid', 'uid', 'rid'),
    )
