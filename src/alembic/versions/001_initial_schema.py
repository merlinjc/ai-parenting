"""Initial schema — 全部 12 个模型建表。

包含：User, Device, Child, Record, Plan, DayTask,
AISession, WeeklyFeedback, Message,
ChannelBinding, PushLog, UserChannelPreference。

Revision ID: 001
Revises: None
Create Date: 2026-03-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("auth_provider", sa.String(20), nullable=False, server_default="email"),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("caregiver_role", sa.String(20), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Shanghai"),
        sa.Column("push_enabled", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # --- devices ---
    op.create_table(
        "devices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("push_token", sa.String(500), nullable=True),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("app_version", sa.String(20), nullable=False),
        sa.Column("last_active_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_device_user_active", "devices", ["user_id", "is_active"])

    # --- children ---
    op.create_table(
        "children",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("nickname", sa.String(50), nullable=False),
        sa.Column("birth_year_month", sa.String(7), nullable=False),
        sa.Column("age_months", sa.Integer, nullable=False),
        sa.Column("stage", sa.String(10), nullable=False),
        sa.Column("focus_themes", sa.Text, nullable=True),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="normal"),
        sa.Column("onboarding_completed", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_child_user", "children", ["user_id"])

    # --- ai_sessions ---
    op.create_table(
        "ai_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("child_id", sa.String(36), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("session_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_scenario", sa.String(200), nullable=True),
        sa.Column("input_text", sa.Text, nullable=True),
        sa.Column("context_snapshot", sa.Text, nullable=True),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("error_info", sa.Text, nullable=True),
        sa.Column("degraded_result", sa.Text, nullable=True),
        sa.Column("model_provider", sa.String(50), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("prompt_template_id", sa.String(100), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_ai_session_child_created", "ai_sessions", ["child_id", "created_at"])

    # --- plans ---
    op.create_table(
        "plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("child_id", sa.String(36), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("primary_goal", sa.String(300), nullable=False),
        sa.Column("focus_theme", sa.String(20), nullable=False),
        sa.Column("priority_scenes", sa.Text, nullable=True),
        sa.Column("stage", sa.String(10), nullable=False),
        sa.Column("risk_level_at_creation", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("current_day", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("completion_rate", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("observation_candidates", sa.Text, nullable=True),
        sa.Column("next_week_context", sa.Text, nullable=True),
        sa.Column("next_week_direction", sa.String(20), nullable=True),
        sa.Column("weekend_review_prompt", sa.Text, nullable=True),
        sa.Column("conservative_note", sa.Text, nullable=True),
        sa.Column("ai_generation_id", sa.String(36), sa.ForeignKey("ai_sessions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plan_child_status", "plans", ["child_id", "status"])
    op.create_index("ix_plan_status", "plans", ["status"])

    # --- day_tasks ---
    op.create_table(
        "day_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("day_number", sa.Integer, nullable=False),
        sa.Column("main_exercise_title", sa.String(100), nullable=False),
        sa.Column("main_exercise_description", sa.Text, nullable=False),
        sa.Column("natural_embed_title", sa.String(100), nullable=False),
        sa.Column("natural_embed_description", sa.Text, nullable=False),
        sa.Column("demo_script", sa.Text, nullable=False),
        sa.Column("observation_point", sa.Text, nullable=False),
        sa.Column("completion_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_day_task_plan", "day_tasks", ["plan_id"])

    # --- records ---
    op.create_table(
        "records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("child_id", sa.String(36), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("voice_url", sa.String(500), nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("scene", sa.String(20), nullable=True),
        sa.Column("time_of_day", sa.String(10), nullable=True),
        sa.Column("theme", sa.String(20), nullable=True),
        sa.Column("source_plan_id", sa.String(36), sa.ForeignKey("plans.id"), nullable=True),
        sa.Column("source_session_id", sa.String(36), sa.ForeignKey("ai_sessions.id"), nullable=True),
        sa.Column("synced_to_plan", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_record_child_created", "records", ["child_id", "created_at"])

    # --- weekly_feedbacks ---
    op.create_table(
        "weekly_feedbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("child_id", sa.String(36), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="generating"),
        sa.Column("positive_changes", sa.Text, nullable=True),
        sa.Column("opportunities", sa.Text, nullable=True),
        sa.Column("summary_text", sa.Text, nullable=True),
        sa.Column("decision_options", sa.Text, nullable=True),
        sa.Column("selected_decision", sa.String(20), nullable=True),
        sa.Column("conservative_path_note", sa.Text, nullable=True),
        sa.Column("error_info", sa.Text, nullable=True),
        sa.Column("record_count_this_week", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("completion_rate_this_week", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("ai_generation_id", sa.String(36), sa.ForeignKey("ai_sessions.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("viewed_at", sa.DateTime, nullable=True),
        sa.Column("decided_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_weekly_feedback_plan_status", "weekly_feedbacks", ["plan_id", "status"])

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("child_id", sa.String(36), sa.ForeignKey("children.id"), nullable=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("summary", sa.String(200), nullable=False),
        sa.Column("target_page", sa.String(100), nullable=True),
        sa.Column("target_params", sa.Text, nullable=True),
        sa.Column("requires_preview", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("read_status", sa.String(10), nullable=False, server_default="unread"),
        sa.Column("push_status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("push_sent_at", sa.DateTime, nullable=True),
        sa.Column("push_delivered_at", sa.DateTime, nullable=True),
        sa.Column("clicked_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_message_user_read_created", "messages", ["user_id", "read_status", "created_at"])

    # --- channel_bindings ---
    op.create_table(
        "channel_bindings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("channel_user_id", sa.String(500), nullable=False),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("display_label", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("verified_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_user_channel", "channel_bindings", ["user_id", "channel"])
    op.create_index("ix_channel_binding_channel_user", "channel_bindings", ["channel", "channel_user_id"])

    # --- push_logs ---
    op.create_table(
        "push_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id"), nullable=True),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("channel_message_id", sa.String(200), nullable=True),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("fallback_used", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("fallback_channel", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_push_log_idempotency", "push_logs", ["idempotency_key"], unique=True)
    op.create_index("ix_push_log_user_created", "push_logs", ["user_id", "created_at"])

    # --- user_channel_preferences ---
    op.create_table(
        "user_channel_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("channel_priority", sa.Text, nullable=False, server_default='["apns"]'),
        sa.Column("quiet_start_hour", sa.Integer, nullable=False, server_default=sa.text("22")),
        sa.Column("quiet_end_hour", sa.Integer, nullable=False, server_default=sa.text("8")),
        sa.Column("max_daily_pushes", sa.Integer, nullable=False, server_default=sa.text("5")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_channel_preferences")
    op.drop_index("ix_push_log_user_created", table_name="push_logs")
    op.drop_index("ix_push_log_idempotency", table_name="push_logs")
    op.drop_table("push_logs")
    op.drop_index("ix_channel_binding_channel_user", table_name="channel_bindings")
    op.drop_table("channel_bindings")
    op.drop_index("ix_message_user_read_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_weekly_feedback_plan_status", table_name="weekly_feedbacks")
    op.drop_table("weekly_feedbacks")
    op.drop_index("ix_record_child_created", table_name="records")
    op.drop_table("records")
    op.drop_index("ix_day_task_plan", table_name="day_tasks")
    op.drop_table("day_tasks")
    op.drop_index("ix_plan_child_status", table_name="plans")
    op.drop_index("ix_plan_status", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_ai_session_child_created", table_name="ai_sessions")
    op.drop_table("ai_sessions")
    op.drop_index("ix_child_user", table_name="children")
    op.drop_table("children")
    op.drop_index("ix_device_user_active", table_name="devices")
    op.drop_table("devices")
    op.drop_table("users")
