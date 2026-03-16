"""SQLAlchemy ORM 模型定义。

基于数据结构草案 V1 定义 9 个领域对象的 ORM 映射：
User, Device, Child, Record, Plan, DayTask,
WeeklyFeedback, AISession, Message。

所有模型使用 UUID 主键，时间戳字段自动管理，
枚举类型复用 ai_parenting.models.enums 中的定义。

使用跨数据库兼容类型（GUID/JSONType/ArrayType），
支持 PostgreSQL 生产环境和 SQLite 测试环境。
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ai_parenting.models.enums import (
    ChildStage,
    CompletionStatus,
    RiskLevel,
    SessionStatus,
)


# ---------------------------------------------------------------------------
# 跨数据库兼容类型
# ---------------------------------------------------------------------------


class GUID(TypeDecorator):
    """跨平台 UUID 类型：PostgreSQL 使用原生 UUID，SQLite 使用 CHAR(36)。"""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(uuid.UUID(value))
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value


class JSONType(TypeDecorator):
    """跨平台 JSON 类型：PostgreSQL 使用 JSONB，SQLite 使用 TEXT + JSON 序列化。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class ArrayType(TypeDecorator):
    """跨平台 Array 类型：PostgreSQL 使用 ARRAY，SQLite 使用 TEXT + JSON 序列化。"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


# ---------------------------------------------------------------------------
# 基类
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""

    pass


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(Base):
    """用户模型 — 身份锚点。"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default="email"
    )
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    caregiver_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Asia/Shanghai"
    )
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    devices: Mapped[list[Device]] = relationship(back_populates="user", lazy="selectin")
    children: Mapped[list[Child]] = relationship(
        back_populates="user", lazy="selectin"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="user", lazy="noload"
    )


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------


class Device(Base):
    """设备模型 — 推送令牌与设备绑定。"""

    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    push_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    app_version: Mapped[str] = mapped_column(String(20), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 关系
    user: Mapped[User] = relationship(back_populates="devices")


# ---------------------------------------------------------------------------
# Child
# ---------------------------------------------------------------------------


class Child(Base):
    """儿童档案模型 — 业务上下文中心。

    阶段自动映射规则：
    - 18—24 月 → 18_24m
    - 24—36 月 → 24_36m
    - 36—48 月 → 36_48m
    """

    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    birth_year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(10), nullable=False)
    focus_themes: Mapped[list | None] = mapped_column(ArrayType(), nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(10), nullable=False, default=RiskLevel.NORMAL.value
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    user: Mapped[User] = relationship(back_populates="children")
    records: Mapped[list[Record]] = relationship(
        back_populates="child", lazy="noload"
    )
    plans: Mapped[list[Plan]] = relationship(back_populates="child", lazy="noload")
    ai_sessions: Mapped[list[AISession]] = relationship(
        back_populates="child", lazy="noload"
    )
    weekly_feedbacks: Mapped[list[WeeklyFeedback]] = relationship(
        back_populates="child", lazy="noload"
    )

    def compute_age_and_stage(self) -> None:
        """根据 birth_year_month 计算当前 age_months 和 stage。"""
        today = date.today()
        parts = self.birth_year_month.split("-")
        birth_year, birth_month = int(parts[0]), int(parts[1])
        months = (today.year - birth_year) * 12 + (today.month - birth_month)
        self.age_months = max(18, min(48, months))

        if self.age_months < 24:
            self.stage = ChildStage.M18_24.value
        elif self.age_months < 36:
            self.stage = ChildStage.M24_36.value
        else:
            self.stage = ChildStage.M36_48.value


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


class Record(Base):
    """观察记录模型 — 最高频写入对象。"""

    __tablename__ = "records"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("children.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    tags: Mapped[list | None] = mapped_column(ArrayType(), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    scene: Mapped[str | None] = mapped_column(String(20), nullable=True)
    time_of_day: Mapped[str | None] = mapped_column(String(10), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("plans.id"), nullable=True
    )
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("ai_sessions.id"), nullable=True
    )
    synced_to_plan: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    child: Mapped[Child] = relationship(back_populates="records")


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


class Plan(Base):
    """微计划模型 — 7 天微计划周期。"""

    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("children.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_goal: Mapped[str] = mapped_column(String(300), nullable=False)
    focus_theme: Mapped[str] = mapped_column(String(20), nullable=False)
    priority_scenes: Mapped[list | None] = mapped_column(ArrayType(), nullable=True)
    stage: Mapped[str] = mapped_column(String(10), nullable=False)
    risk_level_at_creation: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    observation_candidates: Mapped[dict | None] = mapped_column(
        JSONType(), nullable=True
    )
    next_week_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_week_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    weekend_review_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    conservative_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("ai_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    child: Mapped[Child] = relationship(back_populates="plans")
    day_tasks: Mapped[list[DayTask]] = relationship(
        back_populates="plan", lazy="selectin", order_by="DayTask.day_number"
    )


# ---------------------------------------------------------------------------
# DayTask
# ---------------------------------------------------------------------------


class DayTask(Base):
    """日任务模型 — Plan 的子对象。"""

    __tablename__ = "day_tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("plans.id"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    main_exercise_title: Mapped[str] = mapped_column(String(100), nullable=False)
    main_exercise_description: Mapped[str] = mapped_column(Text, nullable=False)
    natural_embed_title: Mapped[str] = mapped_column(String(100), nullable=False)
    natural_embed_description: Mapped[str] = mapped_column(Text, nullable=False)
    demo_script: Mapped[str] = mapped_column(Text, nullable=False)
    observation_point: Mapped[str] = mapped_column(Text, nullable=False)
    completion_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CompletionStatus.PENDING.value
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    plan: Mapped[Plan] = relationship(back_populates="day_tasks")


# ---------------------------------------------------------------------------
# AISession
# ---------------------------------------------------------------------------


class AISession(Base):
    """AI 会话模型 — 承载 AI 交互完整生命周期。"""

    __tablename__ = "ai_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("children.id"), nullable=False
    )
    session_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SessionStatus.PENDING.value
    )
    input_scenario: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    error_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    degraded_result: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    child: Mapped[Child] = relationship(back_populates="ai_sessions")


# ---------------------------------------------------------------------------
# WeeklyFeedback
# ---------------------------------------------------------------------------


class WeeklyFeedback(Base):
    """周反馈模型 — Plan 完成后的 AI 生成反馈。"""

    __tablename__ = "weekly_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("plans.id"), nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("children.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="generating")
    positive_changes: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    opportunities: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_options: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    selected_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conservative_path_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    record_count_this_week: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    completion_rate_this_week: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    ai_generation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("ai_sessions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    child: Mapped[Child] = relationship(back_populates="weekly_feedbacks")
    plan: Mapped[Plan] = relationship(lazy="selectin")


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


class Message(Base):
    """消息模型 — 系统向用户发送的触达消息。"""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    child_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("children.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(String(200), nullable=False)
    target_page: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_params: Mapped[dict | None] = mapped_column(JSONType(), nullable=True)
    requires_preview: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    read_status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="unread"
    )
    push_status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pending"
    )
    push_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    push_delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # 关系
    user: Mapped[User] = relationship(back_populates="messages")
