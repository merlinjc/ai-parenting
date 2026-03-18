"""API 请求/响应 Pydantic 模型。

为 FastAPI 路由定义类型安全的请求体和响应体。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field, PlainSerializer, field_validator


def _serialize_datetime(dt: datetime) -> str:
    """序列化 datetime，确保输出带 Z 时区后缀（ISO 8601）。

    SQLite 存储的 datetime 不含时区信息，Pydantic 默认序列化为
    ``2026-03-16T03:44:08`` 格式，iOS 端 ISO8601DateFormatter 无法解析。
    统一转为 ``2026-03-16T03:44:08Z`` 格式。
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# 带 Z 后缀的 datetime 类型注解，用于响应模型
UTCDatetime = Annotated[datetime, PlainSerializer(_serialize_datetime, return_type=str)]


# ---------------------------------------------------------------------------
# 通用
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


# ---------------------------------------------------------------------------
# Child（儿童档案）
# ---------------------------------------------------------------------------


class ChildCreate(BaseModel):
    """创建儿童档案请求。"""

    nickname: str = Field(..., min_length=1, max_length=50)
    birth_year_month: str = Field(
        ..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="格式 YYYY-MM"
    )
    focus_themes: list[str] = Field(default_factory=list)
    risk_level: str = Field(default="normal")

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        if v not in ("normal", "attention", "consult"):
            raise ValueError("risk_level 必须为 normal/attention/consult")
        return v


class ChildUpdate(BaseModel):
    """更新儿童档案请求。"""

    nickname: str | None = Field(None, min_length=1, max_length=50)
    focus_themes: list[str] | None = None
    risk_level: str | None = None

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str | None) -> str | None:
        if v is not None and v not in ("normal", "attention", "consult"):
            raise ValueError("risk_level 必须为 normal/attention/consult")
        return v


