"""SQLAlchemy 异步引擎与会话工厂。

提供 async_session_factory 和 FastAPI 依赖注入 get_db。
支持 SQLite（开发）和 PostgreSQL（生产）双数据库后端。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_parenting.backend.config import settings

# SQLite 需要 check_same_thread=False，PostgreSQL 不需要此参数
_is_sqlite = settings.database_url.startswith("sqlite")
_engine_kwargs: dict = {
    "echo": settings.database_echo,
}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    settings.database_url,
    **_engine_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：获取数据库会话。"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
