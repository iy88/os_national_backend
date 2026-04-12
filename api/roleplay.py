import json
import threading
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, Response, stream_with_context, current_app

from config import Config
from models import db, RoleplayCharacter, RoleplayCharacterDetail, RoleplaySession, RoleplayMessage
from utils.ai_provider import get_ai_provider, InvalidAISessionError
from utils.jwt_utils import token_required
from utils.redis_client import (
    get_rp_stream_mid,
    set_rp_stream_mid,
    clear_rp_stream_mid,
    append_rp_stream_content,
    get_rp_stream_content,
    clear_rp_stream,
    clear_rp_stream_runtime,
    init_rp_stream_runtime,
    append_rp_stream_event,
    read_rp_stream_events,
    get_rp_stream_last_event_id,
    set_rp_stream_state,
    get_rp_stream_state,
    acquire_rp_stream_producer_lock,
    refresh_rp_stream_producer_lock,
    get_rp_stream_producer_lock,
    release_rp_stream_producer_lock,
    get_rp_ai_session_id,
    set_rp_ai_session_id,
    clear_rp_ai_session_id,
)

roleplay_bp = Blueprint('roleplay', __name__, url_prefix='/agent/roleplay')


def sse_response(generator_func):
    """统一构建 SSE Response"""
    response = Response(stream_with_context(generator_func()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'
    return response


def _build_system_prompt(character: RoleplayCharacter, detail: RoleplayCharacterDetail) -> str:
    """构建角色 system prompt"""
    bio = detail.bio if detail and detail.bio else ''
    phrases = []
    if detail and detail.phrases:
        try:
            phrases = json.loads(detail.phrases)
        except (json.JSONDecodeError, TypeError):
            phrases = []

    prompt_parts = []
    if bio:
        prompt_parts.append(f"角色简介：{bio}")
    if phrases:
        prompt_parts.append(f"角色名言/短语：{' '.join(phrases)}")

    base = f"你正在扮演角色【{character.name}】。"
    if prompt_parts:
        base += " " + " ".join(prompt_parts)
    base += "\n请始终保持角色特性进行对话。"
    return base


def _build_messages(uid: int, rid: int, exclude_mid: int | None = None) -> list:
    """从数据库加载会话历史，构建消息列表"""
    query = RoleplayMessage.query.filter_by(uid=uid, rid=rid)
    if exclude_mid is not None:
        query = query.filter(RoleplayMessage.mid != exclude_mid)
    messages = query.order_by(RoleplayMessage.mid).all()
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def _remove_empty_assistant_message(uid: int, rid: int, mid: int):
    """异常时清理空 assistant 占位"""
    try:
        msg = RoleplayMessage.query.filter_by(mid=mid, uid=uid, rid=rid, role='assistant').first()
        if not msg:
            return
        if (msg.content or '').strip():
            return
        db.session.delete(msg)
        session_row = RoleplaySession.query.filter_by(uid=uid, rid=rid).first()
        if session_row:
            session_row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        print(f"Removed empty roleplay assistant message uid={uid}, rid={rid}, mid={mid}")
    except Exception as cleanup_err:
        db.session.rollback()
        print(f"Failed to remove empty roleplay assistant message uid={uid}, rid={rid}, mid={mid}: {cleanup_err}")


def _persist_assistant_message(uid: int, rid: int, mid: int, full_content: str):
    msg = RoleplayMessage.query.filter_by(mid=mid, uid=uid, rid=rid).first()
    if not msg:
        raise RuntimeError('Roleplay assistant placeholder not found')
    msg.content = full_content

    session_row = RoleplaySession.query.filter_by(uid=uid, rid=rid).first()
    if not session_row:
        raise RuntimeError('Roleplay session not found while persisting stream result')
    session_row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.session.commit()


def _build_error_content(err: Exception, generation_error: bool) -> str:
    """构建错误消息"""
    raw = str(err).strip()
    if generation_error:
        return raw or '生成失败，请稍后重试。'
    return '系统内部错误，请稍后重试。'


def _finalize_error_result(uid: int, rid: int, mid: int, err: Exception, generation_error: bool):
    """错误收敛：落盘错误消息，并通过事件流通知前端 error"""
    error_content = _build_error_content(err, generation_error)

    db.session.rollback()
    try:
        _persist_assistant_message(uid, rid, mid, error_content)
    except Exception:
        db.session.rollback()
        _remove_empty_assistant_message(uid, rid, mid)

    append_rp_stream_event(mid, 'error', message=error_content)
    set_rp_stream_state(mid, 'error', message=error_content)


def _run_stream_producer(
    app,
    uid: int,
    rid: int,
    mid: int,
    base_messages: list,
    app_id: str,
    ai_session_id: str | None = None,
    fallback_messages: list | None = None
):
    """后台生产者：唯一拉取 LLM 流并写入 Redis Stream 事件"""
    with app.app_context():
        ai_provider = get_ai_provider(
            Config.AI_PROVIDER,
            Config.AI_API_KEY,
            app_id=app_id
        )

        set_rp_stream_state(mid, 'running')
        refresh_rp_stream_producer_lock(uid, rid)

        def produce(active_messages: list, active_session_id: str | None, is_resume: bool = False):
            for chunk in ai_provider.chat_stream(active_messages, sid=mid, resume=is_resume, session_id=active_session_id):
                append_rp_stream_content(mid, chunk)
                append_rp_stream_event(mid, 'content', content=chunk)
                refresh_rp_stream_producer_lock(uid, rid)

        try:
            try:
                is_resume = ai_session_id is not None
                produce(base_messages, ai_session_id, is_resume)
            except InvalidAISessionError as invalid_session_err:
                print(f"Invalid roleplay AI session_id detected uid={uid}, rid={rid}: {invalid_session_err}")
                clear_rp_ai_session_id(uid, rid)
                recover_messages = fallback_messages if fallback_messages is not None else base_messages
                produce(recover_messages, None, False)
            except Exception as gen_err:
                if ai_session_id and fallback_messages is not None:
                    print(
                        f"Roleplay AI generation failed with cached session uid={uid}, rid={rid}, "
                        f"mid={mid}, fallback to full messages: {gen_err}"
                    )
                    clear_rp_ai_session_id(uid, rid)
                    try:
                        produce(fallback_messages, None, False)
                    except Exception as fallback_err:
                        print(
                            f"Roleplay AI fallback generation error uid={uid}, rid={rid}, "
                            f"mid={mid}: {fallback_err}"
                        )
                        _finalize_error_result(uid, rid, mid, fallback_err, generation_error=True)
                        return
                else:
                    print(f"Roleplay AI generation error uid={uid}, rid={rid}, mid={mid}: {gen_err}")
                    _finalize_error_result(uid, rid, mid, gen_err, generation_error=True)
                    return

            full_content = get_rp_stream_content(mid)
            try:
                _persist_assistant_message(uid, rid, mid, full_content)
            except Exception as persist_err:
                print(f"Persist roleplay assistant content failed uid={uid}, rid={rid}, mid={mid}: {persist_err}")
                _finalize_error_result(uid, rid, mid, persist_err, generation_error=False)
                return

            new_ai_session_id = ai_provider.get_last_session_id()
            if new_ai_session_id:
                set_rp_ai_session_id(uid, rid, new_ai_session_id)

            append_rp_stream_event(mid, 'done')
            set_rp_stream_state(mid, 'done')
        except Exception as e:
            print(f"Roleplay streaming internal error uid={uid}, rid={rid}, mid={mid}: {e}")
            _finalize_error_result(uid, rid, mid, e, generation_error=False)
        finally:
            try:
                clear_rp_stream_mid(uid, rid)
            except Exception as cleanup_err:
                print(f"Clear roleplay stream marker failed uid={uid}, rid={rid}, mid={mid}: {cleanup_err}")
            finally:
                release_rp_stream_producer_lock(uid, rid)


def _ensure_stream_producer(
    app,
    uid: int,
    rid: int,
    mid: int,
    messages: list,
    app_id: str,
    ai_session_id: str | None = None,
    fallback_messages: list | None = None
):
    """确保同一个 uid/rid/mid 只有一个生产者"""
    lock_mid = get_rp_stream_producer_lock(uid, rid)
    if lock_mid == str(mid):
        return

    if not acquire_rp_stream_producer_lock(uid, rid, mid):
        return

    producer = threading.Thread(
        target=_run_stream_producer,
        args=(app, uid, rid, mid, messages, app_id, ai_session_id, fallback_messages),
        daemon=True
    )
    producer.start()


def _consume_stream_events(uid: int, rid: int, mid: int, resume: bool = False):
    """SSE 消费者：回放已有事件并实时追尾新增事件"""
    should_cleanup_runtime = False
    start_data = {'type': 'start', 'uid': uid, 'rid': rid, 'mid': mid}
    if resume:
        start_data['resume'] = True
    try:
        yield f"data: {json.dumps(start_data)}\n\n"

        last_id = '0-0'
        idle_rounds = 0

        if resume:
            cached_content = get_rp_stream_content(mid)
            if cached_content:
                yield f"data: {json.dumps({'type': 'catchup', 'content': cached_content})}\n\n"

            stream_last_id = get_rp_stream_last_event_id(mid)
            if stream_last_id:
                last_id = stream_last_id

        while True:
            try:
                events = read_rp_stream_events(mid, last_id=last_id, block_ms=5000, count=200)
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
                        yield f"data: {json.dumps({'type': 'done', 'uid': uid, 'rid': rid, 'mid': mid})}\n\n"
                        return
                    elif event_type == 'error':
                        should_cleanup_runtime = True
                        yield f"data: {json.dumps({'type': 'error', 'message': fields.get('message', 'Unknown error')})}\n\n"
                        yield f"data: {json.dumps({'type': 'done', 'uid': uid, 'rid': rid, 'mid': mid})}\n\n"
                        return
                continue

            idle_rounds += 1
            state = get_rp_stream_state(mid)
            stream_state = state.get('state')
            if stream_state == 'done':
                should_cleanup_runtime = True
                yield f"data: {json.dumps({'type': 'done', 'uid': uid, 'rid': rid, 'mid': mid})}\n\n"
                return
            if stream_state == 'error':
                should_cleanup_runtime = True
                yield f"data: {json.dumps({'type': 'error', 'message': state.get('message', 'Unknown error')})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'uid': uid, 'rid': rid, 'mid': mid})}\n\n"
                return

            if idle_rounds >= 24:
                should_cleanup_runtime = True
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream timeout waiting for producer'})}\n\n"
                return

            yield ': ping\n\n'
    finally:
        if should_cleanup_runtime:
            try:
                clear_rp_stream_runtime(mid)
            except Exception as cleanup_err:
                print(f"Clear roleplay stream runtime failed mid={mid}: {cleanup_err}")


@roleplay_bp.route('/list/<type>', methods=['GET'])
@token_required
def list_characters(current_user_id, type):
    """列出指定 type 的角色列表（不含详情）"""
    if type not in Config.ROLEPLAY_APP_ID_MAP:
        return jsonify({'success': False, 'message': 'Invalid character type'}), 400

    characters = RoleplayCharacter.query.filter_by(type=type).all()
    result = [{
        'rid': c.rid,
        'name': c.name,
        'avatarId': c.avatar_id,
        'createdAt': c.created_at.isoformat() + 'Z' if c.created_at else None
    } for c in characters]

    return jsonify({
        'success': True,
        'characters': result
    })


@roleplay_bp.route('/detail/<int:rid>', methods=['GET'])
@token_required
def get_character_detail(current_user_id, rid):
    """获取角色详情"""
    character = RoleplayCharacter.query.get(rid)
    if not character:
        return jsonify({'success': False, 'message': 'Character not found'}), 404

    detail = RoleplayCharacterDetail.query.get(rid)
    phrases = []
    if detail and detail.phrases:
        try:
            phrases = json.loads(detail.phrases)
        except (json.JSONDecodeError, TypeError):
            phrases = []

    return jsonify({
        'success': True,
        'character': {
            'rid': character.rid,
            'type': character.type,
            'name': character.name,
            'avatarId': character.avatar_id,
            'bio': detail.bio if detail else None,
            'phrases': phrases,
            'detailAvatarId': detail.avatar_id if detail else None,
            'updatedAt': detail.updated_at.isoformat() + 'Z' if detail and detail.updated_at else None,
            'createdAt': character.created_at.isoformat() + 'Z' if character.created_at else None
        }
    })


@roleplay_bp.route('/message/send/<int:rid>', methods=['POST'])
@token_required
def send_message(current_user_id, rid):
    """
    向角色发送消息，SSE 流式响应

    请求体:
        content: str - 消息内容（重生成模式可不传）
        regenerateMid: int (可选) - 重生成的 assistant 消息 ID，传了此参数则进入重生成模式
    """
    character = RoleplayCharacter.query.get(rid)
    if not character:
        return jsonify({'success': False, 'message': 'Character not found'}), 404

    detail = RoleplayCharacterDetail.query.get(rid)
    system_prompt = _build_system_prompt(character, detail)

    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    regenerate_mid = data.get('regenerateMid')

    app_id = Config.ROLEPLAY_APP_ID_MAP.get(character.type)
    if not app_id:
        return jsonify({'success': False, 'message': 'Character type not configured'}), 500

    ai_session_id = get_rp_ai_session_id(current_user_id, rid)

    # noinspection PyUnresolvedReferences,PyProtectedMember
    app_obj = current_app._get_current_object()

    # ========== 重生成模式 ==========
    if regenerate_mid is not None:
        # 1. 验证 regenerateMid
        old_msg = RoleplayMessage.query.filter_by(
            mid=regenerate_mid,
            uid=current_user_id,
            rid=rid,
            role='assistant'
        ).first()
        if not old_msg:
            return jsonify({'success': False, 'message': 'Message not found or not assistant'}), 404

        # 2. 删除旧的 assistant 消息
        db.session.delete(old_msg)
        db.session.flush()

        # 3. 创建新的 assistant 占位
        assistant_msg = RoleplayMessage(uid=current_user_id, rid=rid, role='assistant', content='')
        session = RoleplaySession.query.filter_by(uid=current_user_id, rid=rid).first()
        if not session:
            session = RoleplaySession(uid=current_user_id, rid=rid)
            db.session.add(session)
            db.session.flush()
        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.add(assistant_msg)
        db.session.flush()
        assistant_mid = assistant_msg.mid
        db.session.commit()

        # 4. 构建完整消息列表（排除新 assistant 占位），prepend system prompt
        messages = [{"role": "system", "content": system_prompt}] + _build_messages(
            current_user_id,
            rid,
            exclude_mid=assistant_mid
        )

        set_rp_stream_mid(current_user_id, rid, assistant_mid)
        init_rp_stream_runtime(assistant_mid)
        _ensure_stream_producer(
            app_obj,
            current_user_id,
            rid,
            assistant_mid,
            messages,
            app_id,
            ai_session_id=None,
            fallback_messages=None
        )

        return sse_response(lambda: _consume_stream_events(current_user_id, rid, assistant_mid, resume=False))

    # 检查是否有进行中的流（恢复模式）
    existing_mid = get_rp_stream_mid(current_user_id, rid)
    if existing_mid:
        state = get_rp_stream_state(existing_mid)
        lock_mid = get_rp_stream_producer_lock(current_user_id, rid)
        has_runtime = bool(get_rp_stream_content(existing_mid)) or bool(state)

        if not has_runtime and lock_mid != str(existing_mid):
            clear_rp_stream(current_user_id, rid, existing_mid)
            clear_rp_stream_runtime(existing_mid)
        else:
            if lock_mid != str(existing_mid) and state.get('state') == 'running':
                messages = [{"role": "system", "content": system_prompt}] + _build_messages(current_user_id, rid, exclude_mid=existing_mid)
                _ensure_stream_producer(
                    app_obj,
                    current_user_id,
                    rid,
                    existing_mid,
                    messages,
                    app_id,
                    ai_session_id=ai_session_id,
                    fallback_messages=messages if ai_session_id else None
                )

            return sse_response(lambda: _consume_stream_events(current_user_id, rid, existing_mid, resume=True))

    # 非恢复模式必须提供 prompt
    if not content:
        return jsonify({'success': False, 'message': 'content is required'}), 400

    # 查找或创建 session
    session = RoleplaySession.query.filter_by(uid=current_user_id, rid=rid).first()
    existing_session = bool(session)
    if not existing_session and ai_session_id:
        clear_rp_ai_session_id(current_user_id, rid)
        ai_session_id = None
    if not session:
        session = RoleplaySession(uid=current_user_id, rid=rid)
        db.session.add(session)
        db.session.flush()

    # 创建 user message 和 assistant 占位
    user_msg = RoleplayMessage(uid=current_user_id, rid=rid, role='user', content=content)
    assistant_msg = RoleplayMessage(uid=current_user_id, rid=rid, role='assistant', content='')
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.session.add_all([user_msg, assistant_msg])
    db.session.flush()
    assistant_mid = assistant_msg.mid
    db.session.commit()

    # 构建消息列表（排除当前 assistant 空占位）， prepend system prompt
    full_messages = [{"role": "system", "content": system_prompt}] + _build_messages(
        current_user_id,
        rid,
        exclude_mid=assistant_mid
    )

    # 已有历史会话且 session_id 有效时，仅发送最新用户 prompt；失败时回退全量 messages。
    if existing_session and ai_session_id:
        messages = [{"role": "user", "content": content}]
        fallback_messages = full_messages
    else:
        messages = full_messages
        fallback_messages = None

    # 初始化 Redis Stream 运行时并启动唯一生产者
    set_rp_stream_mid(current_user_id, rid, assistant_mid)
    init_rp_stream_runtime(assistant_mid)
    _ensure_stream_producer(
        app_obj,
        current_user_id,
        rid,
        assistant_mid,
        messages,
        app_id,
        ai_session_id=ai_session_id if existing_session else None,
        fallback_messages=fallback_messages
    )

    return sse_response(lambda: _consume_stream_events(current_user_id, rid, assistant_mid, resume=False))


@roleplay_bp.route('/message/list/<int:rid>', methods=['GET'])
@token_required
def list_messages(current_user_id, rid):
    """列出与角色的所有对话（按时间升序）"""
    character = RoleplayCharacter.query.get(rid)
    if not character:
        return jsonify({'success': False, 'message': 'Character not found'}), 404

    messages = RoleplayMessage.query.filter_by(
        uid=current_user_id, rid=rid
    ).order_by(RoleplayMessage.created_at.asc()).all()

    # 检查是否有进行中的流
    incomplete_mid = get_rp_stream_mid(current_user_id, rid)

    return jsonify({
        'success': True,
        'messages': [{
            'mid': msg.mid,
            'role': msg.role,
            'content': msg.content,
            'createdAt': msg.created_at.isoformat() + 'Z' if msg.created_at else None
        } for msg in messages],
        'incompleteMid': incomplete_mid
    })
