import hashlib
import json
from abc import ABC, abstractmethod
from http import HTTPStatus

import dashscope
import requests
import sseclient
from dashscope import Application, Generation


class InvalidAISessionError(Exception):
    """AI session_id 无效，需要回退到全量历史重建上下文"""


def _is_invalid_session_error(status_code, message: str | None) -> bool:
    if not message:
        return False
    msg = message.lower()
    session_keywords = ['session', 'session_id', 'invalid session', 'session not found', '会话']
    # DashScope 侧通常是 4xx 参数错误，结合 message 文本判定
    return int(status_code) in (400, 401, 404, 422) and any(k in msg for k in session_keywords)


class AIProvider(ABC):
    """AI Provider 抽象基类"""

    @abstractmethod
    def chat_stream(self, messages: list, sid: int, resume: bool = False, session_id: str | None = None):
        """
        流式聊天（generator）

        Args:
            messages: 消息列表 [{"role": "user/assistant", "content": "..."}]
            sid: 会话 ID（强制传入，用于生成确定性上下文标识）
            resume: 是否从当前 active session 恢复（而非新开 session）
            session_id: 可选的 AI 提供商 session_id（DashScope 等使用）

        Yields:
            str: 每次收到的文本片段
        """
        pass

    @abstractmethod
    def chat_stream_resume(self, messages: list, sid: int, completed_content: str = '', session_id: str | None = None):
        """
        从断点继续流式聊天

        Args:
            messages: 消息列表
            sid: 会话 ID
            completed_content: 已经传输完成的内容（用于去重或跳过）
            session_id: AI 提供商 session_id（可选）
        """
        pass

    @abstractmethod
    def get_last_session_id(self) -> str | None:
        """获取最近一次调用返回的 DashScope session_id"""
        pass


# noinspection DuplicatedCode
class DashScopeApplicationProvider(AIProvider):
    """阿里云 DashScope Application API（智能体调用）"""

    def __init__(self, api_key: str, app_id: str):
        self.api_key = api_key
        self.app_id = app_id
        self._last_session_id = None
        dashscope.api_key = api_key

    def chat_stream(self, messages: list, sid: int, resume: bool = False, session_id: str | None = None):
        """
        使用 DashScope Application API 进行流式聊天（generator）

        Args:
            messages: 消息列表，支持 messages 或 prompt
            sid: 会话 ID（DashScope 忽略此参数，但保持接口一致）
            resume: 是否恢复现有 session（DashScope 使用 session_id 判断）
            session_id: DashScope session_id（可选）

        Yields:
            str: 每次收到的文本片段
        """
        self._last_session_id = session_id
        # 构建 prompt（如果只有一条消息，直接用 prompt）
        if len(messages) == 1 and messages[0].get('role') == 'user':
            prompt = messages[0]['content']
            responses = Application.call(
                api_key=self.api_key,
                app_id=self.app_id,
                prompt=prompt,
                session_id=session_id,
                stream=True,
                incremental_output=True
            )
            for response in responses:
                if response.status_code != HTTPStatus.OK:
                    if session_id and _is_invalid_session_error(response.status_code, response.message):
                        raise InvalidAISessionError(
                            f'Invalid AI session_id: code={response.status_code}, message={response.message}'
                        )
                    raise Exception(f'API error: code={response.status_code}, message={response.message}')
                if response.output and getattr(response.output, 'session_id', None):
                    self._last_session_id = response.output.session_id
                if response.output and response.output.text:
                    yield response.output.text
        else:
            # 多轮对话恢复使用 messages 参数
            responses = Application.call(
                api_key=self.api_key,
                app_id=self.app_id,
                messages=messages,
                stream=True,
                incremental_output=True
            )
            for response in responses:
                if response.status_code != HTTPStatus.OK:
                    if session_id and _is_invalid_session_error(response.status_code, response.message):
                        raise InvalidAISessionError(
                            f'Invalid AI session_id: code={response.status_code}, message={response.message}'
                        )
                    raise Exception(f'API error: code={response.status_code}, message={response.message}')
                if response.output and getattr(response.output, 'session_id', None):
                    self._last_session_id = response.output.session_id
                if response.output and response.output.text:
                    yield response.output.text

    def chat_stream_resume(self, messages: list, sid: int, completed_content: str = '', session_id: str | None = None):
        # DashScope 不支持真正断点续传：带上 session_id 重新发起流式请求
        yield from self.chat_stream(messages, sid=sid, resume=True, session_id=session_id)

    def get_last_session_id(self) -> str | None:
        return self._last_session_id


