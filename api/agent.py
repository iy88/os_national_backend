import json
import threading
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app

from config import Config
from models import db, ConversationSession, Message
from utils.ai_provider import get_ai_provider, InvalidAISessionError
from utils.jwt_utils import token_required
from utils.redis_client import (
    get_stream_mid,
    set_stream_mid,
    append_stream_content,
    get_stream_content,
    clear_stream,
    clear_stream_runtime,
    clear_stream_marker,
    init_stream_runtime,
    append_stream_event,
    read_stream_events,
    set_stream_state,
    get_stream_state,
    acquire_stream_producer_lock,
    refresh_stream_producer_lock,
    get_stream_producer_lock,
    release_stream_producer_lock,
    get_ai_session_id,
    set_ai_session_id,
    clear_ai_session_id,
)

agent_bp = Blueprint('agent', __name__, url_prefix='/agent/travel-route-plan')


def sse_response(generator_func):
    """统一构建 SSE Response，补齐防缓冲头，降低前端误报 fetch failed。"""
    response = Response(stream_with_context(generator_func()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


def build_messages(sid: int, exclude_mid: int | None = None) -> list:
    """从数据库加载会话历史，构建消息列表"""
    query = Message.query.filter_by(sid=sid)
    if exclude_mid is not None:
        query = query.filter(Message.mid != exclude_mid)
    messages = query.order_by(Message.mid).all()
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def _remove_empty_assistant_message(sid: int, mid: int):
    """异常时清理空 assistant 占位，避免数据库残留空记录。"""
    try:
        msg = Message.query.filter_by(mid=mid, sid=sid, role='assistant').first()
        if not msg:
            return
        if (msg.content or '').strip():
            return

        db.session.delete(msg)
        session_row = ConversationSession.query.filter_by(sid=sid).first()
        if session_row:
            session_row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        print(f"Removed empty assistant message sid={sid}, mid={mid}")
    except Exception as cleanup_err:
        db.session.rollback()
        print(f"Failed to remove empty assistant message sid={sid}, mid={mid}: {cleanup_err}")


def _persist_assistant_message(sid: int, mid: int, current_user_id: int, full_content: str):
    msg = Message.query.filter_by(mid=mid, sid=sid).first()
    if not msg:
        raise RuntimeError('Assistant placeholder not found')
    msg.content = full_content

    session_row = ConversationSession.query.filter_by(sid=sid, uid=current_user_id).first()
    if not session_row:
        raise RuntimeError('Session not found while persisting stream result')
    session_row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.session.commit()


def _run_stream_producer(app, sid: int, mid: int, current_user_id: int, base_messages: list, ai_session_id: str | None):
    """后台生产者：唯一拉取 LLM 流并写入 Redis Stream 事件。"""
    with app.app_context():
        ai_provider = get_ai_provider(
            Config.AI_PROVIDER,
            Config.AI_API_KEY,
            Config.AI_APP_ID
        )

        set_stream_state(mid, 'running')
        refresh_stream_producer_lock(sid)

        def produce(active_messages: list, active_session_id: str | None):
            for chunk in ai_provider.chat_stream(active_messages, session_id=active_session_id):
                append_stream_content(mid, chunk)
                append_stream_event(mid, 'content', content=chunk)
                refresh_stream_producer_lock(sid)

        try:
            try:
                produce(base_messages, ai_session_id)
            except InvalidAISessionError as invalid_session_err:
                print(f"Invalid AI session_id detected sid={sid}: {invalid_session_err}")
                clear_ai_session_id(sid)
                fallback_messages = build_messages(sid, exclude_mid=mid)
                produce(fallback_messages, None)

            full_content = get_stream_content(mid)
            _persist_assistant_message(sid, mid, current_user_id, full_content)

            new_ai_session_id = ai_provider.get_last_session_id()
            if new_ai_session_id:
                set_ai_session_id(sid, new_ai_session_id)

            append_stream_event(mid, 'done', sid=sid)
            set_stream_state(mid, 'done')
        except Exception as e:
            print(f"AI streaming error sid={sid}, mid={mid}: {e}")
            db.session.rollback()
            _remove_empty_assistant_message(sid, mid)
            append_stream_event(mid, 'error', message=str(e))
            set_stream_state(mid, 'error', message=str(e))
        finally:
            clear_stream_marker(sid)
            release_stream_producer_lock(sid)


def _ensure_stream_producer(app, sid: int, mid: int, current_user_id: int, messages: list, ai_session_id: str | None):
    """确保同一个 sid/mid 只有一个生产者。"""
    lock_mid = get_stream_producer_lock(sid)
    if lock_mid == str(mid):
        return

    if not acquire_stream_producer_lock(sid, mid):
        return

    producer = threading.Thread(
        target=_run_stream_producer,
        args=(app, sid, mid, current_user_id, messages, ai_session_id),
        daemon=True
    )
    producer.start()


def _consume_stream_events(sid: int, mid: int, resume: bool = False):
    """SSE 消费者：回放已有事件并实时追尾新增事件。"""
    should_cleanup_runtime = False
    start_data = {'type': 'start', 'sid': sid, 'mid': mid}
    if resume:
        start_data['resume'] = True
    try:
        yield f"data: {json.dumps(start_data)}\n\n"

        last_id = '0-0'
        idle_rounds = 0

        while True:
            try:
                events = read_stream_events(mid, last_id=last_id, block_ms=5000, count=200)
            except Exception as e:
                should_cleanup_runtime = True
                yield f"data: {json.dumps({'type': 'error', 'message': f'Read stream events failed: {e}'})}\n\n"
                return

            if events:
                idle_rounds = 0
                for event_id, fields in events:
                    last_id = event_id
                    event_type = fields.get('type')
                    if event_type == 'content':
                        yield f"data: {json.dumps({'type': 'content', 'content': fields.get('content', '')})}\n\n"
                    elif event_type == 'done':
                        should_cleanup_runtime = True
                        yield f"data: {json.dumps({'type': 'done', 'sid': sid, 'mid': mid})}\n\n"
                        return
                    elif event_type == 'error':
                        should_cleanup_runtime = True
                        yield f"data: {json.dumps({'type': 'error', 'message': fields.get('message', 'Unknown error')})}\n\n"
                        return
                continue

            idle_rounds += 1
            state = get_stream_state(mid)
            stream_state = state.get('state')
            if stream_state == 'done':
                should_cleanup_runtime = True
                yield f"data: {json.dumps({'type': 'done', 'sid': sid, 'mid': mid})}\n\n"
                return
            if stream_state == 'error':
                should_cleanup_runtime = True
                yield f"data: {json.dumps({'type': 'error', 'message': state.get('message', 'Unknown error')})}\n\n"
                return

            if idle_rounds >= 24:
                should_cleanup_runtime = True
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream timeout waiting for producer'})}\n\n"
                return

            # keepalive，避免代理或浏览器空闲断开
            yield ': ping\n\n'
    finally:
        if should_cleanup_runtime:
            try:
                clear_stream_runtime(mid)
            except Exception as cleanup_err:
                print(f"Clear stream runtime failed mid={mid}: {cleanup_err}")


@agent_bp.route('/chat/list', methods=['GET'])
@token_required
def get_sessions(current_user_id):
    """获取用户所有会话列表"""
    sessions = ConversationSession.query.filter_by(uid=current_user_id).order_by(
        ConversationSession.updated_at.desc()
    ).all()

    result = []
    for session in sessions:
        # 检查是否有未完成的流式消息
        has_incomplete = get_stream_mid(session.sid) is not None
        result.append({
            'sid': session.sid,
            'title': session.title,
            'hasIncompleteMessage': has_incomplete,
            'createdAt': session.created_at.isoformat() + 'Z',
            'updatedAt': session.updated_at.isoformat() + 'Z' if session.updated_at else None
        })

    return jsonify({
        'success': True,
        'sessions': result
    })


@agent_bp.route('/chat/detail/<int:sid>', methods=['GET'])
@token_required
def get_session_detail(current_user_id, sid):
    """获取指定会话详情（含消息历史）"""
    session = ConversationSession.query.filter_by(sid=sid, uid=current_user_id).first()
    if not session:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    messages = Message.query.filter_by(sid=sid).order_by(Message.mid).all()
    message_list = [{
        'mid': msg.mid,
        'role': msg.role,
        'content': msg.content,
        'createdAt': msg.created_at.isoformat() + 'Z'
    } for msg in messages]

    # 检查是否有未完成的流式消息
    incomplete_mid = get_stream_mid(sid)

    return jsonify({
        'success': True,
        'session': {
            'sid': session.sid,
            'title': session.title,
            'messages': message_list,
            'incompleteMid': incomplete_mid,
            'createdAt': session.created_at.isoformat() + 'Z',
            'updatedAt': session.updated_at.isoformat() + 'Z' if session.updated_at else None
        }
    })


@agent_bp.route('/chat/title/edit/<int:sid>', methods=['PUT'])
@token_required
def edit_session_title(current_user_id, sid):
    """
    编辑会话标题

    请求体:
        title: string - 新标题
    """
    session = ConversationSession.query.filter_by(sid=sid, uid=current_user_id).first()
    if not session:
        return jsonify({'success': False, 'message': 'Session not found'}), 404

    data = request.get_json() or {}
    title = data.get('title')
    if not title:
        return jsonify({'success': False, 'message': 'title is required'}), 400

    session.title = title
    db.session.commit()

    return jsonify({
        'success': True,
        'session': {
            'sid': session.sid,
            'title': session.title,
            'createdAt': session.created_at.isoformat() + 'Z',
            'updatedAt': session.updated_at.isoformat() + 'Z' if session.updated_at else None
        }
    })


@agent_bp.route('/message', methods=['POST'])
@token_required
def send_message(current_user_id):
    """
    发送消息，自动创建会话，SSE 流式响应

    请求体:
        content: str - 消息内容
        sid: int (可选) - 会话 ID，不传则创建新会话
    """
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    sid = data.get('sid')

    # 验证会话
    session = None
    existing_session = False
    if sid:
        session = ConversationSession.query.filter_by(sid=sid, uid=current_user_id).first()
        if not session:
            return jsonify({'success': False, 'message': 'Session not found'}), 404
        existing_session = True

    # noinspection PyUnresolvedReferences,PyProtectedMember
    app_obj = current_app._get_current_object()

    # 检查是否有进行中的流（恢复模式）
    existing_mid = get_stream_mid(sid) if sid else None
    ai_session_id = get_ai_session_id(sid) if sid else None
    if existing_mid:
        state = get_stream_state(existing_mid)
        lock_mid = get_stream_producer_lock(sid)
        has_runtime = bool(get_stream_content(existing_mid)) or bool(state)

        # 兜底：只有 stream 标记，没有任何运行时数据，视为陈旧状态并清理。
        if not has_runtime and lock_mid != str(existing_mid):
            clear_stream(sid, existing_mid)
            clear_stream_runtime(existing_mid)
        else:
            # 如果生产者意外丢失且状态为 running，则尝试基于历史重启唯一生产者。
            if lock_mid != str(existing_mid) and state.get('state') == 'running':
                messages = build_messages(sid, exclude_mid=existing_mid)
                _ensure_stream_producer(app_obj, sid, existing_mid, current_user_id, messages, ai_session_id)

            return sse_response(lambda: _consume_stream_events(sid, existing_mid, resume=True))

    # 非恢复模式必须提供 prompt
    if not content:
        return jsonify({'success': False, 'message': 'content is required'}), 400

    # 新会话或继续会话
    if not session:
        # 创建新会话
        session = ConversationSession(
            uid=current_user_id,
            title=datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y-%m-%d %H:%M')
        )
        db.session.add(session)
        db.session.flush()
        sid = session.sid

    # 创建 user message 和 assistant 占位，并立即提交，避免长连接导致事务回滚
    user_msg = Message(sid=sid, role='user', content=content)
    assistant_msg = Message(sid=sid, role='assistant', content='')
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.add_all([user_msg, assistant_msg])
    db.session.flush()  # 先拿到 mid
    assistant_mid = assistant_msg.mid
    db.session.commit()  # 先落盘，保证 session/user/assistant 占位可见

    # 构建消息列表（排除当前 assistant 空占位）
    # 对于现有 ai_session 的会话，无需获取历史 message，恢复 1h 内的 session 只需要 prompt，或初始化 session
    messages = build_messages(sid, exclude_mid=assistant_mid) \
        if not ai_session_id and existing_session \
        else [{"role": "user", "content": content}]

    # print(existing_session, messages)

    # 初始化 Redis Stream 运行时并启动唯一生产者。
    set_stream_mid(sid, assistant_mid)
    init_stream_runtime(assistant_mid)
    _ensure_stream_producer(app_obj, sid, assistant_mid, current_user_id, messages, ai_session_id)

    return sse_response(lambda: _consume_stream_events(sid, assistant_mid, resume=False))
