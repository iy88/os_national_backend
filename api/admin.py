from flask import Blueprint, request, jsonify

from models import db
from models.admin import Admin
from models.user import User, UserInfo
from utils.file_utils import generate_file_token
from utils.jwt_utils import generate_token, token_required
from utils.password_utils import verify_password

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['POST'])
def login():
    """管理员登录：先验证用户，再检查是否在 admins 表中"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    username_or_email = data.get('username') or data.get('email')
    password = data.get('password')

    if not username_or_email or not password:
        return jsonify({'success': False, 'message': 'Missing username/email or password'}), 400

    # 1. 查找用户
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    # 2. 检查是否在 admins 表中
    if not Admin.query.get(user.uid):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    # 3. 生成 admin token
    token = generate_token(user.uid, role='admin')

    avatar_token = None
    if user.user_info and user.user_info.avatar_id:
        avatar_token = generate_file_token(user.user_info.avatar_id)

    return jsonify({
        'success': True,
        'token': token,
        'userInfo': {
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'avatarToken': avatar_token
        }
    })


@admin_bp.route('/profile', methods=['GET'])
@token_required(require_admin=True)
def get_profile(current_user_id):
    """获取当前管理员信息"""
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    user_info = UserInfo.query.get(current_user_id)

    avatar_token = None
    if user_info and user_info.avatar_id:
        avatar_token = generate_file_token(user_info.avatar_id)

    return jsonify({
        'success': True,
        'userInfo': {
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'gender': user_info.gender if user_info else None,
            'age': user_info.age if user_info else None,
            'basicInfo': user_info.basic_info if user_info else None,
            'bio': user_info.bio if user_info else None,
            'avatarToken': avatar_token
        }
    })


@admin_bp.route('/profile', methods=['PUT'])
@token_required(require_admin=True)
def update_profile(current_user_id):
    """批量（增量）更新当前管理员信息，字段均可选"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    user_info = UserInfo.query.get(current_user_id)

    # 可更新的字段
    username = data.get('username')
    gender = data.get('gender')
    age = data.get('age')
    basic_info = data.get('basicInfo')
    bio = data.get('bio')

    # 用户名校验
    if username is not None:
        if len(username) < 3 or len(username) > 80:
            return jsonify({'success': False, 'message': 'Username must be 3-80 characters'}), 400
        if username != user.username and User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 409
        user.username = username

    # 更新用户信息
    if user_info:
        if gender is not None:
            user_info.gender = gender
        if age is not None:
            user_info.age = age
        if basic_info is not None:
            user_info.basic_info = basic_info
        if bio is not None:
            user_info.bio = bio
    db.session.commit()

    # 重新获取最新数据
    user = User.query.get(current_user_id)
    user_info = UserInfo.query.get(current_user_id)
    avatar_token = None
    if user_info and user_info.avatar_id:
        avatar_token = generate_file_token(user_info.avatar_id)

    return jsonify({
        'success': True,
        'message': 'Profile updated',
        'userInfo': {
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'gender': user_info.gender if user_info else None,
            'age': user_info.age if user_info else None,
            'basicInfo': user_info.basic_info if user_info else None,
            'bio': user_info.bio if user_info else None,
            'avatarToken': avatar_token
        }
    })
