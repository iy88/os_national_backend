from flask import Blueprint, request, jsonify

from models import db
from models.admin import Admin, AdminInfo
from utils.jwt_utils import generate_token, token_required
from utils.password_utils import verify_password
from utils.file_utils import generate_file_token

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    username_or_email = data.get('username') or data.get('email')
    password = data.get('password')

    if not username_or_email or not password:
        return jsonify({'success': False, 'message': 'Missing username/email or password'}), 400

    admin = Admin.query.filter(
        (Admin.username == username_or_email) | (Admin.email == username_or_email)
    ).first()

    if not admin or not verify_password(password, admin.password_hash):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    token = generate_token(admin.aid, role='admin')

    avatar_token = None
    if admin.admin_info and admin.admin_info.avatar_id:
        avatar_token = generate_file_token(admin.admin_info.avatar_id)

    return jsonify({
        'success': True,
        'token': token,
        'adminInfo': {
            'aid': admin.aid,
            'username': admin.username,
            'email': admin.email,
            'avatarToken': avatar_token
        }
    })


@admin_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user_id):
    """获取当前管理员信息"""
    admin = Admin.query.get(current_user_id)
    if not admin:
        return jsonify({'success': False, 'message': 'Admin not found'}), 404

    avatar_token = None
    if admin.admin_info and admin.admin_info.avatar_id:
        avatar_token = generate_file_token(admin.admin_info.avatar_id)

    return jsonify({
        'success': True,
        'adminInfo': {
            'aid': admin.aid,
            'username': admin.username,
            'email': admin.email,
            'gender': admin.admin_info.gender if admin.admin_info else None,
            'age': admin.admin_info.age if admin.admin_info else None,
            'basicInfo': admin.admin_info.basic_info if admin.admin_info else None,
            'bio': admin.admin_info.bio if admin.admin_info else None,
            'avatarToken': avatar_token
        }
    })


@admin_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user_id):
    """批量（增量）更新当前管理员信息，字段均可选"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    admin = Admin.query.get(current_user_id)
    if not admin:
        return jsonify({'success': False, 'message': 'Admin not found'}), 404

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
        if username != admin.username and Admin.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 409
        admin.username = username

    # 更新管理员信息
    if admin.admin_info:
        if gender is not None:
            admin.admin_info.gender = gender
        if age is not None:
            admin.admin_info.age = age
        if basic_info is not None:
            admin.admin_info.basic_info = basic_info
        if bio is not None:
            admin.admin_info.bio = bio
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Profile updated',
        'adminInfo': {
            'aid': admin.aid,
            'username': admin.username,
            'email': admin.email,
            'gender': admin.admin_info.gender if admin.admin_info else None,
            'age': admin.admin_info.age if admin.admin_info else None,
            'basicInfo': admin.admin_info.basic_info if admin.admin_info else None,
            'bio': admin.admin_info.bio if admin.admin_info else None
        }
    })