"""JWT 认证工具模块。

提供 JWT Token 创建/验证、密码加密/校验、以及 FastAPI 依赖注入。
支持 Bearer Token 认证，同时兼容旧的 X-User-Id Header 模式（渐进迁移）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.config import settings
from ai_parenting.backend.database import get_db

# ---------------------------------------------------------------------------
# 密码加密
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码进行 bcrypt 加密。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与 hash 是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT Token
# ---------------------------------------------------------------------------

# JWT 配置：从环境变量读取，有合理默认值
_SECRET_KEY = getattr(settings, "jwt_secret_key", "ai-parenting-dev-secret-key-change-in-prod")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天


def create_access_token(
    user_id: uuid.UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建 JWT access token。

    Args:
        user_id: 用户 UUID。
        expires_delta: 过期时间增量，默认 7 天。

    Returns:
        JWT token 字符串。
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """解码并验证 JWT token，返回 user_id。

    Raises:
        HTTPException: token 无效或过期。
    """
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return uuid.UUID(user_id_str)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )


# ---------------------------------------------------------------------------
# FastAPI 依赖：获取当前用户 ID
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)
_DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    x_user_id: str | None = Header(None),
) -> uuid.UUID:
    """统一用户身份获取依赖。

    优先级：
    1. Bearer Token（JWT 认证）
    2. X-User-Id Header（兼容模式）
    3. 默认开发用户 ID

    渐进迁移：先支持两种方式，后续可移除 X-User-Id。
    """
    # 优先使用 JWT
    if credentials is not None:
        return decode_access_token(credentials.credentials)

    # 兼容旧的 X-User-Id header
    if x_user_id:
        try:
            return uuid.UUID(x_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-User-Id header",
            )

    # 开发环境默认用户
    return _DEFAULT_USER_ID