class DashScopeGenerationProvider(AIProvider):
    """阿里云 DashScope Generation API（模型调用）"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        dashscope.api_key = api_key

    def chat_stream(self, messages: list, sid: int, resume: bool = False, session_id: str | None = None):
        """
        使用 DashScope Generation API 进行流式聊天

        Args:
            messages: 消息列表
            sid: 会话 ID（Generation API 忽略此参数）
            resume: 是否恢复（Generation API 忽略此参数）
            session_id: 可选 session_id（Generation API 忽略此参数）

        Yields:
            str: 每次收到的文本片段
        """
        responses = Generation.call(
            api_key=self.api_key,
            model=self.model,
            messages=messages,
            result_format='message',
            stream=True,
            incremental_output=True,
            enable_search=False,
            enable_thinking=False
        )
        for response in responses:
            if response.status_code != HTTPStatus.OK:
                raise Exception(f'API error: code={response.status_code}, message={response.message}')
            if response.output and response.output.choices:
                for choice in response.output.choices:
                    if choice.message and choice.message.content:
                        yield choice.message.content

    def chat_non_stream(self, messages: list) -> str:
        """非流式调用，直接返回完整响应内容"""
        response = Generation.call(
            api_key=self.api_key,
            model=self.model,
            messages=messages,
            result_format='message',
            enable_search=False,
            enable_thinking=False
        )
        if response.status_code != HTTPStatus.OK:
            raise Exception(f'API error: code={response.status_code}, message={response.message}')
        if response.output and response.output.choices:
            return response.output.choices[0].message.content
        return ''

    def chat_stream_resume(self, messages: list, sid: int, completed_content: str = '', session_id: str | None = None):
        yield from self.chat_stream(messages, sid=sid, resume=True, session_id=None)

    def get_last_session_id(self) -> str | None:
        return None


def _generate_conversation_id(session_id: str) -> str:
    """从 session_id 生成确定性的 conversationId (MD5)"""
    return hashlib.md5(session_id.encode('utf-8')).hexdigest()


def _extract_last_user_message(messages: list) -> str:
    """从消息列表提取最后一条用户消息"""
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            return msg.get('content', '')
    return ''


class TencentADPProvider(AIProvider):
    """腾讯云 ADP (Application Dialogue Platform) AI Provider

    ADP 智能体对话平台，支持 conversationId 复用 180 天上下文。
    使用 SSE 流式协议，只处理 text.delta 事件。
    sid 用于生成确定性的 conversationId（MD5），保持数据结构一致。
    """

    def __init__(self, app_key: str, visitor_id: str = 'visitor_os_national',
                 url: str = 'https://wss.lke.cloud.tencent.com/adp/v2/chat'):
        self.app_key = app_key
        self.visitor_id = visitor_id
        self.url = url
        self._last_conversation_id = None

    @staticmethod
    def _generate_conversation_id(sid: int) -> str:
        """从 sid 生成确定性的 conversationId (MD5)"""
        return hashlib.md5(str(sid).encode('utf-8')).hexdigest()

    @staticmethod
    def _extract_last_user_message(messages: list) -> str:
        """从消息列表提取最后一条用户消息"""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                return msg.get('content', '')
        return ''

    @staticmethod
    def _extract_system_prompt(messages: list) -> str | None:
        """从消息列表提取第一条 system prompt"""
        for msg in messages:
            if msg.get('role') == 'system':
                return msg.get('content')
        return None

    def chat_stream(self, messages: list, sid: int, resume: bool = False, session_id: str | None = None):
        """
        使用腾讯云 ADP API 进行流式聊天

        Args:
            messages: 消息列表
            sid: 会话 ID（强制），用于生成确定性的 conversationId
            resume: 是否从当前 active session 恢复（复用现有 conversationId）
            session_id: 被忽略（ADP 不使用此参数，保持接口一致）

        Yields:
            str: 每次收到的文本片段
        """
        # 生成确定性的 conversationId
        conversation_id = self._generate_conversation_id(sid)
        self._last_conversation_id = conversation_id

        # 提取 system prompt（用于 roleplay 场景）
        system_prompt = self._extract_system_prompt(messages)
        # 提取最后一条用户消息
        text = self._extract_last_user_message(messages)

        # 构建 Contents：如果是新会话且有 system prompt，则分两条
        contents = []
        if not resume and system_prompt:
            contents.append({'Type': 'text', 'Text': system_prompt})
        contents.append({'Type': 'text', 'Text': text})

        # print(contents)

        # 构建 ADP 请求体
        payload = {
            'ConversationId': conversation_id,
            'AppKey': self.app_key,
            'Contents': contents,
            'VisitorId': self.visitor_id,
            'Incremental': True,
            'EnableMultiIntent': True,
            'Stream': 'enable'
        }

        # 发送 SSE 请求
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            self.url,
            json=payload,
            headers=headers,
            stream=True
        )

        if response.status_code != HTTPStatus.OK:
            raise Exception(f'ADP API error: code={response.status_code}, body={response.text}')

        # 解析 SSE 流
        # 用于跟踪消息类型（过滤 thought 消息）
        message_types = {}  # message_id -> type (thought/reply)

        client = sseclient.SSEClient(response)
        for event in client.events():
            if not event.data:
                continue

            try:
                data = json.loads(event.data)
            except json.JSONDecodeError:
                continue

            event_type = data.get('Type', '')

            # 记录消息类型：message.added 事件包含 Type 字段标识 thought/reply
            # ADP 格式: {"Type":"message.added","Message":{"Type":"thought",...}}
            if event_type == 'message.added':
                msg = data.get('Message', {})
                msg_id = msg.get('MessageId', '')
                msg_type = msg.get('Type', '')
                if msg_id and msg_type:
                    message_types[msg_id] = msg_type
                continue

            # 只处理 text.delta 事件，并过滤掉 thought 类型的消息
            # ADP 格式: {"Type":"text.delta","MessageId":"...","Text":"内容"}
            if event_type == 'text.delta':
                msg_id = data.get('MessageId', '')
                # 跳过 thought 类型的消息（思考过程）
                if message_types.get(msg_id) == 'thought':
                    continue
                content = data.get('Text', '')
                if content:
                    yield content

    def chat_stream_resume(self, messages: list, sid: int, completed_content: str = '', session_id: str | None = None):
        """
        从断点继续流式聊天（ADP 不支持真正断点续传，重新发起请求）
        """
        yield from self.chat_stream(messages, sid=sid, resume=True, session_id=session_id)

    def get_last_session_id(self) -> str | None:
        """返回 conversation_id 以保持接口一致性（数据结构不变）"""
        return self._last_conversation_id


class TencentADPGenerationProvider(AIProvider):
    """腾讯云 MaaS (Model as a Service) Generation Provider

    使用 OpenAI 兼容 API 调用腾讯云的模型服务。
    base_url: https://tokenhub.tencentmaas.com/v1
    """

    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url='https://tokenhub.tencentmaas.com/v1'
        )

    def chat_stream(self, messages: list, sid: int, resume: bool = False, session_id: str | None = None):
        """
        使用腾讯云 MaaS API 进行流式聊天

        Args:
            messages: 消息列表
            sid: 会话 ID（MaaS API 忽略此参数）
            resume: 是否恢复（MaaS API 忽略此参数）
            session_id: 可选 session_id（MaaS API 忽略此参数）

        Yields:
            str: 每次收到的文本片段
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_non_stream(self, messages: list) -> str:
        """非流式调用，直接返回完整响应内容"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=False
        )
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        return ''

    def chat_stream_resume(self, messages: list, sid: int, completed_content: str = '', session_id: str | None = None):
        yield from self.chat_stream(messages, sid=sid, resume=True, session_id=None)

    def get_last_session_id(self) -> str | None:
        return None


class TencentYuanqiProvider(AIProvider):
    """腾讯元器 AI Provider。流式 SSE，每次发送完整 messages（无 session 缓存）。

    接口：https://yuanqi.tencent.com/openapi/v1/agent/chat/completions
    - Auth: Authorization: Bearer <appkey>
    - Body: assistant_id, user_id, stream, messages[]
    - messages[].content 是 [{type, text}] 列表（OpenAI 风格，无 system role）
    - 流式: SSE data: {json}, 终止 data: [DONE]
    - 无 session_id 概念 —— 每次必须发送完整历史
    """

    BASE_URL = 'https://yuanqi.tencent.com/openapi/v1/agent/chat/completions'

    def __init__(self, api_key: str, assistant_id: str):
        self.api_key = api_key
        self.assistant_id = assistant_id
        self._last_session_id = None  # 保留字段以满足接口；Yuanqi 不支持 session

    def chat_stream(self, messages: list, sid: int, resume: bool = False, session_id: str | None = None):
        body = {
            'assistant_id': self.assistant_id,
            'user_id': f'user_{sid}',
            'stream': True,
            'messages': self._convert_messages(messages),
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        with requests.post(
            self.BASE_URL, headers=headers, json=body, stream=True, timeout=120
        ) as resp:
            if resp.status_code != 200:
                raise Exception(
                    f'Yuanqi API error {resp.status_code}: {resp.text[:300]}'
                )
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8') if isinstance(line, bytes) else line
                if not line.startswith('data: '):
                    continue
                data_str = line[6:]
                if data_str.strip() == '[DONE]':
                    break
                try:
                    evt = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                for choice in evt.get('choices', []):
                    delta = choice.get('delta') or {}
                    content = delta.get('content')
                    if content:
                        yield content
                    # tool_calls 不单独 yield —— 工具结果在后续 step
                    # 以 assistant content 形式回来

    def chat_stream_resume(self, messages: list, sid: int, completed_content: str = '',
                           session_id: str | None = None):
        # Yuanqi 无 session —— 重新流式全量 history；completed_content 忽略
        yield from self.chat_stream(messages, sid=sid, resume=True, session_id=None)

    def get_last_session_id(self) -> str | None:
        return None

    def _convert_messages(self, messages: list) -> list:
        """[{role, content_str}] → Yuanqi [{role, content: [{type, text}]}]。
        Yuanqi 无 system role，system prompt 拼到第一条 user 消息前。
        """
        converted = []
        sys_prefix = None
        for m in messages:
            if m.get('role') == 'system':
                sys_prefix = m.get('content', '')
                continue
            converted.append({
                'role': m['role'],
                'content': [{'type': 'text', 'text': m.get('content', '')}]
            })
        if sys_prefix and converted and converted[0]['role'] == 'user':
            converted[0]['content'].insert(0, {'type': 'text', 'text': f'[系统设定] {sys_prefix}'})
        return converted


def get_ai_provider(provider_name: str, api_key: str, app_id: str = None, model: str = None) -> AIProvider:
    """
    工厂函数，获取 AI Provider 实例

    Args:
        provider_name: provider 名称 (dashscope / tencent_adp / tencent_yuanqi)
        api_key: API 密钥（DashScope / Tencent MaaS / Yuanqi 需要；Yuanqi 分支
                会从 Config.YUANQI_API_KEY 重新读取，忽略此参数）
        app_id: APP ID（DashScope / ADP Agent / Yuanqi assistant_id）
        model: 模型名称（DashScope Generation / MaaS 需要；Yuanqi 不支持）

    Returns:
        AIProvider 实例
    """
    if provider_name == 'dashscope':
        if app_id:
            return DashScopeApplicationProvider(api_key, app_id)
        elif model:
            return DashScopeGenerationProvider(api_key, model)
        else:
            raise ValueError('DashScope provider requires app_id or model')
    elif provider_name == 'tencent_adp':
        if app_id:
            return TencentADPProvider(app_key=app_id)
        elif model:
            return TencentADPGenerationProvider(api_key, model)
        else:
            raise ValueError('Tencent ADP provider requires app_id or model')
    elif provider_name == 'tencent_yuanqi':
        if not app_id:
            raise ValueError('tencent_yuanqi provider requires app_id (assistant_id)')
        return TencentYuanqiProvider(api_key=api_key, assistant_id=app_id)
    else:
        raise ValueError(f'Unknown AI provider: {provider_name}')