class ChildResponse(BaseModel):
    """儿童档案响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    nickname: str
    birth_year_month: str
    age_months: int
    stage: str
    focus_themes: list[str] | None
    risk_level: str
    onboarding_completed: bool
    created_at: UTCDatetime
    updated_at: UTCDatetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Record（观察记录）
# ---------------------------------------------------------------------------


class RecordCreate(BaseModel):
    """创建观察记录请求。"""

    child_id: uuid.UUID
    type: str = Field(..., description="quick_check/event/voice")
    tags: list[str] | None = None
    content: str | None = None
    voice_url: str | None = None
    transcript: str | None = None
    scene: str | None = None
    time_of_day: str | None = None
    theme: str | None = None
    source_plan_id: uuid.UUID | None = None
    source_session_id: uuid.UUID | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("quick_check", "event", "voice"):
            raise ValueError("type 必须为 quick_check/event/voice")
        return v


class RecordResponse(BaseModel):
    """观察记录响应。"""

    id: uuid.UUID
    child_id: uuid.UUID
    type: str
    tags: list[str] | None
    content: str | None
    voice_url: str | None
    transcript: str | None
    scene: str | None
    time_of_day: str | None
    theme: str | None
    source_plan_id: uuid.UUID | None
    source_session_id: uuid.UUID | None
    synced_to_plan: bool
    created_at: UTCDatetime

    model_config = {"from_attributes": True}


class RecordListResponse(BaseModel):
    """记录列表响应（含分页）。"""

    records: list[RecordResponse]
    has_more: bool
    total: int


# ---------------------------------------------------------------------------
# Plan（微计划）
# ---------------------------------------------------------------------------


class DayTaskResponse(BaseModel):
    """日任务响应。"""

    id: uuid.UUID
    plan_id: uuid.UUID
    day_number: int
    main_exercise_title: str
    main_exercise_description: str
    natural_embed_title: str
    natural_embed_description: str
    demo_script: str
    observation_point: str
    completion_status: str
    completed_at: UTCDatetime | None

    model_config = {"from_attributes": True}


class DayTaskCompletionUpdate(BaseModel):
    """更新日任务完成状态。"""

    completion_status: str

    @field_validator("completion_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("pending", "executed", "partial", "needs_record"):
            raise ValueError("completion_status 必须为 pending/executed/partial/needs_record")
        return v


class PlanResponse(BaseModel):
    """微计划响应。"""

    id: uuid.UUID
    child_id: uuid.UUID
    version: int
    status: str
    title: str
    primary_goal: str
    focus_theme: str
    priority_scenes: list[str] | None
    stage: str
    risk_level_at_creation: str
    start_date: date
    end_date: date
    current_day: int
    completion_rate: float
    observation_candidates: Any | None
    next_week_context: str | None
    next_week_direction: str | None
    weekend_review_prompt: str | None
    conservative_note: str | None
    ai_generation_id: uuid.UUID | None
    created_at: UTCDatetime
    updated_at: UTCDatetime
    day_tasks: list[DayTaskResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PlanInitialContext(BaseModel):
    """首次计划生成的引导上下文。

    在引导流程中收集的个性化信号，用于增强首次计划的个性化程度。
    所有字段均为可选，未填写时使用空字符串。
    """

    caregiver_role: str = ""
    recent_situation: str = ""
    daily_routine_note: str = ""
    interaction_style: str = ""
    current_concern: str = ""
    best_moment: str = ""


class PlanCreateRequest(BaseModel):
    """创建微计划请求（触发 AI 生成）。

    initial_context 仅在首次引导完成后自动创建时传入，
    后续手动创建计划时为 None。
    """

    child_id: uuid.UUID
    initial_context: PlanInitialContext | None = None


class PlanWithFeedbackStatus(BaseModel):
    """计划响应 + 周反馈状态（计划页 API）。"""

    plan: PlanResponse
    weekly_feedback_status: str | None = None


# ---------------------------------------------------------------------------
# AISession（AI 会话）
# ---------------------------------------------------------------------------


class InstantHelpRequest(BaseModel):
    """即时求助请求。"""

    child_id: uuid.UUID
    scenario: str | None = None
    input_text: str | None = None
    plan_id: uuid.UUID | None = None


class AISessionResponse(BaseModel):
    """AI 会话响应。"""

    id: uuid.UUID
    child_id: uuid.UUID
    session_type: str
    status: str
    input_scenario: str | None
    input_text: str | None
    context_snapshot: dict | None
    result: dict | None
    error_info: str | None
    degraded_result: dict | None
    model_provider: str | None
    model_version: str | None
    prompt_template_id: str | None
    latency_ms: int | None
    retry_count: int
    created_at: UTCDatetime
    completed_at: UTCDatetime | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# WeeklyFeedback（周反馈）
# ---------------------------------------------------------------------------


class WeeklyFeedbackCreateRequest(BaseModel):
    """创建周反馈请求（触发 AI 生成）。"""

    plan_id: uuid.UUID


class WeeklyFeedbackDecisionRequest(BaseModel):
    """周反馈决策回写请求。"""

    decision: str

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("continue", "lower_difficulty", "change_focus"):
            raise ValueError("decision 必须为 continue/lower_difficulty/change_focus")
        return v


class WeeklyFeedbackResponse(BaseModel):
    """周反馈响应。"""

    id: uuid.UUID
    plan_id: uuid.UUID
    child_id: uuid.UUID
    status: str
    positive_changes: dict | None = None
    opportunities: dict | None = None
    summary_text: str | None = None
    decision_options: dict | None = None
    selected_decision: str | None = None
    conservative_path_note: str | None = None
    record_count_this_week: int = 0
    completion_rate_this_week: float = 0.0
    ai_generation_id: uuid.UUID | None = None
    error_info: str | None = None
    created_at: UTCDatetime
    viewed_at: UTCDatetime | None = None
    decided_at: UTCDatetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Message（消息）
# ---------------------------------------------------------------------------


class MessageResponse(BaseModel):
    """消息响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    child_id: uuid.UUID | None = None
    type: str
    title: str
    body: str
    summary: str
    target_page: str | None = None
    target_params: dict | None = None
    requires_preview: bool = True
    read_status: str
    push_status: str
    push_sent_at: UTCDatetime | None = None
    push_delivered_at: UTCDatetime | None = None
    clicked_at: UTCDatetime | None = None
    created_at: UTCDatetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """消息列表响应（含分页）。"""

    messages: list[MessageResponse]
    has_more: bool
    total_unread: int


class MessageUpdateRequest(BaseModel):
    """更新消息状态请求。"""

    read_status: str

    @field_validator("read_status")
    @classmethod
    def validate_read_status(cls, v: str) -> str:
        if v not in ("unread", "read", "processed"):
            raise ValueError("read_status 必须为 unread/read/processed")
        return v


class UnreadCountResponse(BaseModel):
    """未读消息计数响应。"""

    unread_count: int


class PlanListResponse(BaseModel):
    """计划列表响应（含分页）。"""

    plans: list[PlanResponse]
    has_more: bool
    total: int


