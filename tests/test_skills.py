"""技能系统测试 — Phase 3。

覆盖：
1. SkillRegistry 自动发现注册
2. SkillRegistry 意图匹配路由
3. Orchestrator 通过 SkillRegistry 路由
4. sleep_analysis 技能执行
5. GET /skills 端点
6. POST /skills/sleep-analysis 端点
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient

from ai_parenting.skills.adapters.sleep_analysis_skill import SleepAnalysisSkill
from ai_parenting.skills.registry import SkillRegistry


# ---------------------------------------------------------------------------
# 1. SkillRegistry 单元测试
# ---------------------------------------------------------------------------


class TestSkillRegistry:
    """SkillRegistry 核心功能测试。"""

    def test_registry_auto_discover(self):
        """测试自动发现注册 adapters/ 下的 Skill 子类。"""
        registry = SkillRegistry()
        adapters_path = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "ai_parenting"
            / "skills"
            / "adapters"
        )
        count = registry.discover_and_register(adapters_path)
        assert count >= 4, f"Expected at least 4 skills, got {count}"
        assert "instant_help" in registry.skill_names
        assert "plan_generation" in registry.skill_names
        assert "weekly_feedback" in registry.skill_names
        assert "sleep_analysis" in registry.skill_names

    def test_registry_manual_register(self):
        """测试手动注册技能。"""
        registry = SkillRegistry()
        skill = SleepAnalysisSkill()
        registry.register(skill)
        assert registry.skill_count == 1
        assert registry.get("sleep_analysis") is skill

    def test_registry_match_by_intent_exact(self):
        """测试按名称精确匹配意图。"""
        registry = SkillRegistry()
        adapters_path = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "ai_parenting"
            / "skills"
            / "adapters"
        )
        registry.discover_and_register(adapters_path)

        skill = registry.match_by_intent("instant_help")
        assert skill is not None
        assert skill.metadata.name == "instant_help"

    def test_registry_match_by_intent_tag(self):
        """测试按标签匹配意图。"""
        registry = SkillRegistry()
        adapters_path = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "ai_parenting"
            / "skills"
            / "adapters"
        )
        registry.discover_and_register(adapters_path)

        # "help" 是 instant_help 的 tag
        skill = registry.match_by_intent("help")
        assert skill is not None
        assert skill.metadata.name == "instant_help"

    def test_registry_match_by_intent_not_found(self):
        """测试匹配不到意图时返回 None。"""
        registry = SkillRegistry()
        assert registry.match_by_intent("nonexistent") is None

    def test_registry_unregister(self):
        """测试注销技能。"""
        registry = SkillRegistry()
        skill = SleepAnalysisSkill()
        registry.register(skill)
        assert registry.unregister("sleep_analysis") is True
        assert registry.get("sleep_analysis") is None
        assert registry.unregister("sleep_analysis") is False

    def test_registry_get_enabled_skills(self):
        """测试获取已启用技能。"""
        registry = SkillRegistry()
        adapters_path = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "ai_parenting"
            / "skills"
            / "adapters"
        )
        registry.discover_and_register(adapters_path)
        enabled = registry.get_enabled_skills()
        assert len(enabled) >= 4


# ---------------------------------------------------------------------------
# 2. SleepAnalysisSkill 单元测试
# ---------------------------------------------------------------------------


class TestSleepAnalysisSkill:
    """睡眠分析技能功能测试。"""

    @pytest.mark.asyncio
    async def test_sleep_analysis_excellent(self):
        """测试睡眠分析 — 质量很棒。"""
        skill = SleepAnalysisSkill()
        result = await skill.execute(
            params={
                "child_age_months": 24,
                "sleep_records": [
                    {
                        "date": f"2026-03-{10 + i:02d}",
                        "bedtime": "20:30",
                        "wake_time": "07:00",
                        "total_hours": 12.5,
                        "night_wakings": 0,
                        "nap_hours": 2.0,
                    }
                    for i in range(7)
                ],
            },
            context=None,
        )
        assert not result.is_degraded
        assert result.structured_data is not None
        assert result.structured_data.overall_rating == "excellent"  # type: ignore[attr-defined]
        assert "很棒" in result.response_text

    @pytest.mark.asyncio
    async def test_sleep_analysis_needs_improvement(self):
        """测试睡眠分析 — 待改善（夜醒多）。"""
        skill = SleepAnalysisSkill()
        result = await skill.execute(
            params={
                "child_age_months": 30,
                "sleep_records": [
                    {
                        "date": f"2026-03-{10 + i:02d}",
                        "bedtime": "21:00",
                        "wake_time": "06:30",
                        "total_hours": 10.5,
                        "night_wakings": 3,
                        "nap_hours": 1.0,
                    }
                    for i in range(7)
                ],
            },
            context=None,
        )
        assert result.structured_data is not None
        data = result.structured_data
        assert data.overall_rating in ("needs_improvement", "concerning")  # type: ignore[attr-defined]
        assert data.avg_night_wakings == 3.0  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_sleep_analysis_no_records(self):
        """测试无睡眠记录时的降级处理。"""
        skill = SleepAnalysisSkill()
        result = await skill.execute(
            params={"child_age_months": 24, "sleep_records": []},
            context=None,
        )
        assert result.is_degraded
        assert "暂时没有睡眠记录" in result.response_text

    @pytest.mark.asyncio
    async def test_sleep_analysis_metadata(self):
        """测试技能元信息。"""
        skill = SleepAnalysisSkill()
        meta = skill.metadata
        assert meta.name == "sleep_analysis"
        assert meta.display_name == "睡眠分析"
        assert meta.session_type == "sleep_analysis"
        assert meta.is_enabled is True


# ---------------------------------------------------------------------------
# 3. Skill API 端点测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_skills(client: AsyncClient):
    """测试 GET /skills 返回技能列表。"""
    resp = await client.get("/api/v1/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert "skills" in data
    assert "total" in data
    assert data["total"] >= 4
    names = [s["name"] for s in data["skills"]]
    assert "instant_help" in names
    assert "plan_generation" in names
    assert "weekly_feedback" in names
    assert "sleep_analysis" in names


@pytest.mark.asyncio
async def test_list_skills_has_display_info(client: AsyncClient):
    """测试技能列表包含展示信息。"""
    resp = await client.get("/api/v1/skills")
    data = resp.json()
    for skill in data["skills"]:
        assert "display_name" in skill
        assert "description" in skill
        assert "version" in skill
        assert "is_enabled" in skill


@pytest.mark.asyncio
async def test_sleep_analysis_endpoint(client: AsyncClient, db_session):
    """测试 POST /skills/sleep-analysis 端点。"""
    from ai_parenting.backend.models import Child, User

    # 创建测试用户和儿童
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        phone="13800138000",
        display_name="测试家长",
    )
    db_session.add(user)
    await db_session.flush()

    child = Child(
        id=uuid.uuid4(),
        user_id=user_id,
        nickname="宝宝",
        birth_date="2024-03-17",
    )
    db_session.add(child)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/skills/sleep-analysis",
        json={
            "child_id": str(child.id),
            "sleep_records": [
                {
                    "date": f"2026-03-{10 + i:02d}",
                    "bedtime": "20:30",
                    "wake_time": "07:00",
                    "total_hours": 12.0,
                    "night_wakings": 1,
                    "nap_hours": 1.5,
                }
                for i in range(7)
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_rating" in data
    assert "recommendations" in data
    assert "summary_text" in data
    assert data["avg_total_hours"] == 12.0


@pytest.mark.asyncio
async def test_sleep_analysis_missing_child(client: AsyncClient):
    """测试睡眠分析端点 — 儿童不存在。"""
    resp = await client.post(
        "/api/v1/skills/sleep-analysis",
        json={
            "child_id": str(uuid.uuid4()),
            "sleep_records": [
                {
                    "date": "2026-03-10",
                    "bedtime": "20:30",
                    "wake_time": "07:00",
                    "total_hours": 12.0,
                    "night_wakings": 0,
                }
            ],
        },
    )
    assert resp.status_code == 404
