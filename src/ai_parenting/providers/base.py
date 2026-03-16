"""模型供应商抽象接口。

定义模型供应商的统一调用接口，供编排调度器使用。
所有供应商实现（包括 Mock 实现）都必须继承此抽象基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """模型供应商抽象接口。

    编排调度器通过此接口调用不同的模型供应商，
    无需关心底层 API 差异。

    实现者需要提供：
    - generate(): 根据 Prompt 生成模型响应
    - provider_name: 供应商标识
    - model_version: 模型版本
    """

    @abstractmethod
    async def generate(self, prompt: str, timeout_seconds: float) -> str:
        """调用模型生成响应。

        Args:
            prompt: 完整的 Prompt 文本。
            timeout_seconds: 超时时间（秒）。

        Returns:
            模型返回的原始字符串（预期为 JSON 格式）。

        Raises:
            asyncio.TimeoutError: 超时。
            Exception: 其他调用异常。
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """供应商标识（如 "openai", "anthropic"）。"""
        ...

    @property
    @abstractmethod
    def model_version(self) -> str:
        """模型版本标识（如 "gpt-4o-2024-05-13"）。"""
        ...
