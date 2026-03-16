"""审计日志测试。

验证审计日志格式正确、脱敏（不含完整 context/result）。
"""

from __future__ import annotations

import json
import logging
import uuid

import pytest

from ai_parenting.backend.audit import (
    log_ai_session,
    log_boundary_check,
    log_push_event,
    log_risk_escalation,
)


class TestAuditLogging:
    """审计日志格式和内容测试。"""

    def test_log_ai_session(self, caplog):
        """AI 会话审计日志格式正确。"""
        session_id = uuid.uuid4()
        child_id = uuid.uuid4()

        with caplog.at_level(logging.INFO, logger="ai_parenting.audit"):
            log_ai_session(
                session_id=session_id,
                session_type="instant_help",
                child_id=child_id,
                status="completed",
                latency_ms=1200,
                retry_count=0,
                boundary_flags=["flag_a"],
                is_degraded=False,
                model_provider="mock",
            )

        assert len(caplog.records) == 1
        record = json.loads(caplog.records[0].message)
        assert record["event_type"] == "ai_session"
        assert record["session_id"] == str(session_id)
        assert record["session_type"] == "instant_help"
        assert record["child_id"] == str(child_id)
        assert record["status"] == "completed"
        assert record["latency_ms"] == 1200
        assert record["boundary_flags"] == ["flag_a"]
        assert record["is_degraded"] is False
        # 不应包含 context_snapshot 和 result
        assert "context_snapshot" not in record
        assert "result" not in record

    def test_log_ai_session_minimal(self, caplog):
        """AI 审计日志最小参数。"""
        with caplog.at_level(logging.INFO, logger="ai_parenting.audit"):
            log_ai_session(
                session_id=uuid.uuid4(),
                session_type="plan_generation",
                child_id=uuid.uuid4(),
                status="failed",
            )
        record = json.loads(caplog.records[0].message)
        assert record["latency_ms"] is None
        assert record["boundary_flags"] == []

    def test_log_boundary_check(self, caplog):
        """边界检查审计日志格式。"""
        with caplog.at_level(logging.INFO, logger="ai_parenting.audit"):
            log_boundary_check(
                session_id=uuid.uuid4(),
                session_type="instant_help",
                passed=False,
                flags=["diagnosis_term", "absolute_judgment"],
                action_taken="cleaned",
            )
        record = json.loads(caplog.records[0].message)
        assert record["event_type"] == "boundary_check"
        assert record["passed"] is False
        assert len(record["flags"]) == 2
        assert record["action_taken"] == "cleaned"

    def test_log_risk_escalation(self, caplog):
        """风险升级审计日志格式。"""
        with caplog.at_level(logging.WARNING, logger="ai_parenting.audit"):
            log_risk_escalation(
                child_id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                previous_level="attention",
                new_level="consult",
                trigger="suggest_consult_prep",
                message_id=uuid.uuid4(),
            )
        record = json.loads(caplog.records[0].message)
        assert record["event_type"] == "risk_escalation"
        assert record["previous_level"] == "attention"
        assert record["new_level"] == "consult"
        assert record["trigger"] == "suggest_consult_prep"

    def test_log_push_event(self, caplog):
        """推送事件审计日志格式。"""
        with caplog.at_level(logging.INFO, logger="ai_parenting.audit"):
            log_push_event(
                message_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                event="send",
                push_status="sent",
            )
        record = json.loads(caplog.records[0].message)
        assert record["event_type"] == "push_event"
        assert record["event"] == "send"
        assert record["push_status"] == "sent"

    def test_log_push_event_with_error(self, caplog):
        """推送失败审计日志包含错误信息。"""
        with caplog.at_level(logging.INFO, logger="ai_parenting.audit"):
            log_push_event(
                message_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                event="failed",
                push_status="failed",
                error="Connection timeout",
            )
        record = json.loads(caplog.records[0].message)
        assert record["error"] == "Connection timeout"

    def test_desensitization(self, caplog):
        """验证审计日志不包含敏感数据。"""
        with caplog.at_level(logging.INFO, logger="ai_parenting.audit"):
            log_ai_session(
                session_id=uuid.uuid4(),
                session_type="instant_help",
                child_id=uuid.uuid4(),
                status="completed",
            )
        raw = caplog.records[0].message
        # 不应包含任何大段文本或敏感字段名
        assert "context_snapshot" not in raw
        assert "result" not in raw
        assert "prompt" not in raw
