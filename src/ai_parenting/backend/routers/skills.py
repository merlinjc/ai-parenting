"""技能管理路由。

Phase 3：提供技能列表查询和独立技能执行端点。
- GET /skills — 获取所有已注册技能信息（供 iOS 技能列表页使用）
- POST /skills/sleep-analysis — 执行睡眠分析技能
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.deps import get_skill_registry
from ai_parenting.backend.schemas import (
    SkillInfoResponse,
    SkillListResponse,
    SleepAnalysisRequest,
    SleepAnalysisResponse,
)
from ai_parenting.backend.services.child_service import get_child
from ai_parenting.skills.registry import SkillRegistry

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=SkillListResponse)
async def list_skills(
    user_id: uuid.UUID = Depends(get_current_user_id),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SkillListResponse:
    """获取所有已注册的技能列表。

    供 iOS 端 SkillListView 动态渲染技能卡片。
    """
    skills_meta = registry.get_all_metadata()
    items = [
        SkillInfoResponse(
            name=m.name,
            display_name=m.display_name,
            description=m.description,
            version=m.version,
            icon=m.icon,
            tags=m.tags,
            is_enabled=m.is_enabled,
            session_type=m.session_type,
        )
        for m in skills_meta
    ]
    return SkillListResponse(skills=items, total=len(items))


@router.post("/sleep-analysis", response_model=SleepAnalysisResponse, status_code=200)
async def run_sleep_analysis(
    body: SleepAnalysisRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SleepAnalysisResponse:
    """执行睡眠分析。

    接收 7 天睡眠记录，返回评估结果和建议。
    """
    skill = registry.get("sleep_analysis")
    if skill is None:
        raise HTTPException(status_code=503, detail="Sleep analysis skill not available")

    # P1-11: 获取儿童月龄并校验所有权
    child = await get_child(db, body.child_id)
    if child is None:
        raise HTTPException(status_code=404, detail=f"Child {body.child_id} not found")
    if child.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权操作此儿童的数据")

    result = await skill.execute(
        params={
            "child_age_months": child.age_months,
            "sleep_records": body.sleep_records,
        },
        context=None,
    )

    if result.structured_data is None:
        raise HTTPException(status_code=422, detail=result.response_text)

    data = result.structured_data
    return SleepAnalysisResponse(
        overall_rating=data.overall_rating,  # type: ignore[attr-defined]
        rating_display=data.rating_display,  # type: ignore[attr-defined]
        avg_total_hours=data.avg_total_hours,  # type: ignore[attr-defined]
        avg_night_wakings=data.avg_night_wakings,  # type: ignore[attr-defined]
        bedtime_consistency=data.bedtime_consistency,  # type: ignore[attr-defined]
        summary_text=data.summary_text,  # type: ignore[attr-defined]
        recommendations=data.recommendations,  # type: ignore[attr-defined]
        age_reference=data.age_reference,  # type: ignore[attr-defined]
    )
