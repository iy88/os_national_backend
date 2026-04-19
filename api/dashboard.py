from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import func, text

from models import db, User, File, ConversationSession, Message, Route, RoleplayCharacter, RoleplayMessage
from utils.jwt_utils import token_required

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/admin/dashboard')


@dashboard_bp.route('', methods=['GET'])
@token_required(require_admin=True)
def get_dashboard(_):
    """后台主页统计数据概览"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Users
    total_users = db.session.query(func.count(User.uid)).scalar()
    today_new_users = db.session.query(func.count(User.uid)).filter(User.created_at >= today_start).scalar()

    # Characters
    total_chars = db.session.query(func.count(RoleplayCharacter.rid)).scalar()
    type_rows = db.session.query(RoleplayCharacter.type, func.count()).group_by(RoleplayCharacter.type).all()
    by_type = {row[0]: row[1] for row in type_rows}

    # Sessions - RoleplaySession 复合主键需用 text() 直接 COUNT(*)
    total_rp_sessions = db.session.execute(text("SELECT COUNT(*) FROM roleplay_sessions")).scalar()
    total_travel_sessions = db.session.query(func.count(ConversationSession.sid)).scalar()

    # Messages
    total_messages = db.session.query(func.count(Message.mid)).scalar()
    total_rp_messages = db.session.query(func.count(RoleplayMessage.mid)).scalar()

    # Routes & Files
    total_routes = db.session.query(func.count(Route.rid)).scalar()
    total_files = db.session.query(func.count(File.fid)).scalar()

    return jsonify({
        "success": True,
        "users": {"total": total_users, "today_new": today_new_users},
        "characters": {"total": total_chars, "by_type": by_type},
        "sessions": {
            "total": total_travel_sessions + total_rp_sessions,
            "travel": total_travel_sessions,
            "roleplay": total_rp_sessions
        },
        "messages": {
            "total": total_messages + total_rp_messages,
            "travel": total_messages,
            "roleplay": total_rp_messages
        },
        "routes": {"total": total_routes},
        "files": {"total": total_files}
    })
