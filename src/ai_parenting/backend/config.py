"""应用配置。

使用 pydantic-settings 从环境变量加载配置，支持 .env 文件。
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置。"""

    # ---------- 数据库 ----------
    # 默认使用 SQLite 文件数据库（零配置开发），生产环境通过 AIP_DATABASE_URL 覆盖为 PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./ai_parenting_dev.db"
    database_echo: bool = False

    # ---------- 应用 ----------
    app_title: str = "AI Parenting API"
    app_version: str = "0.3.0"
    debug: bool = False

    # ---------- AI 编排 ----------
    ai_provider: str = "mock"

    # ---------- 推送 ----------
    push_provider: str = "mock"

    model_config = {"env_prefix": "AIP_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
