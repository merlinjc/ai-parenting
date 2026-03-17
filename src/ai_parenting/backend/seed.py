"""开发环境种子数据。

幂等插入默认 User（管理员）、普通 User 和 Child，与 iOS 客户端硬编码的 UUID 对齐。
每次 app 启动时调用，已存在则跳过。
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import hash_password
from ai_parenting.backend.models import Child, User

logger = logging.getLogger(__name__)

# 与 iOS 端硬编码对齐的 UUID
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_CHILD_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
ADMIN_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


async def seed_dev_data(session: AsyncSession) -> None:
    """幂等插入开发环境默认数据。"""

    # ---- Admin User ----
    result = await session.execute(select(User).where(User.id == ADMIN_USER_ID))
    if result.scalar_one_or_none() is None:
        admin = User(
            id=ADMIN_USER_ID,
            email="admin@aiparenting.dev",
            hashed_password=hash_password("admin123"),
            auth_provider="email",
            display_name="系统管理员",
            caregiver_role=None,
            timezone="Asia/Shanghai",
            is_admin=True,
        )
        session.add(admin)
        logger.info("Seed: created admin User %s (admin@aiparenting.dev)", ADMIN_USER_ID)
    else:
        # 确保已有用户拥有 admin 权限
        admin = await session.get(User, ADMIN_USER_ID)
        if admin and not admin.is_admin:
            admin.is_admin = True
            logger.info("Seed: upgraded User %s to admin", ADMIN_USER_ID)

    # ---- Default Dev User ----
    result = await session.execute(select(User).where(User.id == DEFAULT_USER_ID))
    if result.scalar_one_or_none() is None:
        user = User(
            id=DEFAULT_USER_ID,
            auth_provider="dev",
            display_name="开发用户",
            caregiver_role="father",
            timezone="Asia/Shanghai",
        )
        session.add(user)
        logger.info("Seed: created default User %s", DEFAULT_USER_ID)
    else:
        logger.info("Seed: default User %s already exists, skipping", DEFAULT_USER_ID)

    # ---- Child ----
    result = await session.execute(select(Child).where(Child.id == DEFAULT_CHILD_ID))
    if result.scalar_one_or_none() is None:
        child = Child(
            id=DEFAULT_CHILD_ID,
            user_id=DEFAULT_USER_ID,
            nickname="小宝",
            birth_year_month="2024-01",
            age_months=26,
            stage="24_36m",
            focus_themes=["language", "social"],
            risk_level="normal",
            onboarding_completed=True,
        )
        session.add(child)
        logger.info("Seed: created default Child %s", DEFAULT_CHILD_ID)
    else:
        logger.info("Seed: default Child %s already exists, skipping", DEFAULT_CHILD_ID)

    await session.commit()
