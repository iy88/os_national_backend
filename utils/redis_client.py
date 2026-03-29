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
STREAM_MESSAGE_TTL = 3600  # 1 hour
AI_SESSION_TTL = 3600  # 1 hour
STREAM_EVENT_MAXLEN = 10000


def set_verification_code(email: str, code: str):
    redis_client.setex(f"email_verify:{email}", VERIFICATION_CODE_EXPIRE, code)


def get_verification_code(email: str) -> str:
    return redis_client.get(f"email_verify:{email}")


def delete_verification_code(email: str):
    redis_client.delete(f"email_verify:{email}")


# ============ 流式消息相关 ============

def get_stream_mid(sid: int) -> int | None:
    """获取当前会话正在流式传输的消息 MID"""
    mid = redis_client.get(f'stream:{sid}')
    return int(mid) if mid else None


def set_stream_mid(sid: int, mid: int):
    """设置当前会话正在流式传输的消息 MID"""
    redis_client.setex(f'stream:{sid}', STREAM_MESSAGE_TTL, mid)


def clear_stream_mid(sid: int):
    """清除当前会话的流式传输状态"""
    redis_client.delete(f'stream:{sid}')


def append_stream_content(mid: int, chunk: str):
    """追加内容到流式消息（片段追加），自动设置 TTL"""
    key = f'stream_content:{mid}'
    pipe = redis_client.pipeline()
    pipe.append(key, chunk)
    pipe.expire(key, STREAM_MESSAGE_TTL)
    pipe.execute()


def get_stream_content(mid: int) -> str:
    """获取已缓存的流式消息内容"""
    return redis_client.get(f'stream_content:{mid}') or ''


def set_stream_content(mid: int, content: str = ''):
    """初始化流式消息内容"""
    redis_client.setex(f'stream_content:{mid}', STREAM_MESSAGE_TTL, content)


def clear_stream_content(mid: int):
    """清除流式消息内容"""
    redis_client.delete(f'stream_content:{mid}')


def clear_stream(sid: int, mid: int):
    """清除流式消息的所有 Redis 缓存"""
    clear_stream_mid(sid)
    clear_stream_content(mid)


def clear_stream_marker(sid: int):
    """仅清除会话进行中标记，不清理内容缓存。"""
    clear_stream_mid(sid)


def init_stream_runtime(mid: int):
    """初始化流式运行时缓存（内容、事件、状态）。"""
    set_stream_content(mid, '')
    redis_client.delete(f'stream_events:{mid}')
    redis_client.delete(f'stream_state:{mid}')


def clear_stream_runtime(mid: int):
    """清除流式运行时缓存（内容、事件、状态）。"""
    pipe = redis_client.pipeline()
    pipe.delete(f'stream_content:{mid}')
    pipe.delete(f'stream_events:{mid}')
    pipe.delete(f'stream_state:{mid}')
    pipe.execute()


def append_stream_event(mid: int, event_type: str, **fields):
    """向 Redis Stream 追加事件。"""
    key = f'stream_events:{mid}'
    payload = {'type': event_type}
    for k, v in fields.items():
        if v is not None:
            payload[k] = str(v)
    pipe = redis_client.pipeline()
    pipe.xadd(key, payload, maxlen=STREAM_EVENT_MAXLEN, approximate=True)
    pipe.expire(key, STREAM_MESSAGE_TTL)
    pipe.execute()


def read_stream_events(mid: int, last_id: str = '0-0', block_ms: int = 15000, count: int = 100):
    """从 Redis Stream 读取新增事件。"""
    key = f'stream_events:{mid}'
    data = redis_client.xread({key: last_id}, count=count, block=block_ms)
    if not data:
        return []
    # data: [(key, [(id, fields), ...])]
    return data[0][1]


def get_stream_last_event_id(mid: int) -> str | None:
    """获取 Redis Stream 最后一条事件 ID。"""
    key = f'stream_events:{mid}'
    data = redis_client.xrevrange(key, count=1)
    if not data:
        return None
    return data[0][0]


def set_stream_state(mid: int, state: str, message: str | None = None):
    """设置流式状态（running/done/error）。"""
    key = f'stream_state:{mid}'
    payload = {'state': state}
    if message:
        payload['message'] = message
    pipe = redis_client.pipeline()
    pipe.hset(key, mapping=payload)
    pipe.expire(key, STREAM_MESSAGE_TTL)
    pipe.execute()


def get_stream_state(mid: int) -> dict:
    """读取流式状态。"""
    return redis_client.hgetall(f'stream_state:{mid}') or {}


def acquire_stream_producer_lock(sid: int, mid: int) -> bool:
    """抢占生产者锁，确保同一 sid/mid 只有一个生产者。"""
    return bool(redis_client.set(f'stream_producer:{sid}', str(mid), nx=True, ex=STREAM_MESSAGE_TTL))


def refresh_stream_producer_lock(sid: int):
    """续期生产者锁。"""
    redis_client.expire(f'stream_producer:{sid}', STREAM_MESSAGE_TTL)


def get_stream_producer_lock(sid: int) -> str | None:
    """读取生产者锁值。"""
    return redis_client.get(f'stream_producer:{sid}')


def release_stream_producer_lock(sid: int):
    """释放生产者锁。"""
    redis_client.delete(f'stream_producer:{sid}')


def get_ai_session_id(sid: int) -> str | None:
    """获取会话绑定的 AI session_id"""
    return redis_client.get(f'ai_session:{sid}')


