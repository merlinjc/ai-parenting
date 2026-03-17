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
    hunyuan_api_key: str = ""
    hunyuan_base_url: str = "https://api.hunyuan.cloud.tencent.com/v1"
    hunyuan_model: str = "hunyuan-lite"

    # ---------- 推送 ----------
    push_provider: str = "channel_router"  # channel_router | mock
    # 推送引擎模式：smart（SmartPushEngine 时区感知调度） / legacy（固定 UTC Cron）
    push_engine_mode: str = "smart"

    # ---------- 渠道配置 ----------
    # 微信服务号
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_token: str = ""
    wechat_aes_key: str = ""

    # APNs
    apns_bundle_id: str = "com.aiparenting.app"
    apns_key_path: str = ""
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_use_sandbox: bool = True

    # OpenClaw Gateway
    openclaw_ws_url: str = "ws://localhost:8765"
    openclaw_api_key: str = ""

    # ---------- 语音服务（云端 Fallback，ASR/TTS 主路径为 iOS 原生） ----------
    # iOS 端优先使用 Speech.framework (ASR) + AVSpeechSynthesizer (TTS)
    # 以下云端配置仅在 iOS ASR 置信度低或需要高品质 TTS 时作为 fallback 使用
    voice_stt_provider: str = "ios_native"  # ios_native | tencent_cloud | mock
    voice_tts_provider: str = "ios_native"  # ios_native | tencent_cloud | mock
    voice_asr_confidence_threshold: float = 0.6  # iOS ASR 置信度低于此值时降级到云端
    tencent_asr_app_id: str = ""
    tencent_asr_secret_key: str = ""
    tencent_tts_app_id: str = ""
    tencent_tts_secret_key: str = ""

    # ---------- JWT 认证 ----------
    jwt_secret_key: str = "ai-parenting-dev-secret-key-change-in-prod"

    model_config = {"env_prefix": "AIP_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
