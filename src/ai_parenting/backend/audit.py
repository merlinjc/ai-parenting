"""审计日志模块。

提供结构化 JSON 审计日志，用于 AI 会话审计、边界检查审计和风险升级审计。
日志中只记录 ID 引用而不记录完整的 context_snapshot 和 result 内容，实现脱敏。

使用 Python 标准 logging 模块，配置专用的 ai_parenting.audit logger。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any


# 配置专用审计 logger
audit_logger = logging.getLogger("ai_parenting.audit")


def _safe_str(value: Any) -> str | None:
    """安全转换为字符串，None 保持为 None。"""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


def log_ai_session(
    *,
    session_id: uuid.UUID,
    session_type: str,
    child_id: uuid.UUID,
    status: str,
    latency_ms: int | None = None,
    retry_count: int = 0,
    boundary_flags: list[str] | None = None,
    is_degraded: bool = False,
    error_info: str | None = None,
    model_provider: str | None = None,
) -> None:
    """记录 AI 会话审计日志（脱敏：不记录 context_snapshot 和 result 原文）。"""
    record = {
        "event_type": "ai_session",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(session_id),
        "session_type": session_type,
        "child_id": str(child_id),
        "status": status,
        "latency_ms": latency_ms,
        "retry_count": retry_count,
        "boundary_flags": boundary_flags or [],
        "is_degraded": is_degraded,
        "error_info": error_info,
        "model_provider": model_provider,
    }
    audit_logger.info(json.dumps(record, ensure_ascii=False))


def log_boundary_check(
    *,
    session_id: uuid.UUID,
    session_type: str,
    passed: bool,
    flags: list[str],
    action_taken: str = "none",
) -> None:
    """记录边界检查审计日志。

    action_taken: "none" | "cleaned" | "degraded"
    """
    record = {
        "event_type": "boundary_check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(session_id),
        "session_type": session_type,
        "passed": passed,
        "flags": flags,
        "action_taken": action_taken,
    }
    audit_logger.info(json.dumps(record, ensure_ascii=False))


def log_risk_escalation(
    *,
    child_id: uuid.UUID,
    session_id: uuid.UUID,
    previous_level: str,
    new_level: str,
    trigger: str,
    message_id: uuid.UUID | None = None,
) -> None:
    """记录风险升级审计日志。"""
    record = {
        "event_type": "risk_escalation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "child_id": str(child_id),
        "session_id": str(session_id),
        "previous_level": previous_level,
        "new_level": new_level,
        "trigger": trigger,
        "message_id": _safe_str(message_id),
    }
    audit_logger.warning(json.dumps(record, ensure_ascii=False))


def log_push_event(
    *,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    event: str,
    push_status: str,
    error: str | None = None,
) -> None:
    """记录推送事件审计日志。

    event: "send" | "delivered" | "clicked" | "failed"
    """
    record = {
        "event_type": "push_event",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_id": str(message_id),
        "user_id": str(user_id),
        "event": event,
        "push_status": push_status,
        "error": error,
    }
    audit_logger.info(json.dumps(record, ensure_ascii=False))
