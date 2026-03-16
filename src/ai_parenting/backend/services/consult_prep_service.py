"""咨询准备服务。

聚合最近观察记录、AI 会话中的咨询建议、风险评级信息，
为家长就诊/咨询提供结构化的准备数据。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import AISession, Child, Record


async def get_consult_prep_data(
    db: AsyncSession,
    child_id: uuid.UUID,
) -> dict:
    """聚合咨询准备数据。

    Returns:
        结构化的就诊准备字典，包含：
        - child_info: 儿童基本信息
        - recent_records: 最近 2 周的观察记录摘要
        - ai_suggestions: AI 会话中的咨询建议
        - checklist: 就诊准备清单
    """
    # 获取儿童信息
    child = await db.get(Child, child_id)
    if child is None:
        raise ValueError(f"Child {child_id} not found")

    # 最近 14 天的记录
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    records_result = await db.execute(
        select(Record)
        .where(
            Record.child_id == child_id,
            Record.created_at >= two_weeks_ago,
        )
        .order_by(Record.created_at.desc())
        .limit(20)
    )
    recent_records = list(records_result.scalars().all())

    # 最近的 AI 会话（包含即时求助）
    sessions_result = await db.execute(
        select(AISession)
        .where(
            AISession.child_id == child_id,
            AISession.session_type == "instant_help",
            AISession.status == "completed",
            AISession.created_at >= two_weeks_ago,
        )
        .order_by(AISession.created_at.desc())
        .limit(10)
    )
    ai_sessions = list(sessions_result.scalars().all())

    # 提取 AI 建议中的咨询相关内容
    ai_suggestions = []
    for session in ai_sessions:
        if session.result and isinstance(session.result, dict):
            result = session.result
            if result.get("suggest_consult_prep"):
                ai_suggestions.append({
                    "date": session.created_at.isoformat(),
                    "scenario": session.input_scenario,
                    "reason": result.get("consult_prep_reason", ""),
                    "summary": result.get("answer", "")[:200],
                })

    # 构建记录摘要
    record_summaries = []
    for record in recent_records:
        record_summaries.append({
            "date": record.created_at.isoformat(),
            "type": record.type,
            "content": (record.content or record.transcript or "")[:200],
            "tags": record.tags or [],
            "theme": record.theme,
        })

    # 就诊准备清单
    checklist = [
        {"item": "带上孩子近期的成长记录（本应用中的记录可截图）", "checked": False},
        {"item": "记录想要咨询的具体问题（2-3 个为佳）", "checked": False},
        {"item": "带上孩子的保健手册和既往体检记录", "checked": False},
        {"item": "观察并记录孩子最近的典型行为表现", "checked": False},
        {"item": "了解当地儿童发展评估机构信息", "checked": False},
    ]

    return {
        "child_info": {
            "nickname": child.nickname,
            "age_months": child.age_months,
            "stage": child.stage,
            "risk_level": child.risk_level,
            "focus_themes": child.focus_themes or [],
        },
        "recent_records": record_summaries,
        "ai_suggestions": ai_suggestions,
        "checklist": checklist,
        "record_count": len(recent_records),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
