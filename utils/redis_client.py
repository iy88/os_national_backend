import os

import redis
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    password=os.getenv('REDIS_PASSWORD') or None,
    decode_responses=True
)

VERIFICATION_CODE_EXPIRE = 300  # 5 minutes


def set_verification_code(email: str, code: str):
    redis_client.setex(f"email_verify:{email}", VERIFICATION_CODE_EXPIRE, code)


def get_verification_code(email: str) -> str:
    return redis_client.get(f"email_verify:{email}")


def delete_verification_code(email: str):
    redis_client.delete(f"email_verify:{email}")
