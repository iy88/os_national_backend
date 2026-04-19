import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import request, jsonify


def generate_token(user_id: int, role: str = 'user') -> str:
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', 168))),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm=os.getenv('JWT_ALGORITHM', 'HS256'))


def token_required(require_admin: bool = False):
    """JWT 认证装饰器
    - require_admin=False（默认）：兼容 user 和 admin token，只验证 token 有效
    - require_admin=True：必须 admin token 才可通过，否则返回 403

    支持两种用法：
    - @token_required  (不带括号，等同于 require_admin=False)
    - @token_required()  (带括号，默认 require_admin=False)
    - @token_required(require_admin=True)  (带参数)
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'success': False, 'message': 'Token is missing'}), 401
            try:
                if token.startswith('Bearer '):
                    token = token[7:]
                payload = decode_token(token)
                if require_admin and payload.get('role') != 'admin':
                    return jsonify({'success': False, 'message': 'Admin access required'}), 403
                current_user_id = payload['user_id']
            except Exception:
                return jsonify({'success': False, 'message': 'Invalid token'}), 401
            return f(current_user_id, *args, **kwargs)

        return decorated

    # 支持 @token_required 不带括号的用法
    if callable(require_admin):
        # require_admin 实际上是函数，说明是用 @token_required 不带括号
        f = require_admin
        require_admin = False
        return decorator(f)

    return decorator


def decode_token(token: str) -> dict:
    return jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=[os.getenv('JWT_ALGORITHM', 'HS256')])
