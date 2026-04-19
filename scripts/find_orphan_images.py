"""
检查孤立图片（orphan images）

孤立图片定义：File 表中的记录未被以下任何字段引用：
- user_info.avatar_id
- admin_info.avatar_id
- roleplay_character_details.avatar_id
- roleplay_character_details.images_id（JSON 数组）

用法：python scripts/find_orphan_images.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import File, UserInfo, AdminInfo, RoleplayCharacterDetail
import json


def find_orphan_images():
    # 收集所有被引用的 fid
    referenced_fids = set()

    # 1. user_info.avatar_id
    for row in UserInfo.query.all():
        if row.avatar_id:
            referenced_fids.add(row.avatar_id)

    # 2. admin_info.avatar_id
    for row in AdminInfo.query.all():
        if row.avatar_id:
            referenced_fids.add(row.avatar_id)

    # 3. roleplay_character_details.avatar_id
    for row in RoleplayCharacterDetail.query.all():
        if row.avatar_id:
            referenced_fids.add(row.avatar_id)

    # 4. roleplay_character_details.images_id (JSON array)
    for row in RoleplayCharacterDetail.query.all():
        if row.images_id:
            try:
                fids = json.loads(row.images_id)
                if isinstance(fids, list):
                    for fid in fids:
                        if isinstance(fid, int):
                            referenced_fids.add(fid)
            except (json.JSONDecodeError, TypeError):
                print(f"  [警告] rid={row.rid} images_id 解析失败: {row.images_id}")

    # 查找孤立文件
    all_files = File.query.all()
    orphan_files = [f for f in all_files if f.fid not in referenced_fids]

    print(f"总文件数: {len(all_files)}")
    print(f"被引用文件数: {len(referenced_fids)}")
    print(f"孤立文件数: {len(orphan_files)}")
    print()

    if orphan_files:
        print("孤立文件列表:")
        for f in orphan_files:
            print(
                f"  fid={f.fid} | original={f.original_filename} | secure={f.secure_filename} | created={f.created_at}")
    else:
        print("未发现孤立文件")

    return orphan_files


if __name__ == '__main__':
    from app import app

    with app.app_context():
        find_orphan_images()
