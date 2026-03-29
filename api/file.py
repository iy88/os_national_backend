import os

from flask import Blueprint, request, jsonify, send_file

from config import Config
from models import db, File, UserInfo
from utils.file_utils import (
    allowed_avatar_file,
    save_avatar_file,
    get_avatar_file_path,
    generate_avatar_token,
    decode_avatar_token,
    get_file_mime
)

file_bp = Blueprint('file', __name__, url_prefix='/file')


@file_bp.route('/avatar/upload', methods=['POST'])
def upload_avatar():
    """上传用户头像，返回 avatar token"""
    user_id = request.form.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'user_id is required'}), 400

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid user_id'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    if not allowed_avatar_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > Config.MAX_AVATAR_SIZE:
        return jsonify({'success': False, 'message': 'File too large'}), 400

    # 获取用户信息，检查是否已有头像
    user_info = UserInfo.query.get(user_id)
    old_avatar_id = user_info.avatar_id if user_info else None

    # 如果已有头像，删除旧文件和相关记录
    if old_avatar_id:
        old_file = File.query.get(old_avatar_id)
        if old_file:
            # 删除物理文件
            old_file_path = get_avatar_file_path(old_file.secure_filename)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            # 删除数据库记录
            db.session.delete(old_file)

    original_filename = file.filename
    secure_filename = save_avatar_file(file)

    # 保存新文件记录到数据库
    new_file = File(
        original_filename=original_filename,
        secure_filename=secure_filename
    )
    db.session.add(new_file)
    db.session.flush()

    # 更新用户头像 ID
    if user_info:
        user_info.avatar_id = new_file.fid
    else:
        # 如果 UserInfo 不存在，创建它
        new_user_info = UserInfo(uid=user_id, avatar_id=new_file.fid)
        db.session.add(new_user_info)

    db.session.commit()

    avatar_token = generate_avatar_token(user_id, new_file.fid)

    return jsonify({
        'success': True,
        'message': 'Avatar uploaded',
        'avatar_token': avatar_token
    })


@file_bp.route('/avatar/fetch', methods=['GET'])
def fetch_avatar():
    """根据 avatar token 获取头像图片"""
    token = request.args.get('token')
    if not token:
        return jsonify({'success': False, 'message': 'token is required'}), 400

    # noinspection PyBroadException
    try:
        payload = decode_avatar_token(token)
        fid = payload.get('fid')
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid or expired token'}), 401

    file_record = File.query.get(fid)
    if not file_record:
        return jsonify({'success': False, 'message': 'Avatar not found'}), 404

    file_path = get_avatar_file_path(file_record.secure_filename)
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'message': 'Avatar not found'}), 404

    mime = get_file_mime(file_record.secure_filename)
    return send_file(file_path, mimetype=mime)
