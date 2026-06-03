import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from werkzeug.utils import secure_filename

from config import Config


def allowed_avatar_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_AVATAR_EXTENSIONS


def get_file_mime(filename: str) -> str:
    """根据文件扩展名获取 MIME 类型"""
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return mime_types.get(ext, 'application/octet-stream')


def save_avatar_file(file) -> str:
    """保存头像文件，返回 secure_filename。
    扩展名从原始 file.filename（raw）取，不经 secure_filename。
    若扩展名不在 Config.ALLOWED_AVATAR_EXTENSIONS 中，抛 ValueError，
    让外层 caller（api/file.py、api/roleplay_admin.py）返回 400，
    不静默写脏数据。
    """
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    raw_name = file.filename or ''
    if '.' not in raw_name:
        raise ValueError(f'File has no extension: {raw_name!r}')
    ext = raw_name.rsplit('.', 1)[1].lower()
    if ext not in Config.ALLOWED_AVATAR_EXTENSIONS:
        raise ValueError(f'Extension {ext!r} not in allowed list')

    secure_filename_str = f"{uuid.uuid4().hex}.{ext}"

    file_path = os.path.join(Config.UPLOAD_FOLDER, secure_filename_str)
    file.save(file_path)

    return secure_filename_str


def get_avatar_file_path(filename: str) -> str:
    """获取头像文件的完整路径"""
    return os.path.join(Config.UPLOAD_FOLDER, filename)


def generate_avatar_token(user_id: int, fid: int) -> str:
    """生成头像访问 JWT token"""
    payload = {
        'user_id': user_id,
        'fid': fid,
        'exp': datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def decode_avatar_token(token: str) -> dict:
    """解码头像访问 JWT token"""
    return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])


def generate_file_token(fid: int) -> str:
    """生成文件访问 JWT token（无需用户认证）"""
    payload = {
        'fid': fid,
        'exp': datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def decode_file_token(token: str) -> dict:
    """解码文件访问 JWT token"""
    return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
