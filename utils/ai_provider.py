from abc import ABC, abstractmethod
from http import HTTPStatus

import dashscope
from dashscope import Application


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
    def chat_stream(self, messages: list, session_id: str | None = None):
        """
        流式聊天（generator）

        Args:
            messages: 消息列表 [{"role": "user/assistant", "content": "..."}]

        Yields:
            str: 每次收到的文本片段
        """
        pass

    @abstractmethod
    def chat_stream_resume(self, messages: list, completed_content: str = '', session_id: str | None = None):
        """
        从断点继续流式聊天

        Args:
            messages: 消息列表
            completed_content: 已经传输完成的内容（用于去重或跳过）
        """
        pass

    @abstractmethod
    def get_last_session_id(self) -> str | None:
        """获取最近一次调用返回的 DashScope session_id"""
        pass


class DashScopeProvider(AIProvider):
    """阿里云 DashScope AI Provider"""

    def __init__(self, api_key: str, app_id: str):
        self.api_key = api_key
        self.app_id = app_id
        self._last_session_id = None
        dashscope.api_key = api_key

    def chat_stream(self, messages: list, session_id: str | None = None):
        """
        使用 DashScope Application API 进行流式聊天（generator）

        Args:
            messages: 消息列表，支持 messages 或 prompt

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
            # 多轮对话使用 messages 参数
            # 将 messages 转换为 DashScope 格式
            dashscope_messages = []
            for msg in messages:
                if msg['role'] == 'user':
                    dashscope_messages.append({
                        'role': 'user',
                        'content': msg['content']
                    })
                elif msg['role'] == 'assistant':
                    dashscope_messages.append({
                        'role': 'assistant',
                        'content': msg['content']
                    })
                elif msg['role'] == 'system':
                    dashscope_messages.append({
                        'role': 'system',
                        'content': msg['content']
                    })

            responses = Application.call(
                api_key=self.api_key,
                app_id=self.app_id,
                prompt=messages[-1]['content'] if messages else '',
                messages=dashscope_messages[:-1] if len(dashscope_messages) > 1 else None,
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

    def chat_stream_resume(self, messages: list, completed_content: str = '', session_id: str | None = None):
        # DashScope 不支持真正断点续传：带上 session_id 重新发起流式请求
        yield from self.chat_stream(messages, session_id=session_id)

    def get_last_session_id(self) -> str | None:
        return self._last_session_id


class YuanqiProvider(AIProvider):
    """元器平台 AI Provider（占位实现）"""

    def __init__(self, app_id: str, api_key: str):
        self.app_id = app_id
        self.api_key = api_key

    def chat_stream(self, messages: list, session_id: str | None = None):
        raise NotImplementedError('Yuanqi provider not yet implemented')

    def chat_stream_resume(self, messages: list, completed_content: str = '', session_id: str | None = None):
        raise NotImplementedError('Yuanqi provider not yet implemented')

    def get_last_session_id(self) -> str | None:
        return None


def get_ai_provider(provider_name: str, api_key: str, app_id: str = None) -> AIProvider:
    """
    工厂函数，获取 AI Provider 实例

    Args:
        provider_name: provider 名称 (dashscope / yuanqi)
        api_key: API 密钥
        app_id: APP ID（DashScope 需要）

    Returns:
        AIProvider 实例
    """
    if provider_name == 'dashscope':
        if not app_id:
            raise ValueError('DashScope provider requires app_id')
        return DashScopeProvider(api_key, app_id)
    elif provider_name == 'yuanqi':
        if not app_id:
            raise ValueError('Yuanqi provider requires app_id')
        return YuanqiProvider(app_id, api_key)
    else:
        raise ValueError(f'Unknown AI provider: {provider_name}')
