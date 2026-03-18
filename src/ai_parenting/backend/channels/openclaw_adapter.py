"""OpenClaw Gateway 渠道适配器。

通过 WebSocket 长连接对接 OpenClaw 网关（协议 v3），
统一转发 WhatsApp/Telegram 等海外渠道消息。
实现指数退避重连、Circuit Breaker 模式和本地消息缓冲队列。

协议 v3 关键变更：
- 帧格式统一为 req/res/event 三种类型
- 连接需要完成 challenge → connect → hello-ok 握手流程
- 健康检查端点为 /healthz

未安装 websockets 库时自动降级为日志 Mock。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

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

# Circuit Breaker 参数
CB_FAILURE_THRESHOLD = 5
CB_RECOVERY_TIMEOUT = 60  # 秒
CB_HALF_OPEN_MAX_CALLS = 3

# 重连参数
RECONNECT_INITIAL_DELAY = 1.0  # 秒
RECONNECT_MAX_DELAY = 60.0  # 秒
RECONNECT_MULTIPLIER = 2.0

# 缓冲队列大小
BUFFER_MAX_SIZE = 1000

# WebSocket 心跳
WS_HEARTBEAT_INTERVAL = 30  # 秒
WS_HEARTBEAT_TIMEOUT = 90  # 秒

# WebSocket 操作超时
WS_SEND_TIMEOUT = 10.0  # 秒
WS_RECV_TIMEOUT = 10.0  # 秒


class CircuitState(Enum):
    """断路器状态。"""

    CLOSED = "closed"  # 正常
    OPEN = "open"  # 熔断
    HALF_OPEN = "half_open"  # 探测恢复


class CircuitBreaker:
    """断路器模式实现。

    连续 N 次失败后自动熔断，避免无效重试占用资源。
    熔断期满后进入半开状态，允许有限探测请求。
    """

    def __init__(
        self,
        failure_threshold: int = CB_FAILURE_THRESHOLD,
        recovery_timeout: float = CB_RECOVERY_TIMEOUT,
        half_open_max_calls: int = CB_HALF_OPEN_MAX_CALLS,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """获取当前断路器状态（自动从 OPEN 转 HALF_OPEN）。"""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
        return self._state

    def allow_request(self) -> bool:
        """判断是否允许发送请求。"""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self._half_open_max_calls
        return False  # OPEN

    def record_success(self) -> None:
        """记录一次成功。"""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self._half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info("Circuit breaker recovered to CLOSED")
        else:
            self._failure_count = 0

    def record_failure(self) -> None:
        """记录一次失败。"""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker re-opened from HALF_OPEN")
        elif self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d failures", self._failure_count
            )


class OpenClawAdapter(ChannelAdapter):
    """OpenClaw Gateway WebSocket 渠道适配器。

    **运行模式：**
    - 如果 websockets 已安装且 ws_url 已配置，使用真实 WebSocket 连接
    - 否则自动降级为日志 Mock 模式

    配置项:
    - ws_url: OpenClaw Gateway WebSocket 地址
    - api_key: 认证密钥
    - target_channels: 此适配器代理的渠道列表，如 ['whatsapp', 'telegram']
    """

    def __init__(
        self,
        ws_url: str = "ws://localhost:8765",
        api_key: str = "",
        target_channels: list[str] | None = None,
    ) -> None:
        self._ws_url = ws_url
        self._api_key = api_key
        self._target_channels = target_channels or ["whatsapp", "telegram"]
        self._ws: Any = None  # websockets.WebSocketClientProtocol (lazy)
        self._connected = False
        self._mock_mode = False
        self._circuit_breaker = CircuitBreaker()
        self._buffer: asyncio.Queue[ChannelMessage] = asyncio.Queue(maxsize=BUFFER_MAX_SIZE)
        self._reconnect_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._last_pong_at: float = 0.0
        self._last_error: str | None = None

    @property
    def channel_name(self) -> str:
        return "openclaw"

    async def send_message(self, message: ChannelMessage) -> SendResult:
        """通过 OpenClaw Gateway 发送消息。

        如果 Circuit Breaker 熔断或未连接，消息进入本地缓冲队列。
        """
        start = time.monotonic()

        # 检查断路器状态
        if not self._circuit_breaker.allow_request():
            await self._buffer_message(message)
            return SendResult(
                success=False,
                channel_name=self.channel_name,
                error=f"Circuit breaker OPEN, message buffered (queue_size={self._buffer.qsize()})",
                latency_ms=int((time.monotonic() - start) * 1000),
            )

        if not self._connected:
            await self._buffer_message(message)
            self._ensure_reconnect_task()
            return SendResult(
                success=False,
                channel_name=self.channel_name,
                error=f"WebSocket disconnected, message buffered (queue_size={self._buffer.qsize()})",
                latency_ms=int((time.monotonic() - start) * 1000),
            )

        # 真实 WebSocket 发送或 Mock
        if self._mock_mode or self._ws is None:
            return self._send_mock(message, start)

        return await self._send_real(message, start)

    async def _send_real(self, message: ChannelMessage, start: float) -> SendResult:
        """通过真实 WebSocket 发送消息（协议 v3 帧格式）。"""
        target_channel = "whatsapp"
        if message.data:
            target_channel = message.data.get("target_channel", "whatsapp")

        # 协议 v3: 使用 req 帧格式
        request_id = f"send-{uuid.uuid4().hex[:12]}"
        payload = {
            "type": "req",
            "id": request_id,
            "method": "send",
            "params": {
                "channel": target_channel,
                "recipient": message.recipient_id,
                "content": {"title": message.title, "body": message.body},
                "idempotency_key": message.idempotency_key,
            },
        }

        try:
            await asyncio.wait_for(
                self._ws.send(json.dumps(payload)),
                timeout=WS_SEND_TIMEOUT,
            )

            # 等待 Gateway 确认回复（协议 v3: res 帧）
            raw_response = await asyncio.wait_for(
                self._ws.recv(),
                timeout=WS_RECV_TIMEOUT,
            )
            response = json.loads(raw_response)
            elapsed = int((time.monotonic() - start) * 1000)

            # 协议 v3: 响应帧通过 ok 字段判断成功
            if response.get("type") == "res" and response.get("ok") is True:
                self._circuit_breaker.record_success()
                self._last_error = None
                resp_payload = response.get("payload", {})
                msg_id = resp_payload.get("message_id", f"oc-{uuid.uuid4().hex[:8]}")
                logger.debug(
                    "OpenClaw sent: recipient=%s, channel=%s, msgid=%s, latency=%dms",
                    message.recipient_id, target_channel, msg_id, elapsed,
                )
                return SendResult(
                    success=True,
                    channel_name=self.channel_name,
                    provider_message_id=str(msg_id),
                    latency_ms=elapsed,
                )
            else:
                error_obj = response.get("error", {})
                error = error_obj.get("message", "Unknown Gateway error") if isinstance(error_obj, dict) else str(error_obj)
                self._circuit_breaker.record_failure()
                self._last_error = error
                logger.warning(
                    "OpenClaw send failed: recipient=%s, error=%s",
                    message.recipient_id, error,
                )
                return SendResult(
                    success=False,
                    channel_name=self.channel_name,
                    error=f"OpenClaw: {error}",
                    latency_ms=elapsed,
                )

        except asyncio.TimeoutError:
            elapsed = int((time.monotonic() - start) * 1000)
            self._circuit_breaker.record_failure()
            self._last_error = "Send timeout"
            logger.error(
                "OpenClaw send timeout: recipient=%s, latency=%dms",
                message.recipient_id, elapsed,
            )
            return SendResult(
                success=False,
                channel_name=self.channel_name,
                error="OpenClaw: send timeout",
                latency_ms=elapsed,
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            self._circuit_breaker.record_failure()
            self._last_error = str(exc)
            self._connected = False
            self._ensure_reconnect_task()
            logger.error(
                "OpenClaw send exception: %s, latency=%dms", exc, elapsed,
            )
            return SendResult(
                success=False,
                channel_name=self.channel_name,
                error=f"OpenClaw exception: {exc}",
                latency_ms=elapsed,
            )

    def _send_mock(self, message: ChannelMessage, start: float) -> SendResult:
        """Mock 模式：仅记录日志并返回成功。"""
        logger.info(
            "OpenClaw mock send: recipient=%s, title='%s'",
            message.recipient_id,
            message.title,
        )
        elapsed = int((time.monotonic() - start) * 1000)
        self._circuit_breaker.record_success()
        return SendResult(
            success=True,
            channel_name=self.channel_name,
            provider_message_id=f"oc-mock-{uuid.uuid4().hex[:8]}",
            latency_ms=elapsed,
        )

    async def receive_message(self, raw_payload: dict[str, Any]) -> InboundMessage | None:
        """解析 OpenClaw Gateway 转发的入站消息。

        支持两种格式：
        1. 协议 v3 event 帧：
        {
            "type": "event",
            "event": "chat.event",
            "payload": {
                "channel": "whatsapp" | "telegram",
                "sender": "user_channel_id",
                "content": {"text": "...", "type": "text"},
                "timestamp": "2026-03-17T10:00:00Z"
            }
        }
        2. Webhook 回调（向后兼容）：
        {
            "type": "inbound",
            "channel": "whatsapp" | "telegram",
            "sender": "user_channel_id",
            "content": {"text": "...", "type": "text"},
            "timestamp": "2026-03-17T10:00:00Z"
        }
        """
        msg_type = raw_payload.get("type")

        # 协议 v3 event 帧
        if msg_type == "event":
            event_name = raw_payload.get("event", "")
            if event_name != "chat.event":
                return None
            payload = raw_payload.get("payload", {})
            channel = payload.get("channel", "unknown")
            sender = payload.get("sender", "")
            content_obj = payload.get("content", {})
            text = content_obj.get("text", "")
            if not sender:
                return None
            return InboundMessage(
                channel_name=f"openclaw_{channel}",
                sender_id=sender,
                content=text,
                message_type=MessageType.TEXT,
                raw_payload=raw_payload,
            )

        # 向后兼容：Webhook 回调格式
        if msg_type != "inbound":
            return None

        channel = raw_payload.get("channel", "unknown")
        sender = raw_payload.get("sender", "")
        content_obj = raw_payload.get("content", {})
        text = content_obj.get("text", "")

        if not sender:
            return None

        return InboundMessage(
            channel_name=f"openclaw_{channel}",
            sender_id=sender,
            content=text,
            message_type=MessageType.TEXT,
            raw_payload=raw_payload,
        )

    async def health_check(self) -> ChannelHealth:
        """OpenClaw 渠道健康检查。

        除了 WebSocket 连接和断路器状态检查外，
        还尝试 HTTP 探活 OpenClaw Gateway 的 /healthz 端点。
        """
        cb_state = self._circuit_breaker.state

        if cb_state == CircuitState.OPEN:
            return ChannelHealth(
                status=ChannelStatus.UNAVAILABLE,
                error="Circuit breaker OPEN",
                last_check_at=datetime.now(timezone.utc),
                metadata={
                    "circuit_state": cb_state.value,
                    "buffer_size": self._buffer.qsize(),
                    "mode": "mock" if self._mock_mode else "production",
                },
            )

        if not self._connected:
            return ChannelHealth(
                status=ChannelStatus.DEGRADED,
                error="WebSocket disconnected (reconnecting)",
                last_check_at=datetime.now(timezone.utc),
                metadata={
                    "circuit_state": cb_state.value,
                    "buffer_size": self._buffer.qsize(),
                    "mode": "mock" if self._mock_mode else "production",
                },
            )

        # HTTP 探活 /healthz（仅在非 Mock 模式下）
        gateway_healthy = True
        gateway_latency_ms = 0
        if not self._mock_mode:
            try:
                import aiohttp

                # 从 ws:// URL 推断 http:// 健康检查 URL
                healthz_url = self._ws_url.replace("ws://", "http://").replace("wss://", "https://")
                # 移除 WebSocket 路径，使用 /healthz
                base_url = healthz_url.rsplit("/", 1)[0] if "/" in healthz_url.split("://", 1)[-1] else healthz_url
                healthz_url = f"{base_url}/healthz"

                probe_start = time.monotonic()
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(healthz_url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        gateway_latency_ms = int((time.monotonic() - probe_start) * 1000)
                        gateway_healthy = resp.status == 200
            except ImportError:
                # aiohttp 未安装，跳过 HTTP 探活
                pass
            except Exception:
                gateway_healthy = False

        return ChannelHealth(
            status=ChannelStatus.HEALTHY if gateway_healthy else ChannelStatus.DEGRADED,
            latency_ms=gateway_latency_ms or 10,
            error=None if gateway_healthy else "Gateway /healthz probe failed",
            last_check_at=datetime.now(timezone.utc),
            metadata={
                "circuit_state": cb_state.value,
                "buffer_size": self._buffer.qsize(),
                "target_channels": self._target_channels,
                "mode": "mock" if self._mock_mode else "production",
                "gateway_healthz": "ok" if gateway_healthy else "failed",
            },
        )

    async def connect(self) -> None:
        """建立 WebSocket 连接并完成协议 v3 握手。

        握手流程：
        1. 建立 WebSocket 连接
        2. 等待 connect.challenge 事件
        3. 发送 connect 请求（含认证信息）
        4. 等待 hello-ok 响应

        如果 websockets 库未安装，自动降级为 Mock 模式。
        """
        logger.info("OpenClaw WebSocket connecting to %s (protocol v3)", self._ws_url)

        try:
            import websockets

            self._ws = await websockets.connect(
                self._ws_url,
                additional_headers={"Authorization": f"Bearer {self._api_key}"},
                ping_interval=WS_HEARTBEAT_INTERVAL,
                ping_timeout=WS_HEARTBEAT_TIMEOUT,
                close_timeout=10,
            )

            # 协议 v3 握手：等待 connect.challenge
            try:
                raw_challenge = await asyncio.wait_for(
                    self._ws.recv(), timeout=5.0,
                )
                challenge = json.loads(raw_challenge)
                if challenge.get("type") == "event" and challenge.get("event") == "connect.challenge":
                    logger.debug("Received connect.challenge, sending connect request")
                else:
                    logger.debug("No challenge received, proceeding with direct connect")
            except asyncio.TimeoutError:
                logger.debug("No challenge event received (legacy mode), proceeding")

            # 发送 connect 请求
            connect_req = {
                "type": "req",
                "id": f"connect-{uuid.uuid4().hex[:8]}",
                "method": "connect",
                "params": {
                    "minProtocol": 3,
                    "maxProtocol": 3,
                    "client": {
                        "id": "ai-parenting-backend",
                        "version": "0.3.0",
                        "platform": "linux",
                        "mode": "operator",
                        "displayName": "AI Parenting Backend",
                    },
                    "role": "operator",
                    "scopes": ["operator.read", "operator.write"],
                    "auth": {"token": self._api_key} if self._api_key else {},
                },
            }
            await self._ws.send(json.dumps(connect_req))

            # 等待 hello-ok 响应
            try:
                raw_hello = await asyncio.wait_for(
                    self._ws.recv(), timeout=5.0,
                )
                hello = json.loads(raw_hello)
                if hello.get("type") == "res" and hello.get("ok") is True:
                    hello_payload = hello.get("payload", {})
                    server_version = hello_payload.get("server", {}).get("version", "unknown")
                    logger.info(
                        "OpenClaw WebSocket connected (protocol v3, server=%s)",
                        server_version,
                    )
                else:
                    logger.warning("Unexpected hello response: %s", hello)
            except asyncio.TimeoutError:
                logger.warning("Hello-ok timeout, proceeding with connection")

            self._connected = True
            self._mock_mode = False
            self._last_pong_at = time.monotonic()

            # 启动心跳监控任务
            self._start_heartbeat_task()

        except ImportError:
            logger.warning(
                "websockets not installed, OpenClaw running in mock mode. "
                "Install with: pip install websockets"
            )
            self._connected = True
            self._mock_mode = True
            self._last_pong_at = time.monotonic()
        except Exception as exc:
            logger.error("OpenClaw WebSocket connection failed: %s", exc)
            self._connected = False
            self._last_error = str(exc)
            raise

        # 连接恢复后，重发缓冲队列中的消息
        await self._flush_buffer()

    async def close(self) -> None:
        """关闭 WebSocket 连接并停止后台任务。"""
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception as exc:
                logger.debug("Error closing WebSocket: %s", exc)
            self._ws = None
        self._connected = False
        logger.info("OpenClaw WebSocket closed")

    def _start_heartbeat_task(self) -> None:
        """启动心跳监控后台任务。"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """心跳监控循环 — 检测连接是否超时断开。"""
        while self._connected and not self._mock_mode:
            try:
                await asyncio.sleep(WS_HEARTBEAT_INTERVAL)

                # websockets 库内建 ping/pong 机制（通过 ping_interval 参数），
                # 这里额外检查连接是否仍然 open
                if self._ws is not None and self._ws.closed:
                    logger.warning("OpenClaw WebSocket closed unexpectedly")
                    self._connected = False
                    self._ensure_reconnect_task()
                    return
                else:
                    self._last_pong_at = time.monotonic()

            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.error("Heartbeat loop error: %s", exc)
                self._connected = False
                self._ensure_reconnect_task()
                return

    async def _buffer_message(self, message: ChannelMessage) -> None:
        """将消息放入本地缓冲队列。"""
        try:
            self._buffer.put_nowait(message)
        except asyncio.QueueFull:
            logger.error(
                "OpenClaw buffer full (max=%d), dropping oldest message",
                BUFFER_MAX_SIZE,
            )
            try:
                self._buffer.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._buffer.put_nowait(message)

    async def _flush_buffer(self) -> None:
        """重发缓冲队列中的消息。"""
        flushed = 0
        while not self._buffer.empty():
            try:
                msg = self._buffer.get_nowait()
                result = await self.send_message(msg)
                if result.success:
                    flushed += 1
                else:
                    await self._buffer_message(msg)
                    break
            except Exception as exc:
                logger.error("Buffer flush error: %s", exc)
                break

        if flushed > 0:
            logger.info("Flushed %d buffered messages", flushed)

    def _ensure_reconnect_task(self) -> None:
        """确保重连任务正在运行。"""
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """指数退避重连循环。"""
        delay = RECONNECT_INITIAL_DELAY
        while not self._connected:
            try:
                logger.info("Attempting WebSocket reconnect (delay=%.1fs)", delay)
                await self.connect()
                if self._connected:
                    logger.info("WebSocket reconnected successfully")
                    return
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.warning("Reconnect failed: %s", exc)
                self._circuit_breaker.record_failure()

            await asyncio.sleep(delay)
            delay = min(delay * RECONNECT_MULTIPLIER, RECONNECT_MAX_DELAY)
