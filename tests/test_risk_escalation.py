"""风险升级单元测试。

覆盖 _check_risk_escalation() 的各种场景：
AI 返回 suggest_consult_prep=True 后 child.risk_level 自动升级、
消息自动创建、已 consult 不重复升级、无信号不触发等。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import AISession, Child, Message, User
from ai_parenting.backend.services.ai_session_service import _check_risk_escalation
from ai_parenting.backend.services import message_service


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    user = User(display_name="测试家长", auth_provider="email")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def child(db_session: AsyncSession, user: User) -> Child:
    child = Child(
        user_id=user.id,
        nickname="小明",
        birth_year_month="2024-01",
        age_months=24,
        stage="24_36m",
        risk_level="normal",
    )
    db_session.add(child)
    await db_session.flush()
    return child


@pytest.fixture
async def ai_session(db_session: AsyncSession, child: Child) -> AISession:
    session = AISession(
        child_id=child.id,
        session_type="instant_help",
        status="completed",
    )
    db_session.add(session)
    await db_session.flush()
    return session


class TestCheckRiskEscalation:
    """_check_risk_escalation 风险升级函数测试。"""

    async def test_suggest_consult_triggers_escalation(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """suggest_consult_prep=True 时自动升级 risk_level 到 consult。"""
        result_dict = {
            "suggest_consult_prep": True,
            "consult_prep_reason": "语言发展滞后",
        }
        await _check_risk_escalation(db_session, child, ai_session, result_dict)
        await db_session.flush()

        await db_session.refresh(child)
        assert child.risk_level == "consult"

    async def test_escalation_creates_risk_alert_message(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """风险升级时自动创建 risk_alert 类型消息。"""
        result_dict = {"suggest_consult_prep": True}
        await _check_risk_escalation(db_session, child, ai_session, result_dict)
        await db_session.flush()

        # 查询消息
        count = await message_service.get_unread_count(db_session, user.id)
        assert count >= 1

        stmt = select(Message).where(
            Message.user_id == user.id,
            Message.type == "risk_alert",
        )
        result = await db_session.execute(stmt)
        messages = list(result.scalars().all())
        assert len(messages) == 1
        assert messages[0].title == "成长关注提醒"
        assert messages[0].child_id == child.id

    async def test_already_consult_no_duplicate(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """已是 consult 级别时不重复升级，不创建消息。"""
        child.risk_level = "consult"
        await db_session.flush()

        result_dict = {"suggest_consult_prep": True}
        await _check_risk_escalation(db_session, child, ai_session, result_dict)

        count = await message_service.get_unread_count(db_session, user.id)
        assert count == 0

    async def test_suggest_false_no_escalation(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """suggest_consult_prep=False 时不触发升级。"""
        result_dict = {"suggest_consult_prep": False}
        await _check_risk_escalation(db_session, child, ai_session, result_dict)

        await db_session.refresh(child)
        assert child.risk_level == "normal"
        count = await message_service.get_unread_count(db_session, user.id)
        assert count == 0

    async def test_missing_field_no_escalation(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """结果中缺少 suggest_consult_prep 字段时不触发升级。"""
        result_dict = {"some_other_field": "value"}
        await _check_risk_escalation(db_session, child, ai_session, result_dict)

        await db_session.refresh(child)
        assert child.risk_level == "normal"

    async def test_none_result_no_escalation(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """result_dict 为 None 时不触发升级。"""
        await _check_risk_escalation(db_session, child, ai_session, None)

        await db_session.refresh(child)
        assert child.risk_level == "normal"

    async def test_escalation_from_elevated_to_consult(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """从 elevated 级别升级到 consult。"""
        child.risk_level = "elevated"
        await db_session.flush()

        result_dict = {"suggest_consult_prep": True}
        await _check_risk_escalation(db_session, child, ai_session, result_dict)
        await db_session.flush()

        await db_session.refresh(child)
        assert child.risk_level == "consult"

        # 验证消息创建
        stmt = select(Message).where(Message.type == "risk_alert")
        result = await db_session.execute(stmt)
        messages = list(result.scalars().all())
        assert len(messages) == 1

    async def test_message_contains_child_id_in_target_params(
        self, db_session: AsyncSession, user: User, child: Child, ai_session: AISession,
    ):
        """风险升级消息的 target_params 中包含 child_id。"""
        result_dict = {"suggest_consult_prep": True}
        await _check_risk_escalation(db_session, child, ai_session, result_dict)
        await db_session.flush()

        stmt = select(Message).where(Message.type == "risk_alert")
        result = await db_session.execute(stmt)
        msg = result.scalar_one()
        assert msg.target_params is not None
        assert msg.target_params.get("child_id") == str(child.id)
