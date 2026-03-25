import os
import uuid
import jwt
from datetime import datetime, timedelta
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
    """保存头像文件，返回 secure_filename"""
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
    secure_filename_str = f"{uuid.uuid4().hex}.{ext}"

    file_path = os.path.join(Config.UPLOAD_FOLDER, secure_filename_str)
    file.save(file_path)

    return secure_filename_str


def get_avatar_file_path(secure_filename: str) -> str:
    """获取头像文件的完整路径"""
    return os.path.join(Config.UPLOAD_FOLDER, secure_filename)


def generate_avatar_token(user_id: int, fid: int) -> str:
    """生成头像访问 JWT token"""
    payload = {
        'user_id': user_id,
        'fid': fid,
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def decode_avatar_token(token: str) -> dict:
    """解码头像访问 JWT token"""
    return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
