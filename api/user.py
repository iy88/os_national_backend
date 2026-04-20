from flask import Blueprint, request, jsonify

from models import db
from models.admin import Admin
from models.user import User, UserInfo
from utils.email_utils import is_valid_email
from utils.file_utils import generate_file_token
from utils.jwt_utils import generate_token, token_required
from utils.password_utils import hash_password, verify_password
from utils.redis_client import get_verification_code, delete_verification_code

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    username_or_email = data.get('username') or data.get('email')
    password = data.get('password')

    if not username_or_email or not password:
        return jsonify({'success': False, 'message': 'Missing username/email or password'}), 400

    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not verify_password(password, user.password_hash):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    is_admin = Admin.query.get(user.uid) is not None
    token = generate_token(user.uid, role='admin' if is_admin else 'user')

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
            'role': 'admin' if is_admin else 'user',
            'avatarToken': avatar_token
        }
    })


@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    email = data.get('email')
    password = data.get('password')
    verify_code = data.get('verifyCode')
    username = data.get('username')

    if not email or not password or not verify_code:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400

    if username and (len(username) < 3 or len(username) > 80):
        return jsonify({'success': False, 'message': 'Username must be 3-80 characters'}), 400

    if len(password) < 6 or len(password) > 128:
        return jsonify({'success': False, 'message': 'Password must be 6-128 characters'}), 400

    stored_code = get_verification_code(email)
    if not stored_code or stored_code != verify_code:
        return jsonify({'success': False, 'message': 'Invalid or expired verification code'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 409

    if User.query.filter_by(username=username).first() and username:
        return jsonify({'success': False, 'message': 'Username already exists'}), 409

    # 默认用户名：取 email @ 前的部分
    if not username:
        username = email.split('@')[0]

    password_hash = hash_password(password)

    new_user = User(username=username, email=email, password_hash=password_hash)
    db.session.add(new_user)
    db.session.flush()

    new_user_info = UserInfo(uid=new_user.uid)
    db.session.add(new_user_info)
    db.session.commit()

    user_uid = new_user.uid
    user_username = new_user.username
    user_email = new_user.email

    delete_verification_code(email)
    token = generate_token(user_uid)

    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'token': token,
        'userInfo': {
            'uid': user_uid,
            'username': user_username,
            'email': user_email
        }
    }), 201


@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user_id):
    """获取当前用户信息"""
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

    avatar_token = None
    if user.user_info and user.user_info.avatar_id:
        avatar_token = generate_file_token(user.user_info.avatar_id)

    return jsonify({
        'success': True,
        'userInfo': {
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'gender': user.user_info.gender if user.user_info else None,
            'age': user.user_info.age if user.user_info else None,
            'basicInfo': user.user_info.basic_info if user.user_info else None,
            'bio': user.user_info.bio if user.user_info else None,
            'avatarToken': avatar_token
        }
    })


@user_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user_id):
    """批量（增量）更新当前用户信息，字段均可选"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404

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

    # 更新用户信息（直接在请求上下文中操作，无需额外 app_context）
    if user.user_info:
        if gender is not None:
            user.user_info.gender = gender
        if age is not None:
            user.user_info.age = age
        if basic_info is not None:
            user.user_info.basic_info = basic_info
        if bio is not None:
            user.user_info.bio = bio
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Profile updated',
        'userInfo': {
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'gender': user.user_info.gender if user.user_info else None,
            'age': user.user_info.age if user.user_info else None,
            'basicInfo': user.user_info.basic_info if user.user_info else None,
            'bio': user.user_info.bio if user.user_info else None
        }
    })
