"""语音 API 集成测试。

覆盖端点：
- POST /api/v1/voice/converse    — 语音对话核心端点
- POST /api/v1/voice/transcribe  — 云端 ASR Fallback
- POST /api/v1/voice/synthesize  — 云端 TTS Fallback

Phase 2 新增：
- 快速记录入库测试（record_id 验证）
- 查询今日计划测试
- 进度查询测试
- synthesize 端点测试
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Child, DayTask, Plan, User


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


async def _create_test_data(db: AsyncSession) -> tuple[uuid.UUID, uuid.UUID]:
    """创建测试用户和儿童，返回 (user_id, child_id)。"""
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    child_id = uuid.UUID("00000000-0000-0000-0000-000000000010")

    user = User(
        id=user_id,
        email="test@example.com",
        auth_provider="email",
        display_name="Test User",
    )
    child = Child(
        id=child_id,
        user_id=user_id,
        nickname="小明",
        birth_year_month="2024-03",
        age_months=24,
        stage="24_36m",
    )
    db.add(user)
    db.add(child)
    await db.commit()
    return user_id, child_id


async def _create_test_plan_with_task(
    db: AsyncSession, child_id: uuid.UUID
) -> uuid.UUID:
    """创建测试计划和今日任务，返回 plan_id。"""
    from datetime import date, timedelta

    plan_id = uuid.UUID("00000000-0000-0000-0000-000000000100")
    plan = Plan(
        id=plan_id,
        child_id=child_id,
        version=1,
        status="active",
        title="语言训练周计划",
        primary_goal="提升表达能力",
        focus_theme="language",
        stage="24_36m",
        risk_level_at_creation="normal",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=6),
        current_day=1,
        completion_rate=0.0,
    )
    db.add(plan)
    await db.flush()

    task = DayTask(
        plan_id=plan_id,
        day_number=1,
        main_exercise_title="模仿游戏",
        main_exercise_description="用勺子假装喂玩偶，鼓励宝宝模仿家长的动作",
        natural_embed_title="吃饭时的语言互动",
        natural_embed_description="吃饭时说出食物名称",
        demo_script="妈妈先喂一口，然后说：宝宝也来喂小熊好不好？",
        observation_point="观察宝宝是否主动拿起勺子模仿",
        completion_status="pending",
    )
    db.add(task)
    await db.commit()
    return plan_id


# ---------------------------------------------------------------------------
# Voice Converse 测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_converse_success(client: AsyncClient, db_session: AsyncSession):
    """正常语音对话应返回 200 和有效回复。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "今天的训练任务是什么？",
            "child_id": str(child_id),
            "confidence": 0.95,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "reply_text" in data
    assert "intent" in data
    assert isinstance(data["reply_text"], str)
    assert len(data["reply_text"]) > 0


@pytest.mark.asyncio
async def test_voice_converse_empty_transcript(client: AsyncClient, db_session: AsyncSession):
    """空转写文本应返回 422（min_length=1 校验）。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "",
            "child_id": str(child_id),
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_voice_converse_missing_child_id(client: AsyncClient, db_session: AsyncSession):
    """缺少 child_id 应返回 422。"""
    await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "测试内容",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_voice_converse_low_confidence(client: AsyncClient, db_session: AsyncSession):
    """低置信度请求应正常处理（后端不拒绝，仅在响应中标记 fallback 建议）。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "宝宝今天什么",
            "child_id": str(child_id),
            "confidence": 0.3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "should_fallback_to_cloud_asr" in data


@pytest.mark.asyncio
async def test_voice_converse_no_confidence(client: AsyncClient, db_session: AsyncSession):
    """不传置信度（None）应正常处理。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "记录一下宝宝自己穿鞋了",
            "child_id": str(child_id),
        },
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Phase 2: Quick Record 入库测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_quick_record_creates_record(client: AsyncClient, db_session: AsyncSession):
    """语音快速记录应真实创建 Record，响应包含 record_id。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "记录一下宝宝自己穿鞋了",
            "child_id": str(child_id),
            "confidence": 0.92,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "quick_record"
    assert "已记录" in data["reply_text"]
    # Phase 2: record_id 应当返回
    assert "record_id" in data


@pytest.mark.asyncio
async def test_voice_quick_record_content_extraction(client: AsyncClient, db_session: AsyncSession):
    """快速记录应提取关键词后面的内容。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "帮我记一下宝宝今天叠了三层积木",
            "child_id": str(child_id),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "quick_record"
    # 应包含 "积木" 相关内容
    assert "积木" in data["reply_text"] or "积木" in str(data.get("action_taken", {}))


# ---------------------------------------------------------------------------
# Phase 2: Query Plan 测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_query_plan_with_active_plan(client: AsyncClient, db_session: AsyncSession):
    """有活跃计划时，语音查询应返回今日任务详情。"""
    _, child_id = await _create_test_data(db_session)
    await _create_test_plan_with_task(db_session, child_id)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "今天做什么训练",
            "child_id": str(child_id),
            "confidence": 0.88,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "query_plan"
    # 应包含计划名称或任务主题
    assert "模仿游戏" in data["reply_text"] or "语言训练" in data["reply_text"]


@pytest.mark.asyncio
async def test_voice_query_plan_no_active_plan(client: AsyncClient, db_session: AsyncSession):
    """无活跃计划时应返回友好提示。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "今天做什么",
            "child_id": str(child_id),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "query_plan"
    assert "没有" in data["reply_text"] or "创建" in data["reply_text"]


# ---------------------------------------------------------------------------
# Phase 2: Query Progress 测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_query_progress(client: AsyncClient, db_session: AsyncSession):
    """进度查询应返回连续打卡天数和计划信息。"""
    _, child_id = await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/converse",
        json={
            "transcript": "这周完成多少了",
            "child_id": str(child_id),
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "query_progress"


# ---------------------------------------------------------------------------
# Voice Transcribe 测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_transcribe(client: AsyncClient, db_session: AsyncSession):
    """云端 ASR Fallback 端点应返回 200。"""
    await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/transcribe",
        json={
            "audio_url": "https://storage.example.com/audio/test.m4a",
            "language": "zh-CN",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "transcript" in data
    assert "confidence" in data


# ---------------------------------------------------------------------------
# Phase 2: Voice Synthesize 测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_voice_synthesize(client: AsyncClient, db_session: AsyncSession):
    """云端 TTS Fallback 端点应返回 200。"""
    await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/synthesize",
        json={
            "text": "今天宝宝表现很棒",
            "voice": "zh-CN",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "audio_url" in data
    assert "provider" in data


@pytest.mark.asyncio
async def test_voice_synthesize_empty_text(client: AsyncClient, db_session: AsyncSession):
    """空文本应返回 422。"""
    await _create_test_data(db_session)

    resp = await client.post(
        "/api/v1/voice/synthesize",
        json={
            "text": "",
        },
    )
    assert resp.status_code == 422
