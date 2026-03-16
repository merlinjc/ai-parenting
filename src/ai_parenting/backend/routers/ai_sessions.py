"""AI 会话路由。

提供即时求助请求/响应和 AI 会话状态查询。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.database import get_db
from ai_parenting.backend.deps import get_orchestrator
from ai_parenting.backend.schemas import AISessionResponse, InstantHelpRequest
from ai_parenting.backend.services.ai_session_service import (
    create_instant_help_session,
    get_session,
)
from ai_parenting.orchestrator import Orchestrator

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/instant-help", response_model=AISessionResponse, status_code=201)
async def instant_help(
    body: InstantHelpRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> AISessionResponse:
    """即时求助：创建 AI 会话并返回结果。

    同步模式：等待 AI 调用完成后返回完整结果。
    超时自动降级为 degraded_result。
    """
    try:
        session = await create_instant_help_session(
            db,
            orchestrator,
            child_id=body.child_id,
            scenario=body.scenario,
            input_text=body.input_text,
            plan_id=body.plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return AISessionResponse.model_validate(session)


@router.get("/sessions/{session_id}", response_model=AISessionResponse)
async def get_ai_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AISessionResponse:
    """获取 AI 会话状态和结果（支持轮询）。"""
    session = await get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return AISessionResponse.model_validate(session)
