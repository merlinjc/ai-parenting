"""Alembic 迁移环境配置。

支持同步和异步两种模式：
- 同步模式：用于 `alembic revision --autogenerate`（自动生成迁移脚本）
- 异步模式：用于 `alembic upgrade head`（执行迁移，支持 asyncpg）

数据库 URL 优先从环境变量 AIP_DATABASE_URL 读取，
未设置时使用 alembic.ini 中的默认值。
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 导入所有模型，确保 Base.metadata 包含全部表定义
from ai_parenting.backend.models import Base  # noqa: F401

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标 metadata（包含全部 12 个模型的表定义）
target_metadata = Base.metadata

# 从环境变量覆盖数据库 URL（优先级高于 alembic.ini）
database_url = os.environ.get("AIP_DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """离线模式迁移（生成 SQL 脚本，不连接数据库）。

    用法：alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在给定连接上执行迁移。"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,  # SQLite 需要 batch mode 来支持 ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步模式迁移（支持 asyncpg/aiosqlite）。

    用于生产环境 PostgreSQL（asyncpg）和开发环境 SQLite（aiosqlite）。
    """
    # 对于 aiosqlite，需要替换驱动名
    url = config.get_main_option("sqlalchemy.url")
    sync_url = url
    if "aiosqlite" in url:
        sync_url = url.replace("sqlite+aiosqlite", "sqlite")
    elif "asyncpg" in url:
        sync_url = url.replace("postgresql+asyncpg", "postgresql")

    # 使用同步引擎执行迁移（Alembic 核心是同步的）
    from sqlalchemy import create_engine

    connectable = create_engine(
        sync_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


def run_migrations_online() -> None:
    """在线模式迁移（连接数据库执行）。"""
    # 直接使用同步方式，兼容 SQLite 和 PostgreSQL
    url = config.get_main_option("sqlalchemy.url")
    sync_url = url
    if "aiosqlite" in url:
        sync_url = url.replace("sqlite+aiosqlite", "sqlite")
    elif "asyncpg" in url:
        sync_url = url.replace("postgresql+asyncpg", "postgresql")

    from sqlalchemy import create_engine

    connectable = create_engine(
        sync_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