def set_ai_session_id(sid: int, ai_session_id: str):
    """保存会话绑定的 AI session_id"""
    redis_client.setex(f'ai_session:{sid}', AI_SESSION_TTL, ai_session_id)


def clear_ai_session_id(sid: int):
    """清除会话绑定的 AI session_id"""
    redis_client.delete(f'ai_session:{sid}')


# ============ Roleplay 流式消息相关 ============

def _rp_stream_key(uid: int, rid: int, suffix: str) -> str:
    """构建 roleplay 流式消息 Redis key"""
    return f'rp_stream:{uid}:{rid}:{suffix}'


def get_rp_stream_mid(uid: int, rid: int) -> int | None:
    """获取当前角色对话正在流式传输的消息 MID"""
    mid = redis_client.get(_rp_stream_key(uid, rid, ''))
    return int(mid) if mid else None


def set_rp_stream_mid(uid: int, rid: int, mid: int):
    """设置当前角色对话正在流式传输的消息 MID"""
    redis_client.setex(_rp_stream_key(uid, rid, ''), STREAM_MESSAGE_TTL, mid)


def clear_rp_stream_mid(uid: int, rid: int):
    """清除当前角色对话的流式传输状态"""
    redis_client.delete(_rp_stream_key(uid, rid, ''))


def append_rp_stream_content(mid: int, chunk: str):
    """追加内容到流式消息（片段追加），自动设置 TTL"""
    key = f'rp_stream_content:{mid}'
    pipe = redis_client.pipeline()
    pipe.append(key, chunk)
    pipe.expire(key, STREAM_MESSAGE_TTL)
    pipe.execute()


def get_rp_stream_content(mid: int) -> str:
    """获取已缓存的流式消息内容"""
    return redis_client.get(f'rp_stream_content:{mid}') or ''


def set_rp_stream_content(mid: int, content: str = ''):
    """初始化流式消息内容"""
    redis_client.setex(f'rp_stream_content:{mid}', STREAM_MESSAGE_TTL, content)


def clear_rp_stream_content(mid: int):
    """清除流式消息内容"""
    redis_client.delete(f'rp_stream_content:{mid}')


def clear_rp_stream(uid: int, rid: int, mid: int):
    """清除流式消息的所有 Redis 缓存"""
    clear_rp_stream_mid(uid, rid)
    clear_rp_stream_content(mid)


def init_rp_stream_runtime(mid: int):
    """初始化流式运行时缓存（内容、事件、状态）。"""
    set_rp_stream_content(mid, '')
    redis_client.delete(f'rp_stream_events:{mid}')
    redis_client.delete(f'rp_stream_state:{mid}')


def clear_rp_stream_runtime(mid: int):
    """清除流式运行时缓存（内容、事件、状态）。"""
    pipe = redis_client.pipeline()
    pipe.delete(f'rp_stream_content:{mid}')
    pipe.delete(f'rp_stream_events:{mid}')
    pipe.delete(f'rp_stream_state:{mid}')
    pipe.execute()


def append_rp_stream_event(mid: int, event_type: str, **fields):
    """向 Redis Stream 追加事件。"""
    key = f'rp_stream_events:{mid}'
    payload = {'type': event_type}
    for k, v in fields.items():
        if v is not None:
            payload[k] = str(v)
    pipe = redis_client.pipeline()
    pipe.xadd(key, payload, maxlen=STREAM_EVENT_MAXLEN, approximate=True)
    pipe.expire(key, STREAM_MESSAGE_TTL)
    pipe.execute()


def read_rp_stream_events(mid: int, last_id: str = '0-0', block_ms: int = 15000, count: int = 100):
    """从 Redis Stream 读取新增事件。"""
    key = f'rp_stream_events:{mid}'
    data = redis_client.xread({key: last_id}, count=count, block=block_ms)
    if not data:
        return []
    return data[0][1]


def get_rp_stream_last_event_id(mid: int) -> str | None:
    """获取 Redis Stream 最后一条事件 ID。"""
    key = f'rp_stream_events:{mid}'
    data = redis_client.xrevrange(key, count=1)
    if not data:
        return None
    return data[0][0]


def set_rp_stream_state(mid: int, state: str, message: str | None = None):
    """设置流式状态（running/done/error）。"""
    key = f'rp_stream_state:{mid}'
    payload = {'state': state}
    if message:
        payload['message'] = message
    pipe = redis_client.pipeline()
    pipe.hset(key, mapping=payload)
    pipe.expire(key, STREAM_MESSAGE_TTL)
    pipe.execute()


def get_rp_stream_state(mid: int) -> dict:
    """读取流式状态。"""
    return redis_client.hgetall(f'rp_stream_state:{mid}') or {}


def acquire_rp_stream_producer_lock(uid: int, rid: int, mid: int) -> bool:
    """抢占生产者锁，确保同一 uid/rid/mid 只有一个生产者。"""
    return bool(redis_client.set(_rp_stream_key(uid, rid, 'producer'), str(mid), nx=True, ex=STREAM_MESSAGE_TTL))


def refresh_rp_stream_producer_lock(uid: int, rid: int):
    """续期生产者锁。"""
    redis_client.expire(_rp_stream_key(uid, rid, 'producer'), STREAM_MESSAGE_TTL)


def get_rp_stream_producer_lock(uid: int, rid: int) -> str | None:
    """读取生产者锁值。"""
    return redis_client.get(_rp_stream_key(uid, rid, 'producer'))


def release_rp_stream_producer_lock(uid: int, rid: int):
    """释放生产者锁。"""
    redis_client.delete(_rp_stream_key(uid, rid, 'producer'))
