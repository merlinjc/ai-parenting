"""观察记录服务测试。"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import Child, User
from ai_parenting.backend.schemas import ChildCreate, RecordCreate
from ai_parenting.backend.services import child_service, record_service


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        auth_provider="email",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_child(db_session: AsyncSession, test_user: User) -> Child:
    child = await child_service.create_child(
        db_session, test_user.id,
        ChildCreate(nickname="小明", birth_year_month="2024-01")
    )
    return child


class TestCreateRecord:
    """创建记录测试。"""

    @pytest.mark.asyncio
    async def test_quick_check(self, db_session, test_child):
        data = RecordCreate(
            child_id=test_child.id,
            type="quick_check",
            tags=["今天说了新词", "主动跟人打招呼"],
        )
        record = await record_service.create_record(db_session, data)

        assert record.type == "quick_check"
        assert record.tags == ["今天说了新词", "主动跟人打招呼"]
        assert record.synced_to_plan is False

    @pytest.mark.asyncio
    async def test_event_record(self, db_session, test_child):
        data = RecordCreate(
            child_id=test_child.id,
            type="event",
            content="今天在公园遇到小朋友，主动分享了玩具",
            scene="playing",
            time_of_day="afternoon",
            theme="social",
        )
        record = await record_service.create_record(db_session, data)

        assert record.type == "event"
        assert record.content == "今天在公园遇到小朋友，主动分享了玩具"
        assert record.scene == "playing"

    @pytest.mark.asyncio
    async def test_voice_record(self, db_session, test_child):
        data = RecordCreate(
            child_id=test_child.id,
            type="voice",
            voice_url="https://example.com/audio/123.m4a",
            transcript="孩子今天吃饭很乖",
        )
        record = await record_service.create_record(db_session, data)
        assert record.voice_url == "https://example.com/audio/123.m4a"


class TestListRecords:
    """记录列表查询测试。"""

    @pytest.mark.asyncio
    async def test_list_empty(self, db_session, test_child):
        records, has_more, total = await record_service.list_records(
            db_session, test_child.id
        )
        assert records == []
        assert has_more is False
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_records(self, db_session, test_child):
        for i in range(5):
            await record_service.create_record(
                db_session,
                RecordCreate(
                    child_id=test_child.id,
                    type="quick_check",
                    tags=[f"tag_{i}"],
                )
            )

        records, has_more, total = await record_service.list_records(
            db_session, test_child.id, limit=3
        )
        assert len(records) == 3
        assert has_more is True
        assert total == 5

    @pytest.mark.asyncio
    async def test_filter_by_type(self, db_session, test_child):
        await record_service.create_record(
            db_session,
            RecordCreate(child_id=test_child.id, type="quick_check", tags=["tag"])
        )
        await record_service.create_record(
            db_session,
            RecordCreate(child_id=test_child.id, type="event", content="test")
        )

        records, _, total = await record_service.list_records(
            db_session, test_child.id, record_type="event"
        )
        assert len(records) == 1
        assert records[0].type == "event"


class TestGetRecentRecords:
    """最近记录查询测试。"""

    @pytest.mark.asyncio
    async def test_get_recent(self, db_session, test_child):
        for i in range(5):
            await record_service.create_record(
                db_session,
                RecordCreate(
                    child_id=test_child.id,
                    type="quick_check",
                    tags=[f"tag_{i}"],
                )
            )

        recent = await record_service.get_recent_records(
            db_session, test_child.id, count=3
        )
        assert len(recent) == 3
