"""Travel Recommendation 公共读 API（匿名）。"""
from flask import Blueprint, jsonify

from models import TravelRecommendation

travel_bp = Blueprint('travel', __name__, url_prefix='/api/travel/recommendation')


def _serialize_recommendation(rec: TravelRecommendation) -> dict:
    """把 TravelRecommendation + 7 张子表合并为前端期望的 cities.json 形态。"""
    return {
        'id': rec.id,
        'name': rec.name,
        'displayName': rec.display_name,
        'center': [float(rec.center_lon), float(rec.center_lat)],
        'players': [
            {
                'name': p.name,
                'hero': p.hero,
                'team': p.team,
                'desc': p.description,
            }
            for p in rec.players
        ],
        'heroes': [
            {
                'name': h.name,
                'role': h.role,
                'style': h.style,
                'desc': h.description,
            }
            for h in rec.heroes
        ],
        'eSportsInfo': [e.content for e in rec.esports_info],
        'food': [f.content for f in rec.foods],
        'travelTips': [t.content for t in rec.travel_tips],
        'tasks': [
            {
                'title': t.title,
                'desc': t.description,
                'reward': t.reward,
            }
            for t in rec.tasks
        ],
        'recommendedRoutes': [r.content for r in rec.routes],
    }


@travel_bp.route('', methods=['GET'])
def list_recommendations():
    """获取所有启用的旅行推荐（含子表）。"""
    recs = TravelRecommendation.query.filter_by(is_active=True).all()
    return jsonify({
        'success': True,
        'recommendations': [_serialize_recommendation(r) for r in recs]
    })


@travel_bp.route('/<int:rec_id>', methods=['GET'])
def get_recommendation(rec_id):
    """获取单条旅行推荐详情。"""
    rec = TravelRecommendation.query.filter_by(id=rec_id, is_active=True).first()
    if not rec:
        return jsonify({'success': False, 'message': 'Recommendation not found'}), 404
    return jsonify({
        'success': True,
        'recommendation': _serialize_recommendation(rec)
    })
