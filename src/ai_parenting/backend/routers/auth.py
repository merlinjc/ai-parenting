"""认证路由 — 注册、登录、Token 刷新。

提供基于邮箱+密码的用户认证体系。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from ai_parenting.backend.database import get_db
from ai_parenting.backend.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """用户注册请求。"""

    email: str = Field(..., min_length=3, max_length=255, description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    display_name: str | None = Field(None, max_length=100)
    caregiver_role: str | None = None


class LoginRequest(BaseModel):
    """用户登录请求。"""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Token 响应。"""

    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """用户注册。

    创建新用户并返回 JWT token。
    """
    # 检查邮箱是否已存在
    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # 创建用户
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        caregiver_role=body.caregiver_role,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # 生成 token
    token = create_access_token(user.id)

    return TokenResponse(access_token=token, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """用户登录。

    验证邮箱+密码，返回 JWT token。
    """
    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_id=user.id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """刷新 Token。

    需要携带有效的 JWT token（或 X-User-Id），返回新的 token。
    """
    # 验证用户存在
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user_id=user.id)
