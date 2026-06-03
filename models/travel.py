from datetime import datetime, timezone

from models import db


class TravelRecommendation(db.Model):
    """旅行推荐地点（首页 SVG 地图上的一个点 + 详情）"""
    __tablename__ = 'travel_recommendations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)  # 完整名，如 "西安 · 长安荣耀之旅"
    display_name = db.Column(db.String(80), nullable=False)  # 短名，如 "西安"
    center_lon = db.Column(db.Numeric(10, 6), nullable=False)  # 经度
    center_lat = db.Column(db.Numeric(10, 6), nullable=False)  # 纬度
    is_active = db.Column(db.Boolean, nullable=False, default=True)  # 软删除/隐藏
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.UniqueConstraint('display_name', name='uq_travel_display_name'),
        db.Index('idx_travel_is_active', 'is_active'),
    )

    players = db.relationship('RecommendationPlayer', backref='recommendation',
                              cascade='all, delete-orphan',
                              order_by='RecommendationPlayer.display_order',
                              passive_deletes=True)
    heroes = db.relationship('RecommendationHero', backref='recommendation',
                             cascade='all, delete-orphan',
                             order_by='RecommendationHero.display_order',
                             passive_deletes=True)
    esports_info = db.relationship('RecommendationEsportsInfo', backref='recommendation',
                                   cascade='all, delete-orphan',
                                   order_by='RecommendationEsportsInfo.display_order',
                                   passive_deletes=True)
    foods = db.relationship('RecommendationFood', backref='recommendation',
                            cascade='all, delete-orphan',
                            order_by='RecommendationFood.display_order',
                            passive_deletes=True)
    travel_tips = db.relationship('RecommendationTravelTip', backref='recommendation',
                                 cascade='all, delete-orphan',
                                 order_by='RecommendationTravelTip.display_order',
                                 passive_deletes=True)
    tasks = db.relationship('RecommendationTask', backref='recommendation',
                            cascade='all, delete-orphan',
                            order_by='RecommendationTask.display_order',
                            passive_deletes=True)
    routes = db.relationship('RecommendationRoute', backref='recommendation',
                             cascade='all, delete-orphan',
                             order_by='RecommendationRoute.display_order',
                             passive_deletes=True)


class RecommendationPlayer(db.Model):
    """电竞选手（属于某个旅行推荐）"""
    __tablename__ = 'recommendation_players'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey('travel_recommendations.id', ondelete='CASCADE'),
        nullable=False
    )
    name = db.Column(db.String(120), nullable=False)
    hero = db.Column(db.String(80), nullable=True)
    team = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rp_recommendation', 'recommendation_id', 'display_order'),
    )


class RecommendationHero(db.Model):
    """王者荣耀英雄（属于某个旅行推荐）"""
    __tablename__ = 'recommendation_heroes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey('travel_recommendations.id', ondelete='CASCADE'),
        nullable=False
    )
    name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(40), nullable=True)
    style = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rh_recommendation', 'recommendation_id', 'display_order'),
    )


class RecommendationEsportsInfo(db.Model):
    """电竞资讯 bullet 列表"""
    __tablename__ = 'recommendation_esports_info'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey('travel_recommendations.id', ondelete='CASCADE'),
        nullable=False
    )
    content = db.Column(db.String(500), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rei_recommendation', 'recommendation_id', 'display_order'),
    )


class RecommendationFood(db.Model):
    """美食 bullet 列表"""
    __tablename__ = 'recommendation_foods'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey('travel_recommendations.id', ondelete='CASCADE'),
        nullable=False
    )
    content = db.Column(db.String(500), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rf_recommendation', 'recommendation_id', 'display_order'),
    )


class RecommendationTravelTip(db.Model):
    """旅行贴士 bullet 列表"""
    __tablename__ = 'recommendation_travel_tips'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey('travel_recommendations.id', ondelete='CASCADE'),
        nullable=False
    )
    content = db.Column(db.String(500), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rtt_recommendation', 'recommendation_id', 'display_order'),
    )


class RecommendationTask(db.Model):
    """打卡任务列表（含 title/desc/reward）"""
    __tablename__ = 'recommendation_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey('travel_recommendations.id', ondelete='CASCADE'),
        nullable=False
    )
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    reward = db.Column(db.String(120), nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rt_recommendation', 'recommendation_id', 'display_order'),
    )


class RecommendationRoute(db.Model):
    """推荐路线 bullet 列表"""
    __tablename__ = 'recommendation_routes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recommendation_id = db.Column(
        db.Integer,
        db.ForeignKey('travel_recommendations.id', ondelete='CASCADE'),
        nullable=False
    )
    content = db.Column(db.String(500), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
                           onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        db.Index('idx_rr_recommendation', 'recommendation_id', 'display_order'),
    )
