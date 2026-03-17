"""OpenClaw 记忆管理路由。

提供记忆初始化 API，在用户完成 Onboarding 后
为其创建 OpenClaw 层级记忆文件系统。

端点：
- POST /memory/initialize  — 初始化记忆（Onboarding 完成后调用）
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import MemoryInitRequest, MemoryInitResponse
from ai_parenting.backend.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/initialize", response_model=MemoryInitResponse, status_code=201)
async def initialize_memory(
    body: MemoryInitRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> MemoryInitResponse:
    """初始化 OpenClaw 记忆文件系统。

    在用户完成 Onboarding（注册 + 创建儿童档案）后调用。
    基于用户档案和儿童信息生成全部 7 个层级的记忆文件：
    AGENTS.md, SOUL.md, IDENTITY.md, USER.md, TOOLS.md, MEMORY.md, memory/YYYY-MM-DD.md

    Returns:
        201: 记忆文件初始化成功，返回全部文件内容。
        404: 找不到指定的儿童档案。
    """
    try:
        files = await memory_service.initialize_memory(
            db=db,
            user_id=user_id,
            child_id=body.child_id,
            caregiver_role=body.caregiver_role,
            recent_situation=body.recent_situation,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MemoryInitResponse(
        success=True,
        files=files.to_dict(),
        message=f"已初始化 {len(files.to_dict())} 个记忆文件",
    )
