"""FastAPI 应用入口。

组装所有路由，配置 CORS 和 OpenAPI 文档。
lifespan 事件自动建表并插入开发种子数据。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from ai_parenting.backend.config import settings
from ai_parenting.backend.database import async_session_factory, engine
from ai_parenting.backend.models import Base
from ai_parenting.backend.routers import (
    ai_sessions,
    auth,
    children,
    consult_prep,
    devices,
    files,
    home,
    messages,
    plans,
    records,
    users,
    weekly_feedbacks,
)
from ai_parenting.backend.scheduler import start_scheduler, stop_scheduler
from ai_parenting.backend.schemas import HealthResponse
from ai_parenting.backend.seed import seed_dev_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动时建表 + 插入种子数据，关闭时清理引擎。"""
    # ---- startup ----
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified (url=%s)", settings.database_url)

    async with async_session_factory() as session:
        await seed_dev_data(session)
    logger.info("Seed data initialized")

    # 启动定时任务调度器
    start_scheduler()

    yield

    # ---- shutdown ----
    stop_scheduler()
    await engine.dispose()


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        description="18-48个月幼儿家长辅助型 AI 产品 — 业务后端 API",
        lifespan=lifespan,
    )

    # ---------- CORS 中间件 ----------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 开发环境允许所有来源，生产环境需缩窄
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- 全局异常处理 ----------
    @app.exception_handler(OperationalError)
    async def db_exception_handler(request: Request, exc: OperationalError):
        logger.error("Database error: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "Database unavailable. Please check the database connection."},
        )

    # ---------- 路由注册 ----------
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(children.router, prefix="/api/v1")
    app.include_router(records.router, prefix="/api/v1")
    app.include_router(plans.router, prefix="/api/v1")
    app.include_router(ai_sessions.router, prefix="/api/v1")
    app.include_router(home.router, prefix="/api/v1")
    app.include_router(weekly_feedbacks.router, prefix="/api/v1")
    app.include_router(messages.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(devices.router, prefix="/api/v1")
    app.include_router(files.router, prefix="/api/v1")
    app.include_router(consult_prep.router, prefix="/api/v1")

    # ---------- 静态文件（上传文件访问） ----------
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    # ---------- 健康检查 ----------
    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(version=settings.app_version)

    return app


app = create_app()
