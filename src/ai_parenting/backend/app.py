"""FastAPI 应用入口。

组装所有路由，配置 CORS 和 OpenAPI 文档。
lifespan 事件自动建表并插入开发种子数据。
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator, Callable, Awaitable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from ai_parenting.backend.config import settings
from ai_parenting.backend.database import async_session_factory, engine
from ai_parenting.backend.models import Base
from ai_parenting.backend.routers import (
    admin,
    admin_panel,
    ai_sessions,
    auth,
    channels,
    children,
    consult_prep,
    devices,
    files,
    home,
    memory,
    messages,
    plans,
    records,
    skills,
    users,
    voice,
    webhooks,
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
    # P1-10: 生产环境应配置具体域名，开发环境允许所有来源
    cors_origins = ["*"] if settings.debug or settings.database_url.startswith("sqlite") else [
        "https://app.aiparenting.com",
        "https://admin.aiparenting.com",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- GZip 压缩中间件 (P2-11) ----------
    from starlette.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ---------- P2-12: 请求日志中间件 ----------
    @app.middleware("http")
    async def access_log_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "%s %s %d %dms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response

    # ---------- P1-8: API 简易限流中间件 ----------
    _rate_limit_store: dict[str, list[float]] = {}

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """基于 IP 的简易滑动窗口限流（60 次/分钟通用，AI 接口 10 次/分钟）。"""
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        now = time.monotonic()

        # AI 接口更严格的限流
        if "/ai/" in path:
            key = f"{client_ip}:ai"
            window = 60.0
            max_requests = 10
        elif "/auth/login" in path:
            key = f"{client_ip}:login"
            window = 60.0
            max_requests = 5
        else:
            key = f"{client_ip}:general"
            window = 60.0
            max_requests = 120

        timestamps = _rate_limit_store.get(key, [])
        # 清除超出窗口的旧请求
        timestamps = [t for t in timestamps if now - t < window]
        _rate_limit_store[key] = timestamps

        if len(timestamps) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )

        timestamps.append(now)
        _rate_limit_store[key] = timestamps
        return await call_next(request)

    # ---------- 全局异常处理 ----------
    @app.exception_handler(OperationalError)
    async def db_exception_handler(request: Request, exc: OperationalError) -> JSONResponse:
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
    app.include_router(channels.router, prefix="/api/v1")
    app.include_router(voice.router, prefix="/api/v1")
    app.include_router(skills.router, prefix="/api/v1")
    app.include_router(files.router, prefix="/api/v1")
    app.include_router(consult_prep.router, prefix="/api/v1")
    app.include_router(memory.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    # Admin 面板（不带 /api/v1 前缀，直接挂载到根路径）
    app.include_router(admin_panel.router)
    # Webhooks（不带 /api/v1 前缀，外部平台直接回调）
    app.include_router(webhooks.router)

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
