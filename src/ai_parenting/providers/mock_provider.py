"""Mock 模型供应商。

用于测试和开发的 Mock 实现。
支持配置以下测试场景：
- 返回预设的合法 JSON 响应
- 模拟超时
- 返回非法 JSON
- 返回包含边界违规内容的 JSON
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from ai_parenting.providers.base import ModelProvider


class MockProvider(ModelProvider):
    """Mock 模型供应商实现。

    用于单元测试和开发环境。可通过构造参数配置不同的测试行为。

    Args:
        response_json: 预设的 JSON 响应字符串。
        simulate_timeout: 是否模拟超时。
        simulate_delay_seconds: 模拟的响应延迟（秒）。
        simulate_invalid_json: 是否返回非法 JSON。
        call_count: 调用计数器（由外部读取）。
    """

    def __init__(
        self,
        response_json: str = "{}",
        simulate_timeout: bool = False,
        simulate_delay_seconds: float = 0.0,
        simulate_invalid_json: bool = False,
    ) -> None:
        self._response_json = response_json
        self._simulate_timeout = simulate_timeout
        self._simulate_delay_seconds = simulate_delay_seconds
        self._simulate_invalid_json = simulate_invalid_json
        self.call_count: int = 0
        self._responses: list[str] = []  # 可设置多次调用的不同响应

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_version(self) -> str:
        return "mock-v1"

    def set_responses(self, responses: list[str]) -> None:
        """设置多次调用的不同响应（用于测试重试逻辑）。"""
        self._responses = list(responses)

    async def generate(self, prompt: str, timeout_seconds: float) -> str:
        """生成 Mock 响应。

        Args:
            prompt: Prompt 文本（Mock 实现中忽略）。
            timeout_seconds: 超时时间。

        Returns:
            预设的响应字符串。

        Raises:
            asyncio.TimeoutError: 当 simulate_timeout=True 时。
        """
        self.call_count += 1

        if self._simulate_timeout:
            await asyncio.sleep(timeout_seconds + 1)
            raise asyncio.TimeoutError("Mock timeout")

        if self._simulate_delay_seconds > 0:
            await asyncio.sleep(self._simulate_delay_seconds)

        if self._simulate_invalid_json:
            return "this is not valid json {{"

        # 如果设置了多个响应，按调用次数返回
        if self._responses:
            idx = min(self.call_count - 1, len(self._responses) - 1)
            return self._responses[idx]

        return self._response_json
