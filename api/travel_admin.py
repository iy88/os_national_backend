"""Travel Recommendation Admin CRUD API."""
from flask import Blueprint, request, jsonify
from sqlalchemy import or_

from models import (
    db,
    TravelRecommendation,
    RecommendationPlayer,
    RecommendationHero,
    RecommendationEsportsInfo,
    RecommendationFood,
    RecommendationTravelTip,
    RecommendationTask,
    RecommendationRoute,
)
from utils.jwt_utils import token_required

travel_admin_bp = Blueprint('travel_admin', __name__, url_prefix='/api/admin/travel/recommendation')


# ============ 序列化（snake_case，给 admin panel 用）============
# 时间戳字段遵循 roleplay_admin 的 camelCase 习惯（createdAt / updatedAt），
# ISO8601 + 'Z' 后缀表示 UTC。

def _ts(dt) -> str | None:
    return dt.isoformat() + 'Z' if dt else None


def _serialize_player(p: RecommendationPlayer) -> dict:
    return {
        'id': p.id,
        'recommendation_id': p.recommendation_id,
        'name': p.name,
        'hero': p.hero,
        'team': p.team,
        'description': p.description,
        'display_order': p.display_order,
        'createdAt': _ts(p.created_at),
        'updatedAt': _ts(p.updated_at),
    }


def _serialize_hero(h: RecommendationHero) -> dict:
    return {
        'id': h.id,
        'recommendation_id': h.recommendation_id,
        'name': h.name,
        'role': h.role,
        'style': h.style,
        'description': h.description,
        'display_order': h.display_order,
        'createdAt': _ts(h.created_at),
        'updatedAt': _ts(h.updated_at),
    }


def _serialize_esports(e: RecommendationEsportsInfo) -> dict:
    return {
        'id': e.id, 'recommendation_id': e.recommendation_id,
        'content': e.content, 'display_order': e.display_order,
        'createdAt': _ts(e.created_at),
        'updatedAt': _ts(e.updated_at),
    }


def _serialize_food(f: RecommendationFood) -> dict:
    return {
        'id': f.id, 'recommendation_id': f.recommendation_id,
        'content': f.content, 'display_order': f.display_order,
        'createdAt': _ts(f.created_at),
        'updatedAt': _ts(f.updated_at),
    }


def _serialize_tip(t: RecommendationTravelTip) -> dict:
    return {
        'id': t.id, 'recommendation_id': t.recommendation_id,
        'content': t.content, 'display_order': t.display_order,
        'createdAt': _ts(t.created_at),
        'updatedAt': _ts(t.updated_at),
    }


def _serialize_task(t: RecommendationTask) -> dict:
    return {
        'id': t.id, 'recommendation_id': t.recommendation_id,
        'title': t.title, 'description': t.description, 'reward': t.reward,
        'display_order': t.display_order,
        'createdAt': _ts(t.created_at),
        'updatedAt': _ts(t.updated_at),
    }


def _serialize_route(r: RecommendationRoute) -> dict:
    return {
        'id': r.id, 'recommendation_id': r.recommendation_id,
        'content': r.content, 'display_order': r.display_order,
        'createdAt': _ts(r.created_at),
        'updatedAt': _ts(r.updated_at),
    }


def _serialize_recommendation_full(rec: TravelRecommendation) -> dict:
    return {
        'id': rec.id,
        'name': rec.name,
        'display_name': rec.display_name,
        'center_lon': float(rec.center_lon),
        'center_lat': float(rec.center_lat),
        'is_active': rec.is_active,
        'players': [_serialize_player(p) for p in rec.players],
        'heroes': [_serialize_hero(h) for h in rec.heroes],
        'esports_info': [_serialize_esports(e) for e in rec.esports_info],
        'foods': [_serialize_food(f) for f in rec.foods],
        'travel_tips': [_serialize_tip(t) for t in rec.travel_tips],
        'tasks': [_serialize_task(t) for t in rec.tasks],
        'routes': [_serialize_route(r) for r in rec.routes],
        'createdAt': _ts(rec.created_at),
        'updatedAt': _ts(rec.updated_at),
    }


