"""[Optional] 云端 TTS Provider 抽象。

iOS 原生优先策略下，此模块为 Fallback 使用：
- 需要高品质拟人语音时切换云端 TTS
- Android / Web 端可复用此 Provider

提供 Provider 抽象 + 腾讯云 TTS 实现 + Mock 实现 + 高频回复预缓存。
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TTSResult:
    """TTS 合成结果。"""

    audio_url: str | None = None  # 音频文件 URL
    audio_data: bytes | None = None  # 原始音频数据
    duration_ms: int | None = None
    provider: str = "unknown"
    cached: bool = False  # 是否命中缓存


class TTSProvider(ABC):
    """TTS Provider 抽象基类。"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def synthesize(self, text: str, voice: str = "zh-CN") -> TTSResult:
        """将文本合成为语音。"""
        ...


class MockTTSProvider(TTSProvider):
    """Mock TTS Provider（开发/测试用）。"""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def synthesize(self, text: str, voice: str = "zh-CN") -> TTSResult:
        logger.info("Mock TTS synthesize: text_len=%d", len(text))
        return TTSResult(
            audio_url=f"mock://tts/{hashlib.md5(text.encode()).hexdigest()[:8]}.mp3",
            duration_ms=len(text) * 100,  # 粗估
            provider=self.provider_name,
        )


class CachedTTSProvider(TTSProvider):
    """带预缓存的 TTS Provider 包装器。

    对高频回复（如"已记录"、"今天的任务是..."）预生成音频缓存，
    命中缓存时延迟为 0ms。
    """

    def __init__(self, delegate: TTSProvider, cache_size: int = 100) -> None:
        self._delegate = delegate
        self._cache: dict[str, TTSResult] = {}
        self._cache_size = cache_size
        self._cache_order: list[str] = []  # P2-8: LRU 顺序追踪

    @property
    def provider_name(self) -> str:
        return f"cached_{self._delegate.provider_name}"

    async def synthesize(self, text: str, voice: str = "zh-CN") -> TTSResult:
        cache_key = f"{voice}:{text}"

        # 查缓存
        if cache_key in self._cache:
            result = self._cache[cache_key]
            result.cached = True
            # P2-8: 更新 LRU 顺序
            if cache_key in self._cache_order:
                self._cache_order.remove(cache_key)
            self._cache_order.append(cache_key)
            return result

        # 未命中，调用底层 Provider
        result = await self._delegate.synthesize(text, voice)

        # P2-8: LRU 淘汰策略（淘汰最久未使用的条目）
        while len(self._cache) >= self._cache_size and self._cache_order:
            oldest_key = self._cache_order.pop(0)
            self._cache.pop(oldest_key, None)
        self._cache[cache_key] = result
        self._cache_order.append(cache_key)

        return result

    async def pre_warm(self, phrases: list[str], voice: str = "zh-CN") -> int:
        """预热缓存：为高频短语预生成音频。"""
        warmed = 0
        for phrase in phrases:
            cache_key = f"{voice}:{phrase}"
            if cache_key not in self._cache:
                try:
                    result = await self._delegate.synthesize(phrase, voice)
                    self._cache[cache_key] = result
                    warmed += 1
                except Exception as exc:
                    logger.error("TTS pre-warm failed for '%s': %s", phrase, exc)
        logger.info("TTS cache pre-warmed: %d/%d phrases", warmed, len(phrases))
        return warmed


# 高频回复预缓存候选列表
HIGH_FREQ_PHRASES = [
    "已记录！",
    "好的，已帮您记录。",
    "让我帮您查看一下今天的任务。",
    "今天的任务已经完成了，真棒！",
    "我来帮您看看。",
    "好的，正在为您查询。",
    "抱歉，暂时无法处理您的请求。",
    "请再说一遍，我没有听清楚。",
]


class TencentCloudTTSProvider(TTSProvider):
    """腾讯云 TTS 实现（Fallback / 高品质场景）。"""

    def __init__(self, app_id: str = "", secret_key: str = "") -> None:
        self._app_id = app_id
        self._secret_key = secret_key

    @property
    def provider_name(self) -> str:
        return "tencent_cloud"

    async def synthesize(self, text: str, voice: str = "zh-CN") -> TTSResult:
        """调用腾讯云 TTS API。"""
        # 生产环境实现:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     resp = await client.post(
        #         "https://tts.tencentcloudapi.com/",
        #         json={"Text": text, "VoiceType": 1001, ...},
        #         headers={...}
        #     )

        logger.info("TencentCloud TTS (stub): text_len=%d", len(text))
        return TTSResult(
            audio_url=f"https://tts.example.com/{hashlib.md5(text.encode()).hexdigest()[:8]}.mp3",
            duration_ms=len(text) * 100,
            provider=self.provider_name,
        )
