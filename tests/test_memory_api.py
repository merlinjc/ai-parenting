"""OpenClaw 记忆初始化 API 测试。

测试记忆初始化端点和 memory_service 模块。
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Child, User
from ai_parenting.backend.services import memory_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_test_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    """创建测试用户。"""
    user = User(
        id=user_id,
        email=f"test_{user_id.hex[:8]}@example.com",
        hashed_password="hashed",
        display_name="测试用户",
        caregiver_role="mother",
        timezone="Asia/Shanghai",
        push_enabled=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_test_child(
    db: AsyncSession,
    user_id: uuid.UUID,
    nickname: str = "小北",
    birth_year_month: str = "2024-06",
    focus_themes: list[str] | None = None,
) -> Child:
    """创建测试儿童档案。"""
    child = Child(
        user_id=user_id,
        nickname=nickname,
        birth_year_month=birth_year_month,
        age_months=21,
        stage="M18_24",
        focus_themes=focus_themes or ["language", "social"],
        risk_level="normal",
        onboarding_completed=True,
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)
    return child


# ---------------------------------------------------------------------------
# memory_service 单元测试
# ---------------------------------------------------------------------------


class TestMemoryService:
    """记忆服务单元测试。"""

    @pytest.mark.asyncio
    async def test_initialize_memory_basic(self, db_session: AsyncSession):
        """测试基本记忆初始化。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(db_session, user_id)
        await db_session.commit()

        files = await memory_service.initialize_memory(
            db=db_session,
            user_id=user_id,
            child_id=child.id,
            caregiver_role="mother",
        )

        file_dict = files.to_dict()
        assert len(file_dict) == 7
        assert "AGENTS.md" in file_dict
        assert "SOUL.md" in file_dict
        assert "IDENTITY.md" in file_dict
        assert "USER.md" in file_dict
        assert "TOOLS.md" in file_dict
        assert "MEMORY.md" in file_dict

        # 检查是否有今天的日志
        today = date.today().isoformat()
        assert f"memory/{today}.md" in file_dict

    @pytest.mark.asyncio
    async def test_agents_md_contains_safety_rules(self, db_session: AsyncSession):
        """测试 AGENTS.md 包含安全红线规则。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(db_session, user_id)
        await db_session.commit()

        files = await memory_service.initialize_memory(
            db=db_session,
            user_id=user_id,
            child_id=child.id,
            caregiver_role="mother",
        )

        agents = files.agents
        assert "非诊断化原则" in agents
        assert "绝对不可" in agents
        assert "自闭症" in agents
        assert "信息安全" in agents
        assert "情感安全" in agents

    @pytest.mark.asyncio
    async def test_user_md_contains_child_info(self, db_session: AsyncSession):
        """测试 USER.md 包含正确的儿童信息。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(
            db_session,
            user_id,
            nickname="小贝",
            focus_themes=["language", "emotion", "motor"],
        )
        await db_session.commit()

        files = await memory_service.initialize_memory(
            db=db_session,
            user_id=user_id,
            child_id=child.id,
            caregiver_role="father",
            recent_situation="最近开始学说话了",
        )

        user_md = files.user
        assert "小贝" in user_md
        assert "爸爸" in user_md
        assert "语言发展" in user_md
        assert "情绪管理" in user_md
        assert "运动发展" in user_md
        assert "最近开始学说话了" in user_md

    @pytest.mark.asyncio
    async def test_identity_md_contains_role(self, db_session: AsyncSession):
        """测试 IDENTITY.md 包含正确的角色信息。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(db_session, user_id)
        await db_session.commit()

        files = await memory_service.initialize_memory(
            db=db_session,
            user_id=user_id,
            child_id=child.id,
            caregiver_role="grandparent",
        )

        identity = files.identity
        assert "祖辈长辈" in identity
        assert "AI Parenting 育儿助手" in identity

    @pytest.mark.asyncio
    async def test_tools_md_contains_skills(self, db_session: AsyncSession):
        """测试 TOOLS.md 包含可用技能。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(db_session, user_id)
        await db_session.commit()

        files = await memory_service.initialize_memory(
            db=db_session,
            user_id=user_id,
            child_id=child.id,
            caregiver_role="mother",
        )

        tools = files.tools
        assert "instant_help" in tools
        assert "plan_generation" in tools
        assert "sleep_analysis" in tools

    @pytest.mark.asyncio
    async def test_daily_log_contains_registration(self, db_session: AsyncSession):
        """测试首日日志包含注册信息。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(
            db_session, user_id, nickname="豆豆"
        )
        await db_session.commit()

        files = await memory_service.initialize_memory(
            db=db_session,
            user_id=user_id,
            child_id=child.id,
            caregiver_role="mother",
        )

        log = files.daily_log
        assert "新用户注册" in log
        assert "豆豆" in log
        assert "妈妈" in log

    @pytest.mark.asyncio
    async def test_initialize_nonexistent_child_raises(self, db_session: AsyncSession):
        """测试初始化不存在的儿童档案时抛出 ValueError。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        await db_session.commit()

        with pytest.raises(ValueError, match="找不到儿童档案"):
            await memory_service.initialize_memory(
                db=db_session,
                user_id=user_id,
                child_id=uuid.uuid4(),
                caregiver_role="mother",
            )

    @pytest.mark.asyncio
    async def test_soul_md_contains_values(self, db_session: AsyncSession):
        """测试 SOUL.md 包含核心价值观。"""
        user_id = uuid.uuid4()
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(db_session, user_id)
        await db_session.commit()

        files = await memory_service.initialize_memory(
            db=db_session,
            user_id=user_id,
            child_id=child.id,
            caregiver_role="mother",
        )

        soul = files.soul
        assert "世界观" in soul
        assert "人生观" in soul
        assert "价值观" in soul
        assert "温和而坚定" in soul


