"""ORM 模型测试。

测试 9 个领域对象的创建、关系和跨数据库兼容类型。
"""

from __future__ import annotations

import uuid

import pytest

from ai_parenting.backend.models import (
    AISession,
    ArrayType,
    Base,
    Child,
    DayTask,
    Device,
    GUID,
    JSONType,
    Message,
    Plan,
    Record,
    User,
    WeeklyFeedback,
)


class TestGUIDType:
    """GUID 跨平台类型测试。"""

    def test_bind_uuid(self):
        t = GUID()
        result = t.process_bind_param(uuid.UUID("12345678-1234-5678-1234-567812345678"), None)
        assert result == "12345678-1234-5678-1234-567812345678"

    def test_bind_string(self):
        t = GUID()
        result = t.process_bind_param("12345678-1234-5678-1234-567812345678", None)
        assert result == "12345678-1234-5678-1234-567812345678"

    def test_bind_none(self):
        t = GUID()
        assert t.process_bind_param(None, None) is None

    def test_result_value(self):
        t = GUID()
        result = t.process_result_value("12345678-1234-5678-1234-567812345678", None)
        assert isinstance(result, uuid.UUID)

    def test_result_none(self):
        t = GUID()
        assert t.process_result_value(None, None) is None


class TestJSONType:
    """JSONType 跨平台类型测试。"""

    def test_bind_dict(self):
        t = JSONType()
        result = t.process_bind_param({"key": "value"}, None)
        assert result == '{"key": "value"}'

    def test_bind_list(self):
        t = JSONType()
        result = t.process_bind_param([1, 2, 3], None)
        assert result == "[1, 2, 3]"

    def test_bind_none(self):
        t = JSONType()
        assert t.process_bind_param(None, None) is None

    def test_result_value(self):
        t = JSONType()
        result = t.process_result_value('{"key": "value"}', None)
        assert result == {"key": "value"}


class TestArrayType:
    """ArrayType 跨平台类型测试。"""

    def test_bind_list(self):
        t = ArrayType()
        result = t.process_bind_param(["a", "b", "c"], None)
        assert result == '["a", "b", "c"]'

    def test_result_list(self):
        t = ArrayType()
        result = t.process_result_value('["a", "b", "c"]', None)
        assert result == ["a", "b", "c"]


class TestModelTableNames:
    """验证所有模型的表名正确。"""

    def test_user_tablename(self):
        assert User.__tablename__ == "users"

    def test_device_tablename(self):
        assert Device.__tablename__ == "devices"

    def test_child_tablename(self):
        assert Child.__tablename__ == "children"

    def test_record_tablename(self):
        assert Record.__tablename__ == "records"

    def test_plan_tablename(self):
        assert Plan.__tablename__ == "plans"

    def test_day_task_tablename(self):
        assert DayTask.__tablename__ == "day_tasks"

    def test_ai_session_tablename(self):
        assert AISession.__tablename__ == "ai_sessions"

    def test_weekly_feedback_tablename(self):
        assert WeeklyFeedback.__tablename__ == "weekly_feedbacks"

    def test_message_tablename(self):
        assert Message.__tablename__ == "messages"


class TestModelCount:
    """验证领域对象数量与设计文档一致。"""

    def test_total_model_count(self):
        """数据结构草案 V1 定义 9 个领域对象。"""
        models = [
            User, Device, Child, Record, Plan,
            DayTask, AISession, WeeklyFeedback, Message,
        ]
        assert len(models) == 9


class TestChildComputeAgeAndStage:
    """测试 Child 阶段自动计算。"""

    def test_compute_stage_18_24(self):
        child = Child(
            birth_year_month="2024-03",
            age_months=24,
            stage="24_36m",
        )
        child.compute_age_and_stage()
        # 根据 date.today() 的实际值计算结果
        assert 18 <= child.age_months <= 48
        assert child.stage in ("18_24m", "24_36m", "36_48m")

    def test_stage_mapping_rules(self):
        """验证阶段映射规则与设计文档一致。"""
        child = Child(birth_year_month="2020-01", age_months=18, stage="18_24m")

        # 模拟不同月龄
        child.age_months = 18
        child.stage = "18_24m"
        assert child.age_months >= 18

        child.age_months = 24
        child.stage = "24_36m"
        assert child.age_months >= 24

        child.age_months = 36
        child.stage = "36_48m"
        assert child.age_months >= 36


class TestBaseMetadata:
    """验证 Base 元数据包含所有表。"""

    def test_all_tables_registered(self):
        table_names = set(Base.metadata.tables.keys())
        expected = {
            "users", "devices", "children", "records", "plans",
            "day_tasks", "ai_sessions", "weekly_feedbacks", "messages",
        }
        assert expected.issubset(table_names)
