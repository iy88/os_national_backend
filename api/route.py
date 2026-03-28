from flask import Blueprint, request, jsonify

from models import db, Route, Message, ConversationSession
from utils.jwt_utils import token_required

route_bp = Blueprint('route', __name__, url_prefix='/route')


@route_bp.route('/list', methods=['GET'])
@token_required
def list_favorites(current_user_id):
    """获取用户所有收藏路线"""
    routes = Route.query.filter_by(uid=current_user_id).order_by(Route.created_at.desc()).all()

    result = [{
        'rid': route.rid,
        'mid': route.mid,
        'title': route.title,
        'createdAt': route.created_at.isoformat() + 'Z',
        'updatedAt': route.updated_at.isoformat() + 'Z' if route.updated_at else None
    } for route in routes]

    return jsonify({
        'success': True,
        'routes': result
    })


@route_bp.route('/detail/<int:rid>', methods=['GET'])
@token_required
def get_favorite_detail(current_user_id, rid):
    """获取收藏路线详情"""
    route = Route.query.filter_by(rid=rid, uid=current_user_id).first()
    if not route:
        return jsonify({'success': False, 'message': 'Route not found'}), 404

    return jsonify({
        'success': True,
        'route': {
            'rid': route.rid,
            'mid': route.mid,
            'title': route.title,
            'content': route.content,
            'createdAt': route.created_at.isoformat() + 'Z',
            'updatedAt': route.updated_at.isoformat() + 'Z' if route.updated_at else None
        }
    })


@route_bp.route('/favorite', methods=['POST'])
@token_required
def add_favorite(current_user_id):
    """
    收藏路线（只提供 mid，后端自动复制 session.title 和 message.content）

    请求体:
        mid: int - 消息 ID（必须是 assistant role 的消息）
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    mid = data.get('mid')
    if not mid:
        return jsonify({'success': False, 'message': 'mid is required'}), 400

    # 查找消息，必须是 assistant role
    message = Message.query.get(mid)
    if not message:
        return jsonify({'success': False, 'message': 'Message not found'}), 404

    if message.role != 'assistant':
        return jsonify({'success': False, 'message': 'Can only favorite assistant messages'}), 400

    # 验证消息所属会话的用户
    session = ConversationSession.query.get(message.sid)
    if not session or session.uid != current_user_id:
        return jsonify({'success': False, 'message': 'Message not found'}), 404

    # 检查是否已收藏
    existing = Route.query.filter_by(uid=current_user_id, mid=mid).first()
    if existing:
        return jsonify({'success': False, 'message': 'Already favorited'}), 409

    # 创建收藏（自动复制 title 和 content）
    route = Route(
        uid=current_user_id,
        mid=mid,
        title=session.title,
        content=message.content
    )
    db.session.add(route)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Route favorited'
    }), 201


@route_bp.route('/edit/<int:rid>', methods=['PUT'])
@token_required
def edit_favorite(current_user_id, rid):
    """
    编辑收藏路线（更新 title 和/或 content）

    请求体:
        title: string (可选)
        content: string (可选)
    """
    route = Route.query.filter_by(rid=rid, uid=current_user_id).first()
    if not route:
        return jsonify({'success': False, 'message': 'Route not found'}), 404

    data = request.get_json() or {}
    title = data.get('title')
    content = data.get('content')

    if not title and not content:
        return jsonify({'success': False, 'message': 'title or content is required'}), 400

    if title is not None:
        route.title = title
    if content is not None:
        route.content = content

    from datetime import datetime, timezone
    route.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.session.commit()

    return jsonify({
        'success': True,
        'route': {
            'rid': route.rid,
            'mid': route.mid,
            'title': route.title,
            'content': route.content,
            'createdAt': route.created_at.isoformat() + 'Z',
            'updatedAt': route.updated_at.isoformat() + 'Z' if route.updated_at else None
        }
    })


@route_bp.route('/delete/<int:rid>', methods=['DELETE'])
@token_required
def delete_favorite(current_user_id, rid):
    """删除收藏"""
    route = Route.query.filter_by(rid=rid, uid=current_user_id).first()
    if not route:
        return jsonify({'success': False, 'message': 'Route not found'}), 404

    db.session.delete(route)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Route deleted'
    })
