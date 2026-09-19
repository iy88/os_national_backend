import json
import os
from datetime import datetime

import requests

# token 从环境变量读取，不要把真实凭据写进仓库
# 取值：调用登录接口，复制响应中的 token 字段
TOKEN = os.getenv("TEST_TOKEN")
if not TOKEN:
    raise SystemExit("请先设置环境变量 TEST_TOKEN")

URL = "http://127.0.0.1:8080/agent/travel-route-plan/message"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

LONG_PROMPT = '''【电竞文旅规划请求】
目标城市：西安
旅行天数：3天
出行人数：2人
关系类型：情侣出游
本命英雄：李白

【用户需求】
我想要一个简短的行程
'''


def log(msg: str):
    print(f"[{datetime.now()}] {msg}")


def post_stream(content: str | None = None, sid: int | None = None):
    payload = {}
    if content is not None:
        payload["content"] = content
    if sid is not None:
        payload["sid"] = sid
    return requests.post(URL, headers=HEADERS, json=payload, stream=True, timeout=(10, 300))


def iter_sse_events(response):
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        if not raw_line.startswith("data: "):
            continue
        data_str = raw_line[6:]
        try:
            event = json.loads(data_str)
        except json.JSONDecodeError:
            log(f"Skip invalid json line: {raw_line}")
            continue
        yield event


def start_and_interrupt() -> tuple[int, int, str]:
    """发起首轮请求，读取部分内容后主动中断，制造可恢复场景。"""
    log("Step1: start stream and interrupt after partial chunks")
    response = post_stream(LONG_PROMPT)
    log(f"Step1 status={response.status_code}")
    if response.status_code != 200:
        raise RuntimeError(f"Step1 failed status={response.status_code}")

    sid = None
    mid = None
    partial = []

    try:
        for event in iter_sse_events(response):
            log(f"Step1 event={event.get('type')}")

            if event.get("type") == "start":
                sid = event.get("sid")
                mid = event.get("mid")
            elif event.get("type") == "content":
                partial.append(event.get("content", ""))
                # 读到一定内容后主动断开
                if len(partial) >= 8:
                    log("Step1 interrupt stream intentionally")
                    break
            elif event.get("type") == "error":
                raise RuntimeError(f"Step1 SSE error: {event}")
    finally:
        response.close()

    if sid is None or mid is None:
        raise RuntimeError("Step1 did not receive start event with sid/mid")

    partial_text = "".join(partial)
    log(f"Step1 got sid={sid}, mid={mid}, partial_len={len(partial_text)}")
    return sid, mid, partial_text


def resume_stream(sid: int):
    """对同一个 sid 再次请求，期望触发 resume。"""
    log(f"Step2: resume stream with sid={sid}")
    response = post_stream(sid=sid)
    log(f"Step2 status={response.status_code}")
    if response.status_code != 200:
        raise RuntimeError(f"Step2 failed status={response.status_code}")

    resume_flag = False
    done_flag = False
    content_count = 0
    content_len = 0

    try:
        for event in iter_sse_events(response):
            et = event.get("type")
            log(f"Step2 event={et}")
            if et == "start":
                resume_flag = bool(event.get("resume"))
                log(f"Step2 start resume={resume_flag}, sid={event.get('sid')}, mid={event.get('mid')}")
            elif et == "content":
                chunk = event.get("content", "")
                content_count += 1
                content_len += len(chunk)
                # log(f"Step2 content={chunk}")
            elif et == "done":
                done_flag = True
                log("Step2 done")
                break
            elif et == "error":
                raise RuntimeError(f"Step2 SSE error: {event}")
    finally:
        response.close()

    log(f"Step2 content_count={content_count}, content_len={content_len}")
    if not done_flag:
        raise RuntimeError("Step2 did not receive done event")

    return resume_flag, content_count, content_len


def follow_up_turn(sid: int):
    """验证恢复结束后，同会话还能继续正常流式对话。"""
    log(f"Step3: normal follow-up turn with sid={sid}")
    response = post_stream("基于上面的规划，再给我一个预算更省的版本。", sid=sid)
    log(f"Step3 status={response.status_code}")
    if response.status_code != 200:
        raise RuntimeError(f"Step3 failed status={response.status_code}")

    done_flag = False
    content_count = 0
    content_len = 0
    try:
        for event in iter_sse_events(response):
            et = event.get("type")
            log(f"Step3 event={et}")
            if et == "content":
                chunk = event.get("content", "")
                content_count += 1
                content_len += len(chunk)
                # log(f"Step3 content={chunk}")
            elif et == "done":
                done_flag = True
                log("Step3 done")
                break
            elif et == "error":
                raise RuntimeError(f"Step3 SSE error: {event}")
    finally:
        response.close()

    if not done_flag:
        raise RuntimeError("Step3 did not receive done event")
    log(f"Step3 content_count={content_count}, content_len={content_len}")


if __name__ == '__main__':
    log("Session resume test started")
    sid_val, mid_val, partial_text_val = start_and_interrupt()
    resume_ok, resume_chunks, resume_len = resume_stream(sid_val)
    follow_up_turn(sid_val)

    print("\n========== TEST SUMMARY ==========")
    print(f"sid={sid_val}, interrupted_mid={mid_val}")
    print(f"step1_partial_len={len(partial_text_val)}")
    print(f"step2_resume_flag={resume_ok}")
    print(f"step2_content_chunks={resume_chunks}, step2_content_len={resume_len}")
    print("step3_follow_up=ok")
    print("==================================")