class HomeSummaryResponse(BaseModel):
    """首页聚合响应。"""

    child: ChildResponse | None = None
    active_plan: PlanResponse | None = None
    today_task: DayTaskResponse | None = None
    recent_records: list[RecordResponse] = Field(default_factory=list)
    unread_count: int = 0
    weekly_feedback_status: str | None = None
    weekly_feedback_id: uuid.UUID | None = None
    greeting: str = ""
    streak_days: int = 0
    week_day_statuses: list[str] = Field(default_factory=list)
    plan_generating: bool = False  # 是否有正在进行中的计划生成会话


# ---------------------------------------------------------------------------
# User（用户档案）
# ---------------------------------------------------------------------------


class UserProfileResponse(BaseModel):
    """用户档案响应。"""

    id: uuid.UUID
    display_name: str | None = None
    caregiver_role: str | None = None
    timezone: str = "Asia/Shanghai"
    push_enabled: bool = True
    created_at: UTCDatetime
    updated_at: UTCDatetime
    children: list[ChildResponse] = Field(default_factory=list)
    channel_bindings: list["ChannelBindingResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """更新用户档案请求。"""

    display_name: str | None = Field(None, min_length=1, max_length=100)
    caregiver_role: str | None = None
    timezone: str | None = None
    push_enabled: bool | None = None

    @field_validator("caregiver_role")
    @classmethod
    def validate_caregiver_role(cls, v: str | None) -> str | None:
        if v is not None and v not in ("mother", "father", "grandparent", "other"):
            raise ValueError(
                "caregiver_role 必须为 mother/father/grandparent/other"
            )
        return v


# ---------------------------------------------------------------------------
# Device（设备注册）
# ---------------------------------------------------------------------------


class DeviceRegisterRequest(BaseModel):
    """设备注册/更新请求。"""

    push_token: str | None = None
    platform: str = Field(..., description="iOS/Android")
    app_version: str = Field(..., min_length=1, max_length=20)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v not in ("iOS", "Android"):
            raise ValueError("platform 必须为 iOS/Android")
        return v


class DeviceResponse(BaseModel):
    """设备响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    push_token: str | None = None
    platform: str
    app_version: str
    last_active_at: UTCDatetime
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Plan Focus Note（加入本周关注）
# ---------------------------------------------------------------------------


class PlanFocusNoteUpdate(BaseModel):
    """加入本周关注请求（追加关注内容到计划的 next_week_context）。"""

    note: str = Field(..., min_length=1, max_length=2000, description="关注内容摘要")


# ---------------------------------------------------------------------------
# File Upload（文件上传）
# ---------------------------------------------------------------------------


class FileUploadResponse(BaseModel):
    """文件上传响应。"""

    url: str
    filename: str
    size: int


# ---------------------------------------------------------------------------
# ChannelBinding（渠道绑定）
# ---------------------------------------------------------------------------


class ChannelBindingCreate(BaseModel):
    """绑定渠道请求。"""

    channel: str = Field(..., description="渠道类型：apns/wechat/whatsapp/telegram")
    channel_user_id: str = Field(..., min_length=1, max_length=500, description="渠道侧用户标识")
    device_id: uuid.UUID | None = Field(None, description="APNs 渠道关联的 Device ID")
    display_label: str | None = Field(None, max_length=100, description="展示名称（如微信昵称）")

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        allowed = ("apns", "wechat", "whatsapp", "telegram")
        if v not in allowed:
            raise ValueError(f"channel 必须为 {'/'.join(allowed)}")
        return v


class ChannelBindingResponse(BaseModel):
    """渠道绑定响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    channel: str
    channel_user_id: str
    device_id: uuid.UUID | None = None
    display_label: str | None = None
    is_active: bool = True
    verified_at: UTCDatetime | None = None
    created_at: UTCDatetime
    updated_at: UTCDatetime

    model_config = {"from_attributes": True}


class ChannelBindingListResponse(BaseModel):
    """渠道绑定列表响应。"""

    bindings: list[ChannelBindingResponse]


# ---------------------------------------------------------------------------
# UserChannelPreference（用户渠道偏好）
# ---------------------------------------------------------------------------


class ChannelPreferenceUpdate(BaseModel):
    """更新渠道偏好请求。"""

    channel_priority: list[str] | None = Field(
        None, description="渠道优先级排序，如 ['wechat', 'apns']"
    )
    quiet_start_hour: int | None = Field(None, ge=0, le=23, description="静默开始时（本地时间 0-23）")
    quiet_end_hour: int | None = Field(None, ge=0, le=23, description="静默结束时（本地时间 0-23）")
    max_daily_pushes: int | None = Field(None, ge=1, le=50, description="每日最大推送数")

    @field_validator("channel_priority")
    @classmethod
    def validate_channel_priority(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            allowed = {"apns", "wechat", "whatsapp", "telegram"}
            for ch in v:
                if ch not in allowed:
                    raise ValueError(f"无效渠道类型: {ch}")
            if len(v) != len(set(v)):
                raise ValueError("渠道优先级不能包含重复项")
        return v


class ChannelPreferenceResponse(BaseModel):
    """渠道偏好响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    channel_priority: list[str]
    quiet_start_hour: int = 22
    quiet_end_hour: int = 8
    max_daily_pushes: int = 5
    created_at: UTCDatetime
    updated_at: UTCDatetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# PushLog（推送日志）
# ---------------------------------------------------------------------------


class PushLogResponse(BaseModel):
    """推送日志响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    rule_id: str | None = None
    message_id: uuid.UUID | None = None
    channel: str
    status: str
    error: str | None = None
    latency_ms: int | None = None
    fallback_used: bool = False
    fallback_channel: str | None = None
    created_at: UTCDatetime

    model_config = {"from_attributes": True}


class PushLogListResponse(BaseModel):
    """推送日志列表响应。"""

    logs: list[PushLogResponse]
    has_more: bool
    total: int


# ---------------------------------------------------------------------------
# Voice（语音交互 — iOS 原生优先，后端处理意图+Skill）
# ---------------------------------------------------------------------------


class VoiceConverseRequest(BaseModel):
    """语音对话请求（接收 iOS 端 ASR 转写后的文本）。"""

    transcript: str = Field(..., min_length=1, max_length=2000, description="ASR 转写文本")
    child_id: uuid.UUID
    confidence: float | None = Field(None, ge=0.0, le=1.0, description="iOS ASR 置信度")


class VoiceConverseResponse(BaseModel):
    """语音对话响应（返回纯文本，由 iOS 端 TTS 播报）。"""

    reply_text: str
    intent: str
    action_taken: dict | None = None
    should_fallback_to_cloud_asr: bool = False  # 建议 iOS 端降级到云端 ASR
    record_id: str | None = None  # 快速记录创建后的 record_id


class VoiceTranscribeRequest(BaseModel):
    """[Optional] 云端 ASR Fallback 请求。"""

    audio_url: str = Field(..., description="音频文件 URL")
    language: str = Field(default="zh-CN")


class VoiceTranscribeResponse(BaseModel):
    """[Optional] 云端 ASR Fallback 响应。"""

    transcript: str
    confidence: float
    duration_ms: int | None = None


# ---------------------------------------------------------------------------
# 微信 OAuth 绑定
# ---------------------------------------------------------------------------


class WeChatQRCodeResponse(BaseModel):
    """微信 OAuth 绑定二维码响应。"""

    qrcode_url: str
    state: str  # 用于校验回调
    expires_in: int = 300  # 二维码有效期（秒）


# ---------------------------------------------------------------------------
# Skill（技能系统 — Phase 3）
# ---------------------------------------------------------------------------


class SkillInfoResponse(BaseModel):
    """单个技能信息响应。"""

    name: str
    display_name: str
    description: str
    version: str
    icon: str = ""
    tags: list[str] = []
    is_enabled: bool = True
    session_type: str | None = None


class SkillListResponse(BaseModel):
    """技能列表响应。"""

    skills: list[SkillInfoResponse]
    total: int


class SleepAnalysisRequest(BaseModel):
    """睡眠分析请求。"""

    child_id: uuid.UUID
    sleep_records: list[dict] = Field(..., min_length=1, max_length=14)


class SleepAnalysisResponse(BaseModel):
    """睡眠分析响应。"""

    overall_rating: str
    rating_display: str
    avg_total_hours: float
    avg_night_wakings: float
    bedtime_consistency: str
    summary_text: str
    recommendations: list[str]
    age_reference: str


# ---------------------------------------------------------------------------
# Memory（OpenClaw 记忆初始化）
# ---------------------------------------------------------------------------


class MemoryInitRequest(BaseModel):
    """记忆初始化请求。"""

    child_id: uuid.UUID
    caregiver_role: str = Field(default="", description="照护角色: mother/father/grandparent/other")
    recent_situation: str = Field(default="", description="用户填写的近况描述")


class MemoryInitResponse(BaseModel):
    """记忆初始化响应。"""

    success: bool
    files: dict[str, str] = Field(
        ..., description="初始化的记忆文件名 → 内容映射"
    )
    message: str = ""