# ============ 主表 CRUD ============

@travel_admin_bp.route('', methods=['GET'])
@token_required(require_admin=True)
def list_recommendations(_):
    """分页列表 + 模糊搜索 name/display_name。"""
    page = max(1, int(request.args.get('page', 1)))
    page_size = min(50, max(1, int(request.args.get('page_size', 10))))
    search = (request.args.get('search') or '').strip()

    query = TravelRecommendation.query
    if search:
        like = f'%{search}%'
        query = query.filter(or_(
            TravelRecommendation.name.like(like),
            TravelRecommendation.display_name.like(like),
        ))

    total = query.count()
    recs = query.order_by(TravelRecommendation.id.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()

    return jsonify({
        'success': True,
        'recommendations': [_serialize_recommendation_full(r) for r in recs],
        'total': total, 'page': page, 'page_size': page_size,
    })


@travel_admin_bp.route('/<int:rec_id>', methods=['GET'])
@token_required(require_admin=True)
def get_recommendation(_, rec_id):
    """获取单条详情（含全部子表）。"""
    rec = TravelRecommendation.query.get(rec_id)
    if not rec:
        return jsonify({'success': False, 'message': 'Recommendation not found'}), 404
    return jsonify({
        'success': True,
        'recommendation': _serialize_recommendation_full(rec)
    })


@travel_admin_bp.route('', methods=['POST'])
@token_required(require_admin=True)
def create_recommendation(_):
    """
    创建一条推荐（body 含全部子表数组）。
    必填: name, display_name, center_lon, center_lat
    """
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    display_name = (data.get('display_name') or '').strip()
    center_lon = data.get('center_lon')
    center_lat = data.get('center_lat')

    if not name or not display_name or center_lon is None or center_lat is None:
        return jsonify({'success': False,
                        'message': 'name, display_name, center_lon, center_lat are required'}), 400

    if TravelRecommendation.query.filter_by(display_name=display_name).first():
        return jsonify({'success': False,
                        'message': f'display_name "{display_name}" already exists'}), 409

    rec = TravelRecommendation(
        name=name,
        display_name=display_name,
        center_lon=center_lon,
        center_lat=center_lat,
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(rec)
    db.session.flush()  # 取 rec.id

    _bulk_create_children(rec, data)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Created',
        'recommendation': _serialize_recommendation_full(rec)
    }), 201


@travel_admin_bp.route('/<int:rec_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_recommendation(_, rec_id):
    """
    整条替换：body 字段缺失则不更新；子表数组缺失则保留现有，传入空数组则清空。
    """
    rec = TravelRecommendation.query.get(rec_id)
    if not rec:
        return jsonify({'success': False, 'message': 'Recommendation not found'}), 404

    data = request.get_json() or {}

    if 'name' in data:
        rec.name = (data.get('name') or '').strip() or rec.name
    if 'display_name' in data:
        new_dn = (data.get('display_name') or '').strip()
        if new_dn and new_dn != rec.display_name:
            if TravelRecommendation.query.filter(
                TravelRecommendation.id != rec_id,
                TravelRecommendation.display_name == new_dn
            ).first():
                return jsonify({'success': False,
                                'message': f'display_name "{new_dn}" already exists'}), 409
            rec.display_name = new_dn
    if 'center_lon' in data:
        rec.center_lon = data['center_lon']
    if 'center_lat' in data:
        rec.center_lat = data['center_lat']
    if 'is_active' in data:
        rec.is_active = bool(data['is_active'])

    _replace_children(rec, data)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Updated',
        'recommendation': _serialize_recommendation_full(rec)
    })


