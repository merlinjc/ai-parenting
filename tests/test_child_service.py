"""儿童档案服务测试。"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Child, User
from ai_parenting.backend.schemas import ChildCreate, ChildUpdate
from ai_parenting.backend.services import child_service


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户。"""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        auth_provider="email",
        display_name="测试家长",
        timezone="Asia/Shanghai",
    )
    db_session.add(user)
    await db_session.flush()
    return user


class TestCreateChild:
    """创建儿童档案测试。"""

    @pytest.mark.asyncio
    async def test_create_basic(self, db_session, test_user):
        data = ChildCreate(
            nickname="小明",
            birth_year_month="2024-01",
            focus_themes=["language", "social"],
            risk_level="normal",
        )
        child = await child_service.create_child(db_session, test_user.id, data)

        assert child.nickname == "小明"
        assert child.birth_year_month == "2024-01"
        assert child.focus_themes == ["language", "social"]
        assert child.risk_level == "normal"
        assert child.onboarding_completed is False
        assert child.id is not None

    @pytest.mark.asyncio
    async def test_auto_computes_age_and_stage(self, db_session, test_user):
        """创建时自动计算月龄和阶段。"""
        data = ChildCreate(
            nickname="小红",
            birth_year_month="2024-01",
        )
        child = await child_service.create_child(db_session, test_user.id, data)

        assert child.age_months >= 18
        assert child.stage in ("18_24m", "24_36m", "36_48m")

    @pytest.mark.asyncio
    async def test_empty_focus_themes(self, db_session, test_user):
        data = ChildCreate(nickname="小花", birth_year_month="2024-06")
        child = await child_service.create_child(db_session, test_user.id, data)
        assert child.focus_themes == []


class TestGetChild:
    """获取儿童档案测试。"""

    @pytest.mark.asyncio
    async def test_get_existing(self, db_session, test_user):
        data = ChildCreate(nickname="小明", birth_year_month="2024-01")
        created = await child_service.create_child(db_session, test_user.id, data)

        found = await child_service.get_child(db_session, created.id)
        assert found is not None
        assert found.nickname == "小明"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, db_session):
        found = await child_service.get_child(db_session, uuid.uuid4())
        assert found is None


class TestGetChildrenByUser:
    """获取用户下所有儿童测试。"""

    @pytest.mark.asyncio
    async def test_multiple_children(self, db_session, test_user):
        await child_service.create_child(
            db_session, test_user.id,
            ChildCreate(nickname="老大", birth_year_month="2023-06")
        )
        await child_service.create_child(
            db_session, test_user.id,
            ChildCreate(nickname="老二", birth_year_month="2024-06")
        )

        children = await child_service.get_children_by_user(db_session, test_user.id)
        assert len(children) == 2

    @pytest.mark.asyncio
    async def test_no_children(self, db_session, test_user):
        children = await child_service.get_children_by_user(db_session, test_user.id)
        assert len(children) == 0


class TestUpdateChild:
    """更新儿童档案测试。"""

    @pytest.mark.asyncio
    async def test_update_nickname(self, db_session, test_user):
        data = ChildCreate(nickname="小明", birth_year_month="2024-01")
        child = await child_service.create_child(db_session, test_user.id, data)

        updated = await child_service.update_child(
            db_session, child.id, ChildUpdate(nickname="大明")
        )
        assert updated.nickname == "大明"

    @pytest.mark.asyncio
    async def test_update_focus_themes(self, db_session, test_user):
        data = ChildCreate(nickname="小明", birth_year_month="2024-01")
        child = await child_service.create_child(db_session, test_user.id, data)

        updated = await child_service.update_child(
            db_session, child.id,
            ChildUpdate(focus_themes=["emotion", "motor"])
        )
        assert updated.focus_themes == ["emotion", "motor"]

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, db_session):
        result = await child_service.update_child(
            db_session, uuid.uuid4(), ChildUpdate(nickname="不存在")
        )
        assert result is None


class TestRefreshAgeAndStage:
    """刷新月龄和阶段测试。"""

    @pytest.mark.asyncio
    async def test_refresh(self, db_session, test_user):
        data = ChildCreate(nickname="小明", birth_year_month="2024-01")
        child = await child_service.create_child(db_session, test_user.id, data)
        original_age = child.age_months

        refreshed = await child_service.refresh_age_and_stage(db_session, child.id)
        assert refreshed is not None
        assert refreshed.age_months >= 18


class TestCompleteOnboarding:
    """完成首次引导测试。"""

    @pytest.mark.asyncio
    async def test_complete(self, db_session, test_user):
        data = ChildCreate(nickname="小明", birth_year_month="2024-01")
        child = await child_service.create_child(db_session, test_user.id, data)
        assert child.onboarding_completed is False

        completed = await child_service.complete_onboarding(db_session, child.id)
        assert completed.onboarding_completed is True
