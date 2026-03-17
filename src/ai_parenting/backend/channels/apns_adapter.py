"""APNs 推送渠道适配器。

基于 Apple Push Notification service 实现，
复用现有 Device 模型的 push_token 字段。
使用 aioapns 库进行真实推送，未安装时自动降级为日志 Mock。
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ai_parenting.backend.channels.base import (
    ChannelAdapter,
    ChannelHealth,
    ChannelMessage,
    ChannelStatus,
    InboundMessage,
    SendResult,
)

logger = logging.getLogger(__name__)

# APNs 错误码分类 — 需要标记 token 失活的错误
_TOKEN_INVALID_REASONS = frozenset({
    "BadDeviceToken",
    "Unregistered",
    "DeviceTokenNotForTopic",
    "TopicDisallowed",
    "ExpiredProviderToken",
})

# 需要重试的临时性错误
_RETRYABLE_REASONS = frozenset({
    "ServiceUnavailable",
    "InternalServerError",
    "Shutdown",
    "TooManyRequests",
})

# 静默推送需要的 content-available payload
_SILENT_PUSH_PAYLOAD = {
    "aps": {"content-available": 1},
}


class APNsAdapter(ChannelAdapter):
    """Apple Push Notification service 渠道适配器。

    **运行模式：**
    - 如果 aioapns 已安装且配置完整（key_path/key_id/team_id），使用真实 APNs 推送
    - 否则自动降级为日志 Mock 模式（开发阶段可用）

    配置项:
    - bundle_id: iOS 应用 Bundle ID
    - key_path: APNs Auth Key (.p8) 文件路径
    - key_id: APNs Key ID
    - team_id: Apple Developer Team ID
    - use_sandbox: 是否使用 sandbox 环境
    """

    def __init__(
        self,
        bundle_id: str = "",
        key_path: str = "",
        key_id: str = "",
        team_id: str = "",
        use_sandbox: bool = True,
    ) -> None:
        self._bundle_id = bundle_id
        self._key_path = key_path
        self._key_id = key_id
        self._team_id = team_id
        self._use_sandbox = use_sandbox
        self._client: Any = None  # aioapns.APNs instance (lazy init)
        self._mock_mode = False
        self._last_error: str | None = None
        self._consecutive_failures = 0
        # 记录失活 token（供外部查询和清理，P2-9: 限制大小）
        self.invalid_tokens: set[str] = set()
        self._max_invalid_tokens = 10000

    def _is_configured(self) -> bool:
        """检查 APNs 凭据是否完整配置。"""
        return bool(self._key_path and self._key_id and self._team_id and self._bundle_id)

    async def _ensure_client(self) -> bool:
        """确保 aioapns 客户端已初始化。

        Returns:
            True 如果客户端就绪，False 如果降级为 Mock。
        """
        if self._client is not None:
            return True

        if not self._is_configured():
            logger.info(
                "APNs credentials not configured (key_path=%s, key_id=%s, team_id=%s), "
                "running in mock mode",
                bool(self._key_path), bool(self._key_id), bool(self._team_id),
            )
            self._mock_mode = True
            return False

        try:
            from aioapns import APNs

            self._client = APNs(
                key=self._key_path,
                key_id=self._key_id,
                team_id=self._team_id,
                topic=self._bundle_id,
                use_sandbox=self._use_sandbox,
            )
            self._mock_mode = False
            logger.info(
                "APNs client initialized (bundle=%s, sandbox=%s)",
                self._bundle_id, self._use_sandbox,
            )
            return True
        except ImportError:
            logger.warning(
                "aioapns not installed, APNs running in mock mode. "
                "Install with: pip install aioapns"
            )
            self._mock_mode = True
            return False
        except Exception as exc:
            logger.error("Failed to initialize APNs client: %s", exc)
            self._mock_mode = True
            self._last_error = str(exc)
            return False

    @property
    def channel_name(self) -> str:
        return "apns"

    async def send_message(self, message: ChannelMessage) -> SendResult:
        """通过 APNs 发送推送通知。

        message.recipient_id 对应 Device.push_token。
        """
        start = time.monotonic()

        # 尝试初始化真实客户端
        client_ready = await self._ensure_client()

        if client_ready and self._client is not None:
            return await self._send_real(message, start)
        else:
            return self._send_mock(message, start)

    async def _send_real(self, message: ChannelMessage, start: float) -> SendResult:
        """通过 aioapns 发送真实 APNs 推送。"""
        from aioapns import NotificationRequest

        token = message.recipient_id
        truncated_token = token[:16] + "..." if len(token) > 16 else token

        request = NotificationRequest(
            device_token=token,
            message={
                "aps": {
                    "alert": {"title": message.title, "body": message.body},
                    "sound": "default",
                    "badge": 1,
                },
                **(message.data or {}),
            },
        )

        try:
            response = await self._client.send_notification(request)
            elapsed = int((time.monotonic() - start) * 1000)

            if response.is_successful:
                self._consecutive_failures = 0
                self._last_error = None
                logger.debug(
                    "APNs sent: token=%s, latency=%dms",
                    truncated_token, elapsed,
                )
                return SendResult(
                    success=True,
                    channel_name=self.channel_name,
                    provider_message_id=f"apns-{uuid.uuid4().hex[:8]}",
                    latency_ms=elapsed,
                )

            # 发送失败 — 检查错误原因
            reason = response.description or "unknown"
            self._last_error = reason
            logger.warning(
                "APNs send failed: token=%s, reason=%s, status=%s",
                truncated_token, reason, response.status,
            )

            # Token 无效 → 记录以供后续清理
            if reason in _TOKEN_INVALID_REASONS:
                # P2-9: 限制 invalid_tokens 集合大小
                if len(self.invalid_tokens) < self._max_invalid_tokens:
                    self.invalid_tokens.add(token)
                logger.info(
                    "APNs token invalidated: %s (reason=%s)",
                    truncated_token, reason,
                )

            # 可重试错误 → 标记为临时失败
            is_retryable = reason in _RETRYABLE_REASONS
            if is_retryable:
                self._consecutive_failures += 1

            return SendResult(
                success=False,
                channel_name=self.channel_name,
                error=f"APNs: {reason}",
                latency_ms=elapsed,
            )

        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            self._consecutive_failures += 1
            self._last_error = str(exc)
            logger.error(
                "APNs send exception: token=%s, error=%s, latency=%dms",
                truncated_token, exc, elapsed,
            )
            return SendResult(
                success=False,
                channel_name=self.channel_name,
                error=f"APNs exception: {exc}",
                latency_ms=elapsed,
            )

    def _send_mock(self, message: ChannelMessage, start: float) -> SendResult:
        """Mock 模式：仅记录日志并返回成功。"""
        token = message.recipient_id
        truncated_token = token[:16] + "..." if len(token) > 16 else token
        logger.info(
            "APNs mock send: token=%s, title='%s'",
            truncated_token,
            message.title,
        )
        elapsed = int((time.monotonic() - start) * 1000)
        return SendResult(
            success=True,
            channel_name=self.channel_name,
            provider_message_id=f"apns-mock-{uuid.uuid4().hex[:8]}",
            latency_ms=elapsed,
        )

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage | None:
        """APNs 是纯推送渠道，不支持入站消息。"""
        return None

    async def health_check(self) -> ChannelHealth:
        """APNs 健康检查。

        - Mock 模式：直接返回 HEALTHY（开发环境）
        - 生产模式：基于最近发送结果判断健康状态
        """
        now = datetime.now(timezone.utc)

        if self._mock_mode:
            return ChannelHealth(
                status=ChannelStatus.HEALTHY,
                latency_ms=1,
                last_check_at=now,
                metadata={"mode": "mock"},
            )

        # 基于连续失败次数判断健康度
        if self._consecutive_failures >= 5:
            return ChannelHealth(
                status=ChannelStatus.UNAVAILABLE,
                error=self._last_error or "Multiple consecutive failures",
                last_check_at=now,
                metadata={
                    "mode": "production",
                    "consecutive_failures": self._consecutive_failures,
                    "invalid_tokens_count": len(self.invalid_tokens),
                },
            )
        elif self._consecutive_failures >= 2:
            return ChannelHealth(
                status=ChannelStatus.DEGRADED,
                error=self._last_error,
                last_check_at=now,
                metadata={
                    "mode": "production",
                    "consecutive_failures": self._consecutive_failures,
                    "invalid_tokens_count": len(self.invalid_tokens),
                },
            )

        return ChannelHealth(
            status=ChannelStatus.HEALTHY,
            latency_ms=10,
            last_check_at=now,
            metadata={
                "mode": "production",
                "sandbox": self._use_sandbox,
                "invalid_tokens_count": len(self.invalid_tokens),
            },
        )

    async def close(self) -> None:
        """释放 APNs 客户端资源。"""
        if self._client is not None:
            try:
                # aioapns APNs 类没有 close() 方法，但其内部 httpx 连接会在 GC 时释放
                self._client = None
                logger.info("APNs client released")
            except Exception as exc:
                logger.error("Error releasing APNs client: %s", exc)
