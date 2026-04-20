import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import request, jsonify

from utils.redis_client import get_token_valid_since, set_token_valid_since


def generate_token(user_id: int, role: str = 'user') -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': now + timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', 168))),
        'iat': now
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm=os.getenv('JWT_ALGORITHM', 'HS256'))


def decode_token(token: str) -> dict:
    # 懒加载：首次解码时确保 token_valid_since 已设置（服务启动时间）
    _ensure_token_valid_since()

    payload = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=[os.getenv('JWT_ALGORITHM', 'HS256')])

    # 检查 token 是否在最早有效时间之后
    valid_since = get_token_valid_since()
    if valid_since is not None:
        iat = payload.get('iat')
        if iat and iat < valid_since:
            raise Exception('Token expired by security policy')

    return payload


def _ensure_token_valid_since():
    """确保 token_valid_since 已设置（服务启动时或首次使用时）"""
    valid_since = get_token_valid_since()
    if valid_since is None:
        # 服务启动时默认设置当前时间为最早有效时间
        set_token_valid_since(datetime.now(timezone.utc).timestamp())


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
