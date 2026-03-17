"""[Optional] 云端 STT Provider 抽象。

iOS 原生优先策略下，此模块为 Fallback 使用：
- iOS ASR 置信度 < 0.6 时降级到云端 ASR
- Android / Web 端可复用此 Provider

提供 Provider 抽象 + 腾讯云 ASR 实现 + Mock 实现。
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    """ASR 转写结果。"""

    transcript: str
    confidence: float
    duration_ms: int | None = None
    provider: str = "unknown"


class STTProvider(ABC):
    """STT Provider 抽象基类。"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def transcribe(self, audio_url: str, language: str = "zh-CN") -> STTResult:
        """将音频转写为文本。"""
        ...


class MockSTTProvider(STTProvider):
    """Mock STT Provider（开发/测试用）。"""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def transcribe(self, audio_url: str, language: str = "zh-CN") -> STTResult:
        logger.info("Mock STT transcribe: audio_url=%s", audio_url)
        return STTResult(
            transcript="[Mock 转写] 这是一段测试语音内容",
            confidence=0.95,
            duration_ms=3000,
            provider=self.provider_name,
        )


class TencentCloudSTTProvider(STTProvider):
    """腾讯云 ASR 实现（Fallback 使用）。

    使用一句话识别 API，适合短语音（< 60 秒）。
    """

    def __init__(self, app_id: str = "", secret_key: str = "") -> None:
        self._app_id = app_id
        self._secret_key = secret_key

    @property
    def provider_name(self) -> str:
        return "tencent_cloud"

    async def transcribe(self, audio_url: str, language: str = "zh-CN") -> STTResult:
        """调用腾讯云一句话识别 API。"""
        # 生产环境实现:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     resp = await client.post(
        #         "https://asr.tencentcloudapi.com/",
        #         json={
        #             "ProjectId": 0,
        #             "SubServiceType": 2,
        #             "EngSerViceType": "16k_zh",
        #             "SourceType": 0,
        #             "Url": audio_url,
        #         },
        #         headers={...}  # 签名认证
        #     )

        logger.info("TencentCloud STT (stub): audio_url=%s", audio_url)
        return STTResult(
            transcript="[腾讯云 ASR Stub] 转写结果",
            confidence=0.9,
            duration_ms=2000,
            provider=self.provider_name,
        )