@travel_admin_bp.route('/<int:rec_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_recommendation(_, rec_id):
    """删除主表，FK CASCADE 自动清空子表。"""
    rec = TravelRecommendation.query.get(rec_id)
    if not rec:
        return jsonify({'success': False, 'message': 'Recommendation not found'}), 404
    db.session.delete(rec)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200


# ============ 子表批量替换辅助（主表 create/update 共用）============

def _bulk_create_children(rec: TravelRecommendation, data: dict):
    for i, p in enumerate(data.get('players') or []):
        rec.players.append(RecommendationPlayer(
            name=p.get('name') or '',
            hero=p.get('hero'),
            team=p.get('team'),
            description=p.get('description'),
            display_order=p.get('display_order', i),
        ))
    for i, h in enumerate(data.get('heroes') or []):
        rec.heroes.append(RecommendationHero(
            name=h.get('name') or '',
            role=h.get('role'),
            style=h.get('style'),
            description=h.get('description'),
            display_order=h.get('display_order', i),
        ))
    for i, e in enumerate(data.get('esports_info') or []):
        rec.esports_info.append(RecommendationEsportsInfo(
            content=str(e), display_order=i,
        ))
    for i, f in enumerate(data.get('foods') or []):
        rec.foods.append(RecommendationFood(
            content=str(f), display_order=i,
        ))
    for i, t in enumerate(data.get('travel_tips') or []):
        rec.travel_tips.append(RecommendationTravelTip(
            content=str(t), display_order=i,
        ))
    for i, t in enumerate(data.get('tasks') or []):
        rec.tasks.append(RecommendationTask(
            title=t.get('title') or '',
            description=t.get('description'),
            reward=t.get('reward'),
            display_order=t.get('display_order', i),
        ))
    for i, r in enumerate(data.get('routes') or []):
        rec.routes.append(RecommendationRoute(
            content=str(r), display_order=i,
        ))


def _replace_children(rec: TravelRecommendation, data: dict):
    """仅当 data 中明确包含某子表 key 时才替换。"""
    if 'players' in data:
        RecommendationPlayer.query.filter_by(recommendation_id=rec.id).delete()
        db.session.flush()
        for i, p in enumerate(data.get('players') or []):
            rec.players.append(RecommendationPlayer(
                name=p.get('name') or '',
                hero=p.get('hero'),
                team=p.get('team'),
                description=p.get('description'),
                display_order=p.get('display_order', i),
            ))
    if 'heroes' in data:
        RecommendationHero.query.filter_by(recommendation_id=rec.id).delete()
        db.session.flush()
        for i, h in enumerate(data.get('heroes') or []):
            rec.heroes.append(RecommendationHero(
                name=h.get('name') or '',
                role=h.get('role'),
                style=h.get('style'),
                description=h.get('description'),
                display_order=h.get('display_order', i),
            ))
    if 'esports_info' in data:
        RecommendationEsportsInfo.query.filter_by(recommendation_id=rec.id).delete()
        db.session.flush()
        for i, e in enumerate(data.get('esports_info') or []):
            rec.esports_info.append(RecommendationEsportsInfo(
                content=str(e), display_order=i,
            ))
    if 'foods' in data:
        RecommendationFood.query.filter_by(recommendation_id=rec.id).delete()
        db.session.flush()
        for i, f in enumerate(data.get('foods') or []):
            rec.foods.append(RecommendationFood(
                content=str(f), display_order=i,
            ))
    if 'travel_tips' in data:
        RecommendationTravelTip.query.filter_by(recommendation_id=rec.id).delete()
        db.session.flush()
        for i, t in enumerate(data.get('travel_tips') or []):
            rec.travel_tips.append(RecommendationTravelTip(
                content=str(t), display_order=i,
            ))
    if 'tasks' in data:
        RecommendationTask.query.filter_by(recommendation_id=rec.id).delete()
        db.session.flush()
        for i, t in enumerate(data.get('tasks') or []):
            rec.tasks.append(RecommendationTask(
                title=t.get('title') or '',
                description=t.get('description'),
                reward=t.get('reward'),
                display_order=t.get('display_order', i),
            ))
    if 'routes' in data:
        RecommendationRoute.query.filter_by(recommendation_id=rec.id).delete()
        db.session.flush()
        for i, r in enumerate(data.get('routes') or []):
            rec.routes.append(RecommendationRoute(
                content=str(r), display_order=i,
            ))


# ============ 子表 CRUD：通用辅助 ============

def _get_rec_or_404(rec_id):
    rec = TravelRecommendation.query.get(rec_id)
    if not rec:
        return None, (jsonify({'success': False, 'message': 'Recommendation not found'}), 404)
    return rec, None


def _next_order(model, rec_id) -> int:
    last = model.query.filter_by(recommendation_id=rec_id) \
        .order_by(model.display_order.desc()).first()
    return (last.display_order + 1) if last else 0


# ============ Players 子表 ============

@travel_admin_bp.route('/<int:rec_id>/players', methods=['GET'])
@token_required(require_admin=True)
def list_players(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    items = RecommendationPlayer.query.filter_by(recommendation_id=rec_id) \
        .order_by(RecommendationPlayer.display_order).all()
    return jsonify({'success': True, 'players': [_serialize_player(p) for p in items]})


@travel_admin_bp.route('/<int:rec_id>/players', methods=['POST'])
@token_required(require_admin=True)
def create_player(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    data = request.get_json() or {}
    if not (data.get('name') or '').strip():
        return jsonify({'success': False, 'message': 'name is required'}), 400
    item = RecommendationPlayer(
        recommendation_id=rec_id,
        name=data['name'],
        hero=data.get('hero'),
        team=data.get('team'),
        description=data.get('description'),
        display_order=data.get('display_order', _next_order(RecommendationPlayer, rec_id)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'player': _serialize_player(item)}), 201


@travel_admin_bp.route('/<int:rec_id>/players/<int:item_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_player(_, rec_id, item_id):
    item = RecommendationPlayer.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Player not found'}), 404
    data = request.get_json() or {}
    for field in ('name', 'hero', 'team', 'description', 'display_order'):
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return jsonify({'success': True, 'player': _serialize_player(item)})


@travel_admin_bp.route('/<int:rec_id>/players/<int:item_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_player(_, rec_id, item_id):
    item = RecommendationPlayer.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Player not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200


# ============ Heroes 子表 ============

@travel_admin_bp.route('/<int:rec_id>/heroes', methods=['GET'])
@token_required(require_admin=True)
def list_heroes(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    items = RecommendationHero.query.filter_by(recommendation_id=rec_id) \
        .order_by(RecommendationHero.display_order).all()
    return jsonify({'success': True, 'heroes': [_serialize_hero(h) for h in items]})


@travel_admin_bp.route('/<int:rec_id>/heroes', methods=['POST'])
@token_required(require_admin=True)
def create_hero(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    data = request.get_json() or {}
    if not (data.get('name') or '').strip():
        return jsonify({'success': False, 'message': 'name is required'}), 400
    item = RecommendationHero(
        recommendation_id=rec_id,
        name=data['name'],
        role=data.get('role'),
        style=data.get('style'),
        description=data.get('description'),
        display_order=data.get('display_order', _next_order(RecommendationHero, rec_id)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'hero': _serialize_hero(item)}), 201


@travel_admin_bp.route('/<int:rec_id>/heroes/<int:item_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_hero(_, rec_id, item_id):
    item = RecommendationHero.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Hero not found'}), 404
    data = request.get_json() or {}
    for field in ('name', 'role', 'style', 'description', 'display_order'):
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return jsonify({'success': True, 'hero': _serialize_hero(item)})


@travel_admin_bp.route('/<int:rec_id>/heroes/<int:item_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_hero(_, rec_id, item_id):
    item = RecommendationHero.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Hero not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200


# ============ Esports Info 子表 ============

@travel_admin_bp.route('/<int:rec_id>/esports_info', methods=['GET'])
@token_required(require_admin=True)
def list_esports_info(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    items = RecommendationEsportsInfo.query.filter_by(recommendation_id=rec_id) \
        .order_by(RecommendationEsportsInfo.display_order).all()
    return jsonify({'success': True, 'esports_info': [_serialize_esports(e) for e in items]})


@travel_admin_bp.route('/<int:rec_id>/esports_info', methods=['POST'])
@token_required(require_admin=True)
def create_esports_info(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'content is required'}), 400
    item = RecommendationEsportsInfo(
        recommendation_id=rec_id,
        content=content,
        display_order=data.get('display_order', _next_order(RecommendationEsportsInfo, rec_id)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'esports_info': _serialize_esports(item)}), 201


@travel_admin_bp.route('/<int:rec_id>/esports_info/<int:item_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_esports_info(_, rec_id, item_id):
    item = RecommendationEsportsInfo.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'EsportsInfo not found'}), 404
    data = request.get_json() or {}
    if 'content' in data:
        item.content = (data['content'] or '').strip() or item.content
    if 'display_order' in data:
        item.display_order = data['display_order']
    db.session.commit()
    return jsonify({'success': True, 'esports_info': _serialize_esports(item)})


@travel_admin_bp.route('/<int:rec_id>/esports_info/<int:item_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_esports_info(_, rec_id, item_id):
    item = RecommendationEsportsInfo.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'EsportsInfo not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200


# ============ Foods 子表 ============

@travel_admin_bp.route('/<int:rec_id>/foods', methods=['GET'])
@token_required(require_admin=True)
def list_foods(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    items = RecommendationFood.query.filter_by(recommendation_id=rec_id) \
        .order_by(RecommendationFood.display_order).all()
    return jsonify({'success': True, 'foods': [_serialize_food(f) for f in items]})


@travel_admin_bp.route('/<int:rec_id>/foods', methods=['POST'])
@token_required(require_admin=True)
def create_food(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'content is required'}), 400
    item = RecommendationFood(
        recommendation_id=rec_id,
        content=content,
        display_order=data.get('display_order', _next_order(RecommendationFood, rec_id)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'food': _serialize_food(item)}), 201


@travel_admin_bp.route('/<int:rec_id>/foods/<int:item_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_food(_, rec_id, item_id):
    item = RecommendationFood.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Food not found'}), 404
    data = request.get_json() or {}
    if 'content' in data:
        item.content = (data['content'] or '').strip() or item.content
    if 'display_order' in data:
        item.display_order = data['display_order']
    db.session.commit()
    return jsonify({'success': True, 'food': _serialize_food(item)})


@travel_admin_bp.route('/<int:rec_id>/foods/<int:item_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_food(_, rec_id, item_id):
    item = RecommendationFood.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Food not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200


# ============ Travel Tips 子表 ============

@travel_admin_bp.route('/<int:rec_id>/travel_tips', methods=['GET'])
@token_required(require_admin=True)
def list_travel_tips(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    items = RecommendationTravelTip.query.filter_by(recommendation_id=rec_id) \
        .order_by(RecommendationTravelTip.display_order).all()
    return jsonify({'success': True, 'travel_tips': [_serialize_tip(t) for t in items]})


@travel_admin_bp.route('/<int:rec_id>/travel_tips', methods=['POST'])
@token_required(require_admin=True)
def create_travel_tip(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'content is required'}), 400
    item = RecommendationTravelTip(
        recommendation_id=rec_id,
        content=content,
        display_order=data.get('display_order', _next_order(RecommendationTravelTip, rec_id)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'travel_tip': _serialize_tip(item)}), 201


@travel_admin_bp.route('/<int:rec_id>/travel_tips/<int:item_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_travel_tip(_, rec_id, item_id):
    item = RecommendationTravelTip.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'TravelTip not found'}), 404
    data = request.get_json() or {}
    if 'content' in data:
        item.content = (data['content'] or '').strip() or item.content
    if 'display_order' in data:
        item.display_order = data['display_order']
    db.session.commit()
    return jsonify({'success': True, 'travel_tip': _serialize_tip(item)})


@travel_admin_bp.route('/<int:rec_id>/travel_tips/<int:item_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_travel_tip(_, rec_id, item_id):
    item = RecommendationTravelTip.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'TravelTip not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200


# ============ Tasks 子表 ============

@travel_admin_bp.route('/<int:rec_id>/tasks', methods=['GET'])
@token_required(require_admin=True)
def list_tasks(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    items = RecommendationTask.query.filter_by(recommendation_id=rec_id) \
        .order_by(RecommendationTask.display_order).all()
    return jsonify({'success': True, 'tasks': [_serialize_task(t) for t in items]})


@travel_admin_bp.route('/<int:rec_id>/tasks', methods=['POST'])
@token_required(require_admin=True)
def create_task(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    data = request.get_json() or {}
    if not (data.get('title') or '').strip():
        return jsonify({'success': False, 'message': 'title is required'}), 400
    item = RecommendationTask(
        recommendation_id=rec_id,
        title=data['title'],
        description=data.get('description'),
        reward=data.get('reward'),
        display_order=data.get('display_order', _next_order(RecommendationTask, rec_id)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'task': _serialize_task(item)}), 201


@travel_admin_bp.route('/<int:rec_id>/tasks/<int:item_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_task(_, rec_id, item_id):
    item = RecommendationTask.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    data = request.get_json() or {}
    for field in ('title', 'description', 'reward', 'display_order'):
        if field in data:
            setattr(item, field, data[field])
    db.session.commit()
    return jsonify({'success': True, 'task': _serialize_task(item)})


@travel_admin_bp.route('/<int:rec_id>/tasks/<int:item_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_task(_, rec_id, item_id):
    item = RecommendationTask.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200


# ============ Routes 子表 ============

@travel_admin_bp.route('/<int:rec_id>/routes', methods=['GET'])
@token_required(require_admin=True)
def list_routes(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    items = RecommendationRoute.query.filter_by(recommendation_id=rec_id) \
        .order_by(RecommendationRoute.display_order).all()
    return jsonify({'success': True, 'routes': [_serialize_route(r) for r in items]})


@travel_admin_bp.route('/<int:rec_id>/routes', methods=['POST'])
@token_required(require_admin=True)
def create_route(_, rec_id):
    rec, err = _get_rec_or_404(rec_id)
    if err:
        return err
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'content is required'}), 400
    item = RecommendationRoute(
        recommendation_id=rec_id,
        content=content,
        display_order=data.get('display_order', _next_order(RecommendationRoute, rec_id)),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'route': _serialize_route(item)}), 201


@travel_admin_bp.route('/<int:rec_id>/routes/<int:item_id>', methods=['PUT'])
@token_required(require_admin=True)
def update_route(_, rec_id, item_id):
    item = RecommendationRoute.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Route not found'}), 404
    data = request.get_json() or {}
    if 'content' in data:
        item.content = (data['content'] or '').strip() or item.content
    if 'display_order' in data:
        item.display_order = data['display_order']
    db.session.commit()
    return jsonify({'success': True, 'route': _serialize_route(item)})


@travel_admin_bp.route('/<int:rec_id>/routes/<int:item_id>', methods=['DELETE'])
@token_required(require_admin=True)
def delete_route(_, rec_id, item_id):
    item = RecommendationRoute.query.filter_by(id=item_id, recommendation_id=rec_id).first()
    if not item:
        return jsonify({'success': False, 'message': 'Route not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Deleted'}), 200
