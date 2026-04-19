import json
import os

from flask import Blueprint, request, jsonify

from config import Config
from models import db, File, RoleplayCharacter, RoleplayCharacterDetail, RoleplaySession
from utils.file_utils import (
    allowed_avatar_file,
    save_avatar_file,
    get_avatar_file_path,
    get_file_mime,
    generate_file_token, decode_file_token
)
from utils.jwt_utils import token_required

roleplay_admin_bp = Blueprint('roleplay_admin', __name__, url_prefix='/admin/roleplay')


def _delete_file(fid: int):
    """删除文件物理文件和数据库记录"""
    file_record = File.query.get(fid)
    if file_record:
        file_path = get_avatar_file_path(file_record.secure_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(file_record)
        return True
    return False


def _parse_images_id(images_id_str: str | None) -> list:
    """解析 images_id JSON 字符串为列表"""
    if not images_id_str:
        return []
    try:
        return json.loads(images_id_str)
    except (json.JSONDecodeError, TypeError):
        return []


def _serialize_images_id(images_id_list: list) -> str:
    """序列化 images_id 列表为 JSON 字符串"""
    return json.dumps(images_id_list) if images_id_list else None


@roleplay_admin_bp.route('/create', methods=['POST'])
@token_required(require_admin=True)
def create_character(_):
    """创建角色，支持同时上传头像和图片（可选）"""
    # 支持 multipart/form-data 和 JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        char_type = request.form.get('type')
        name = request.form.get('name')
        bio = request.form.get('bio')
        phrases_str = request.form.get('phrases')
        phrases = json.loads(phrases_str) if phrases_str else []
        avatar_file = request.files.get('avatar')
        images_files = request.files.getlist('images')
    else:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Invalid JSON'}), 400
        char_type = data.get('type')
        name = data.get('name')
        bio = data.get('bio')
        phrases = data.get('phrases', [])
        avatar_file = None
        images_files = []

    if not char_type or not name:
        return jsonify({'success': False, 'message': 'type and name are required'}), 400

    if char_type not in Config.ROLEPLAY_APP_ID_MAP:
        return jsonify({'success': False, 'message': 'Invalid character type'}), 400

    # 创建角色
    character = RoleplayCharacter(type=char_type, name=name)
    db.session.add(character)
    db.session.flush()

    # 创建详情
    detail = RoleplayCharacterDetail(rid=character.rid)
    detail.bio = bio
    detail.phrases = json.dumps(phrases) if phrases else None
    db.session.add(detail)
    db.session.flush()

    # 处理头像上传
    if avatar_file and avatar_file.filename:
        if allowed_avatar_file(avatar_file.filename):
            avatar_file.seek(0, os.SEEK_END)
            avatar_size = avatar_file.tell()
            avatar_file.seek(0)
            if avatar_size <= Config.MAX_AVATAR_SIZE:
                secure_filename = save_avatar_file(avatar_file)
                new_file = File(original_filename=avatar_file.filename, secure_filename=secure_filename)
                db.session.add(new_file)
                db.session.flush()
                detail.avatar_id = new_file.fid

    # 处理图片上传
    if images_files:
        new_fids = []
        for file in images_files:
            if file.filename and allowed_avatar_file(file.filename):
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                if file_size <= Config.MAX_AVATAR_SIZE:
                    secure_filename = save_avatar_file(file)
                    new_file = File(original_filename=file.filename, secure_filename=secure_filename)
                    db.session.add(new_file)
                    db.session.flush()
                    new_fids.append(new_file.fid)
        if new_fids:
            detail.images_id = _serialize_images_id(new_fids)

    db.session.commit()

    detail = character.detail
    images_id_list = _parse_images_id(detail.images_id) if detail else []

    return jsonify({
        'success': True,
        'message': 'Character created',
        'character': {
            'rid': character.rid,
            'type': character.type,
            'name': character.name,
            'bio': detail.bio if detail else None,
            'phrases': json.loads(detail.phrases) if detail and detail.phrases else [],
            'avatar_token': generate_file_token(detail.avatar_id) if detail and detail.avatar_id else None,
            'images_token': [generate_file_token(fid) for fid in images_id_list],
            'created_at': character.created_at.isoformat() + 'Z' if character.created_at else None
        }
    }), 201


@roleplay_admin_bp.route('/<int:rid>/detail', methods=['GET'])
@token_required(require_admin=True)
def get_character_detail(_, rid):
    """获取角色详情"""
    character = RoleplayCharacter.query.get(rid)
    if not character:
        return jsonify({'success': False, 'message': 'Character not found'}), 404

    detail = character.detail
    images_id_list = _parse_images_id(detail.images_id) if detail else []

    return jsonify({
        'success': True,
        'character': {
            'rid': character.rid,
            'type': character.type,
            'name': character.name,
            'bio': detail.bio if detail else None,
            'phrases': json.loads(detail.phrases) if detail and detail.phrases else [],
            'avatar_token': generate_file_token(detail.avatar_id) if detail and detail.avatar_id else None,
            'images_token': [generate_file_token(fid) for fid in images_id_list],
            'created_at': character.created_at.isoformat() + 'Z' if character.created_at else None,
            'updated_at': detail.updated_at.isoformat() + 'Z' if detail and detail.updated_at else None
        }
    })


@roleplay_admin_bp.route('/<int:rid>/update', methods=['PUT'])
@token_required(require_admin=True)
def update_character(_, rid):
    """更新角色，支持 multipart/form-data（上传头像/图片）或 JSON"""
    character = RoleplayCharacter.query.get(rid)
    if not character:
        return jsonify({'success': False, 'message': 'Character not found'}), 404

    # 支持 multipart/form-data 和 JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        name = request.form.get('name')
        char_type = request.form.get('type')
        bio = request.form.get('bio')
        phrases_str = request.form.get('phrases')
        phrases = json.loads(phrases_str) if phrases_str else None
        avatar_file = request.files.get('avatar')
        images_files = request.files.getlist('images')
        delete_avatar = request.form.get('delete_avatar') == 'true'
        delete_images_tokens = request.form.getlist('delete_images_token')
    else:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Invalid JSON'}), 400
        name = data.get('name')
        char_type = data.get('type')
        bio = data.get('bio')
        phrases = data.get('phrases')
        avatar_file = None
        images_files = []
        delete_avatar = data.get('delete_avatar') == True
        delete_images_tokens = data.get('delete_images_token') or []

    # 更新基本信息
    if name:
        character.name = name
    if char_type and char_type in Config.ROLEPLAY_APP_ID_MAP:
        character.type = char_type

    # 获取或创建详情
    detail = character.detail
    if not detail:
        detail = RoleplayCharacterDetail(rid=character.rid)
        db.session.add(detail)
        db.session.flush()

    # 更新文本字段
    if bio is not None:
        detail.bio = bio
    if phrases is not None:
        detail.phrases = json.dumps(phrases) if phrases else None

    # 处理删除头像
    if delete_avatar and detail.avatar_id:
        _delete_file(detail.avatar_id)
        detail.avatar_id = None

    # 处理上传头像
    if avatar_file and avatar_file.filename:
        if allowed_avatar_file(avatar_file.filename):
            avatar_file.seek(0, os.SEEK_END)
            avatar_size = avatar_file.tell()
            avatar_file.seek(0)
            if avatar_size <= Config.MAX_AVATAR_SIZE:
                if detail.avatar_id:
                    _delete_file(detail.avatar_id)
                secure_filename = save_avatar_file(avatar_file)
                new_file = File(original_filename=avatar_file.filename, secure_filename=secure_filename)
                db.session.add(new_file)
                db.session.flush()
                detail.avatar_id = new_file.fid

    # 处理增量删除图片（通过 token）
    if delete_images_tokens:
        old_images_set = set(_parse_images_id(detail.images_id))
        for token in delete_images_tokens:
            try:
                payload = decode_file_token(token)
                fid = payload.get('fid')
                if fid in old_images_set:
                    _delete_file(fid)
                    old_images_set.discard(fid)
            except Exception:
                continue
        detail.images_id = _serialize_images_id(list(old_images_set)) if old_images_set else None

    # 处理追加新图片
    if images_files:
        old_images = _parse_images_id(detail.images_id) if detail.images_id else []
        new_fids = []
        for file in images_files:
            if file.filename and allowed_avatar_file(file.filename):
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                if file_size <= Config.MAX_AVATAR_SIZE:
                    secure_filename = save_avatar_file(file)
                    new_file = File(original_filename=file.filename, secure_filename=secure_filename)
                    db.session.add(new_file)
                    db.session.flush()
                    new_fids.append(new_file.fid)
        if new_fids:
            all_fids = old_images + new_fids
            detail.images_id = _serialize_images_id(all_fids)

    db.session.commit()

    detail = character.detail
    images_id_list = _parse_images_id(detail.images_id) if detail else []

    return jsonify({
        'success': True,
        'message': 'Character updated',
        'character': {
            'rid': character.rid,
            'type': character.type,
            'name': character.name,
            'bio': detail.bio if detail else None,
            'phrases': json.loads(detail.phrases) if detail and detail.phrases else [],
            'avatar_token': generate_file_token(detail.avatar_id) if detail and detail.avatar_id else None,
            'images_token': [generate_file_token(fid) for fid in images_id_list]
        }
    })


@roleplay_admin_bp.route('/<int:rid>/delete', methods=['DELETE'])
@token_required(require_admin=True)
def delete_character(_, rid):
    """删除角色（需无关联会话），同时删除关联图片文件"""
    character = RoleplayCharacter.query.get(rid)
    if not character:
        return jsonify({'success': False, 'message': 'Character not found'}), 404

    # 检查是否有会话关联
    session_count = RoleplaySession.query.filter_by(rid=rid).count()
    if session_count > 0:
        return jsonify({'success': False, 'message': 'Cannot delete character with active sessions'}), 409

    # 清理图片文件（avatar + images）
    detail = character.detail
    if detail:
        if detail.avatar_id:
            _delete_file(detail.avatar_id)
        if detail.images_id:
            for fid in _parse_images_id(detail.images_id):
                _delete_file(fid)

    db.session.delete(character)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Character deleted'}), 200