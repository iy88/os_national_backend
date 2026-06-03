"""
Seed travel_recommendations tables from os_national_frontend/src/data/cities.json.

灌库前请先执行 `flask init-db`（或确保 8 张 travel_recommendations* 表已建好）。
脚本是 idempotent 的：按 display_name 查重，已存在则跳过。

用法:
    python scripts/seed_travel_recommendations.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from models import (  # noqa: E402
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


CITIES_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '..', 'os_national_frontend', 'src', 'data', 'cities.json'
)


def _load_cities() -> dict:
    path = os.path.normpath(CITIES_JSON)
    if not os.path.exists(path):
        print(f'[ERROR] cities.json not found at {path}')
        print('        请确认 frontend 目录结构未变，或修改 CITIES_JSON 路径')
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _seed_one(key: str, city: dict) -> str:
    """灌一条；返回 'created' / 'skipped'。"""
    display_name = (city.get('displayName') or '').strip()
    if not display_name:
        return 'skipped (no displayName)'

    existing = TravelRecommendation.query.filter_by(display_name=display_name).first()
    if existing:
        return 'skipped (exists)'

    center = city.get('center') or [None, None]
    rec = TravelRecommendation(
        name=city.get('name') or display_name,
        display_name=display_name,
        center_lon=center[0] if len(center) > 0 else 0,
        center_lat=center[1] if len(center) > 1 else 0,
        is_active=True,
    )
    db.session.add(rec)
    db.session.flush()  # 取 rec.id

    for i, p in enumerate(city.get('players') or []):
        rec.players.append(RecommendationPlayer(
            name=p.get('name') or '',
            hero=p.get('hero'),
            team=p.get('team'),
            description=p.get('desc'),
            display_order=i,
        ))

    for i, h in enumerate(city.get('heroes') or []):
        rec.heroes.append(RecommendationHero(
            name=h.get('name') or '',
            role=h.get('role'),
            style=h.get('style'),
            description=h.get('desc'),
            display_order=i,
        ))

    for i, c in enumerate(city.get('eSportsInfo') or []):
        rec.esports_info.append(RecommendationEsportsInfo(content=str(c), display_order=i))

    for i, c in enumerate(city.get('food') or []):
        rec.foods.append(RecommendationFood(content=str(c), display_order=i))

    for i, c in enumerate(city.get('travelTips') or []):
        rec.travel_tips.append(RecommendationTravelTip(content=str(c), display_order=i))

    for i, t in enumerate(city.get('tasks') or []):
        rec.tasks.append(RecommendationTask(
            title=t.get('title') or '',
            description=t.get('desc'),
            reward=t.get('reward'),
            display_order=i,
        ))

    for i, c in enumerate(city.get('recommendedRoutes') or []):
        rec.routes.append(RecommendationRoute(content=str(c), display_order=i))

    return 'created'


def main():
    cities = _load_cities()
    print(f'Found {len(cities)} cities in cities.json\n')

    created = skipped = failed = 0
    with app.app_context():
        for key, city in cities.items():
            try:
                status = _seed_one(key, city)
                if status == 'created':
                    db.session.commit()
                    created += 1
                else:
                    db.session.rollback()  # 跳过时确保无残留
                    skipped += 1
                print(f'  [{status:20s}] {key} -> {city.get("displayName")}')
            except Exception as e:
                db.session.rollback()
                failed += 1
                print(f'  [failed               ] {key} -> {city.get("displayName")}: {e}')

    print(f'\nDone. created={created}, skipped={skipped}, failed={failed}')


if __name__ == '__main__':
    main()
