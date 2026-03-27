import os
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import request, jsonify


def generate_token(user_id: int) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', 168))),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm=os.getenv('JWT_ALGORITHM', 'HS256'))


def decode_token(token: str) -> dict:
    return jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=[os.getenv('JWT_ALGORITHM', 'HS256')])


def token_required(f):
    """JWT 认证装饰器，从 Authorization Header 提取 token 并验证"""
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
