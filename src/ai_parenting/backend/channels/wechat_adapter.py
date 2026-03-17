"""微信服务号渠道适配器。

直连微信公众平台 API，实现模板消息发送和客服消息收发。
包含消息签名验证和 access_token 自动刷新。
配置不完整时自动降级为日志 Mock。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from ai_parenting.backend.channels.base import (
    ChannelAdapter,
    ChannelHealth,
    ChannelMessage,
    ChannelStatus,
    InboundMessage,
    MessageType,
    SendResult,
)

logger = logging.getLogger(__name__)

# access_token 有效期（微信官方为 7200 秒，提前 300 秒刷新）
TOKEN_REFRESH_BUFFER = 300

# 微信 API 基础 URL
_WX_API_BASE = "https://api.weixin.qq.com/cgi-bin"


class WeChatAdapter(ChannelAdapter):
    """微信服务号渠道适配器。

    **运行模式：**
    - 如果 app_id 和 app_secret 完整配置，使用真实微信 API
    - 否则自动降级为日志 Mock 模式

    配置项:
    - app_id: 微信公众号 AppID
    - app_secret: 微信公众号 AppSecret
    - token: 消息签名验证 Token
    - aes_key: 消息加解密 AES Key（可选，明文模式不需要）
    """

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        token: str = "",
        aes_key: str = "",
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._token = token
        self._aes_key = aes_key
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._mock_mode = not (app_id and app_secret)
        self._http_client: httpx.AsyncClient | None = None
        self._last_error: str | None = None
        self._consecutive_failures = 0
        self._token_lock = asyncio.Lock()  # P1-6: 防止并发刷新竞态

    def _is_configured(self) -> bool:
        """检查微信凭据是否完整配置。"""
        return bool(self._app_id and self._app_secret)

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取复用的 HTTP 客户端。"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    @property
    def channel_name(self) -> str:
        return "wechat"

    async def send_message(self, message: ChannelMessage) -> SendResult:
        """发送微信模板消息或客服消息。

        message.recipient_id 对应微信用户的 OpenID。
        message.template_id 非空时发送模板消息，否则发送客服文本消息。
        """
        start = time.monotonic()

        if self._mock_mode:
            return self._send_mock(message, start)

        try:
            await self._ensure_access_token()

            if message.template_id:
                return await self._send_template_message(message, start)
            else:
                return await self._send_custom_message(message, start)

        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            self._consecutive_failures += 1
            self._last_error = str(exc)
            logger.error("WeChat send exception: %s", exc)
            return SendResult(
                success=False,
                channel_name=self.channel_name,
                error=f"WeChat exception: {exc}",
                latency_ms=elapsed,
            )

    async def _send_template_message(
        self, message: ChannelMessage, start: float
    ) -> SendResult:
        """发送模板消息。"""
        client = await self._get_http_client()
        url = f"{_WX_API_BASE}/message/template/send?access_token={self._access_token}"
        payload: dict[str, Any] = {
            "touser": message.recipient_id,
            "template_id": message.template_id,
            "data": message.template_data or {},
        }

        resp = await client.post(url, json=payload)
        result = resp.json()
        elapsed = int((time.monotonic() - start) * 1000)

        errcode = result.get("errcode", 0)
        if errcode == 0:
            self._consecutive_failures = 0
            self._last_error = None
            msg_id = str(result.get("msgid", ""))
            logger.debug(
                "WeChat template sent: openid=%s, msgid=%s, latency=%dms",
                message.recipient_id, msg_id, elapsed,
            )
            return SendResult(
                success=True,
                channel_name=self.channel_name,
                provider_message_id=f"wechat-tpl-{msg_id}",
                latency_ms=elapsed,
            )

        # 微信 API 返回错误
        errmsg = result.get("errmsg", "unknown")
        self._consecutive_failures += 1
        self._last_error = f"{errcode}: {errmsg}"
        logger.warning(
            "WeChat template send failed: openid=%s, errcode=%d, errmsg=%s",
            message.recipient_id, errcode, errmsg,
        )

        # 特殊错误码处理
        if errcode == 40001:
            # access_token 失效，强制刷新
            self._access_token = None
            self._token_expires_at = 0.0
        elif errcode == 43004:
            # 用户未关注公众号
            logger.info("User %s has unfollowed", message.recipient_id)

        return SendResult(
            success=False,
            channel_name=self.channel_name,
            error=f"WeChat: {errcode} {errmsg}",
            latency_ms=elapsed,
        )

    async def _send_custom_message(
        self, message: ChannelMessage, start: float
    ) -> SendResult:
        """发送客服文本消息（48 小时内有互动的用户才可发送）。"""
        client = await self._get_http_client()
        url = f"{_WX_API_BASE}/message/custom/send?access_token={self._access_token}"
        payload = {
            "touser": message.recipient_id,
            "msgtype": "text",
            "text": {"content": f"{message.title}\n{message.body}"},
        }

        resp = await client.post(url, json=payload)
        result = resp.json()
        elapsed = int((time.monotonic() - start) * 1000)

        errcode = result.get("errcode", 0)
        if errcode == 0:
            self._consecutive_failures = 0
            self._last_error = None
            logger.debug(
                "WeChat custom message sent: openid=%s, latency=%dms",
                message.recipient_id, elapsed,
            )
            return SendResult(
                success=True,
                channel_name=self.channel_name,
                provider_message_id=f"wechat-custom-{uuid.uuid4().hex[:8]}",
                latency_ms=elapsed,
            )

        errmsg = result.get("errmsg", "unknown")
        self._consecutive_failures += 1
        self._last_error = f"{errcode}: {errmsg}"
        logger.warning(
            "WeChat custom send failed: openid=%s, errcode=%d, errmsg=%s",
            message.recipient_id, errcode, errmsg,
        )

        if errcode == 40001:
            self._access_token = None
            self._token_expires_at = 0.0

        return SendResult(
            success=False,
            channel_name=self.channel_name,
            error=f"WeChat: {errcode} {errmsg}",
            latency_ms=elapsed,
        )

    def _send_mock(self, message: ChannelMessage, start: float) -> SendResult:
        """Mock 模式：仅记录日志并返回成功。"""
        logger.info(
            "WeChat mock send: openid=%s, title='%s', template=%s",
            message.recipient_id,
            message.title,
            message.template_id,
        )
        elapsed = int((time.monotonic() - start) * 1000)
        return SendResult(
            success=True,
            channel_name=self.channel_name,
            provider_message_id=f"wechat-mock-{uuid.uuid4().hex[:8]}",
            latency_ms=elapsed,
        )

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage | None:
        """解析微信公众号回调消息。

        raw_payload 为微信回调 XML 解析后的字典，包含:
        - MsgType: text/image/voice/event
        - FromUserName: 发送者 OpenID
        - Content: 文本消息内容
        """
        msg_type = raw_payload.get("MsgType", "")
        from_user = raw_payload.get("FromUserName", "")

        if not from_user:
            return None

        if msg_type == "text":
            return InboundMessage(
                channel_name=self.channel_name,
                sender_id=from_user,
                content=raw_payload.get("Content", ""),
                message_type=MessageType.TEXT,
                raw_payload=raw_payload,
            )
        elif msg_type == "voice":
            return InboundMessage(
                channel_name=self.channel_name,
                sender_id=from_user,
                content=raw_payload.get("Recognition", ""),
                message_type=MessageType.VOICE,
                raw_payload=raw_payload,
            )
        elif msg_type == "event":
            event = raw_payload.get("Event", "")
            event_key = raw_payload.get("EventKey", "")
            return InboundMessage(
                channel_name=self.channel_name,
                sender_id=from_user,
                content=f"event:{event}:{event_key}",
                message_type=MessageType.TEXT,
                raw_payload=raw_payload,
            )

        logger.debug("Unsupported WeChat message type: %s", msg_type)
        return None

    async def health_check(self) -> ChannelHealth:
        """微信渠道健康检查。

        生产模式通过验证 access_token 有效性来检查连通性。
        """
        now = datetime.now(timezone.utc)

        if self._mock_mode:
            return ChannelHealth(
                status=ChannelStatus.HEALTHY,
                latency_ms=1,
                last_check_at=now,
                metadata={"mode": "mock"},
            )

        try:
            start = time.monotonic()
            await self._ensure_access_token()
            elapsed = int((time.monotonic() - start) * 1000)

            if self._consecutive_failures >= 5:
                return ChannelHealth(
                    status=ChannelStatus.UNAVAILABLE,
                    error=self._last_error,
                    latency_ms=elapsed,
                    last_check_at=now,
                    metadata={"mode": "production", "consecutive_failures": self._consecutive_failures},
                )
            elif self._consecutive_failures >= 2:
                return ChannelHealth(
                    status=ChannelStatus.DEGRADED,
                    error=self._last_error,
                    latency_ms=elapsed,
                    last_check_at=now,
                    metadata={"mode": "production", "consecutive_failures": self._consecutive_failures},
                )

            return ChannelHealth(
                status=ChannelStatus.HEALTHY,
                latency_ms=elapsed,
                last_check_at=now,
                metadata={"mode": "production"},
            )
        except Exception as exc:
            return ChannelHealth(
                status=ChannelStatus.UNAVAILABLE,
                error=str(exc),
                last_check_at=now,
                metadata={"mode": "production"},
            )

    def verify_signature(self, signature: str, timestamp: str, nonce: str) -> bool:
        """验证微信消息签名。

        Args:
            signature: 微信传来的签名。
            timestamp: 时间戳。
            nonce: 随机字符串。

        Returns:
            签名是否有效。
        """
        params = sorted([self._token, timestamp, nonce])
        computed = hashlib.sha1("".join(params).encode()).hexdigest()
        return computed == signature

    async def get_rate_limit_status(self) -> dict[str, int]:
        """微信 API 调用配额状态。

        模板消息限制：每日 10 万次（认证服务号）。
        客服消息限制：用户 48 小时内互动后才可发送。
        """
        if self._mock_mode:
            return {"template_remaining": 100000, "template_limit": 100000}

        # 生产环境下可调用微信配额查询接口
        # 但该接口本身每月仅可调用 10 次，因此日常使用估算值
        return {
            "template_remaining": 100000,
            "template_limit": 100000,
        }

    async def _ensure_access_token(self) -> None:
        """确保 access_token 有效，过期时自动刷新（P1-6: 双重检查锁防止并发刷新）。"""
        if self._access_token and time.time() < self._token_expires_at:
            return

        async with self._token_lock:
            # 双重检查：其他协程可能已经刷新
            if self._access_token and time.time() < self._token_expires_at:
                return

            if self._mock_mode:
                self._access_token = "mock_access_token"
                self._token_expires_at = time.time() + 7200
                return

            client = await self._get_http_client()
            url = (
                f"{_WX_API_BASE}/token"
                f"?grant_type=client_credential&appid={self._app_id}&secret={self._app_secret}"
            )

            resp = await client.get(url)
            data = resp.json()

            if "access_token" in data:
                self._access_token = data["access_token"]
                expires_in = data.get("expires_in", 7200)
                self._token_expires_at = time.time() + expires_in - TOKEN_REFRESH_BUFFER
                logger.info(
                    "WeChat access_token refreshed, expires_in=%ds",
                    expires_in,
                )
            else:
                errcode = data.get("errcode", -1)
                errmsg = data.get("errmsg", "unknown")
                raise RuntimeError(
                    f"Failed to get WeChat access_token: {errcode} {errmsg}"
                )

    async def close(self) -> None:
        """释放 HTTP 客户端资源。"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("WeChat HTTP client closed")
