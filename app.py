from functools import wraps

from flask import Flask, request, jsonify

from config import Config
from models import db
from models.user import User, UserInfo
from utils.email_utils import is_valid_email, generate_verification_code, send_verification_email
from utils.jwt_utils import generate_token, decode_token
from utils.password_utils import hash_password, verify_password
from utils.redis_client import get_verification_code, delete_verification_code

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            payload = decode_token(token)
            current_user_id = payload['user_id']
        except Exception:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
        return f(current_user_id, *args, **kwargs)

    return decorated


@app.route('/user/login', methods=['POST'])
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

    token = generate_token(user.uid)

    return jsonify({
        'success': True,
        'token': token,
        'userInfo': {
            'uid': user.uid,
            'username': user.username,
            'email': user.email
        }
    })


@app.route('/user/register', methods=['POST'])
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

    with app.app_context():
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


@app.route('/email/verification/send', methods=['POST'])
def send_verification():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON'}), 400

    email = data.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400

    code = generate_verification_code()
    send_verification_email(email, code)

    return jsonify({
        'success': True,
        'message': 'Verification code sent'
    })


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


@app.cli.command('init-db')
def init_db():
    """Initialize the database tables."""
    with app.app_context():
        db.create_all()
        print('Database tables created successfully.')


if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.FLASK_DEBUG)