class TestMemoryHelpers:
    """记忆辅助方法测试。"""

    def test_update_user_md(self):
        """测试 USER.md 更新。"""
        result = memory_service.update_user_md(
            caregiver_role="mother",
            child_nickname="小北",
            child_age_months=24,
            child_stage="M24_36",
            focus_themes=["language", "cognition"],
            interaction_preferences={"沟通偏好": "喜欢简洁回复"},
        )
        assert "小北" in result
        assert "喜欢简洁回复" in result
        assert "（待观察）" in result  # 其他偏好仍为待观察

    def test_append_daily_log(self):
        """测试日志追加。"""
        original = "# 📅 2026-03-17 每日日志\n\n## 08:00 UTC\n\n- 初始日志\n\n---\n*后续*"
        result = memory_service.append_daily_log(original, "- 用户进行了语音对话")
        assert "用户进行了语音对话" in result
        assert "初始日志" in result
        assert "---" in result


# ---------------------------------------------------------------------------
# API 端点测试
# ---------------------------------------------------------------------------


class TestMemoryAPI:
    """记忆初始化 API 测试。"""

    @pytest.mark.asyncio
    async def test_initialize_memory_api(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """测试 POST /api/v1/memory/initialize 端点。"""
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(db_session, user_id)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/memory/initialize",
            json={
                "child_id": str(child.id),
                "caregiver_role": "mother",
                "recent_situation": "最近开始对积木感兴趣",
            },
        )
        assert resp.status_code == 201

        data = resp.json()
        assert data["success"] is True
        assert len(data["files"]) == 7
        assert "AGENTS.md" in data["files"]
        assert "SOUL.md" in data["files"]
        assert "USER.md" in data["files"]
        assert "积木" in data["files"]["USER.md"]

    @pytest.mark.asyncio
    async def test_initialize_memory_api_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """测试初始化不存在的儿童档案返回 404。"""
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        await _create_test_user(db_session, user_id)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/memory/initialize",
            json={
                "child_id": str(uuid.uuid4()),
                "caregiver_role": "father",
            },
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_initialize_memory_api_default_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """测试不提供 caregiver_role 时使用默认值。"""
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        await _create_test_user(db_session, user_id)
        child = await _create_test_child(db_session, user_id)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/memory/initialize",
            json={
                "child_id": str(child.id),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert "家长" in data["files"]["IDENTITY.md"]
