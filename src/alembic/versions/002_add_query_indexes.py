"""Add composite indexes for high-frequency queries.

覆盖以下查询热路径:
- Plan: get_active_plan(child_id, status), advance_all_plans(status)
- Device: 推送时按 user_id + is_active 查找活跃设备
- WeeklyFeedback: 按 plan_id + status 查周反馈
- ChannelBinding: webhook 回调按 channel + channel_user_id 查绑定
- Child: 按 user_id 列出孩子（外键列无自动索引）
- DayTask: Plan.day_tasks selectin 关系加载（plan_id 外键列）

Revision ID: 002
Revises: 001
Create Date: 2026-03-17
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # P0: Plan — 覆盖 get_active_plan / supersede / list_plans 查询
    op.create_index("ix_plan_child_status", "plans", ["child_id", "status"])
    # P2: Plan — 覆盖定时任务 advance_all_plans 和 admin 按状态筛选
    op.create_index("ix_plan_status", "plans", ["status"])

    # P0: Device — 覆盖推送时查找用户活跃设备
    op.create_index("ix_device_user_active", "devices", ["user_id", "is_active"])

    # P1: WeeklyFeedback — 覆盖首页和活跃计划页查周反馈
    op.create_index(
        "ix_weekly_feedback_plan_status", "weekly_feedbacks", ["plan_id", "status"]
    )

    # P1: ChannelBinding — 覆盖 webhook 回调按渠道+用户ID查绑定
    op.create_index(
        "ix_channel_binding_channel_user",
        "channel_bindings",
        ["channel", "channel_user_id"],
    )

    # P1: Child — 外键列无自动索引，覆盖按用户查孩子列表
    op.create_index("ix_child_user", "children", ["user_id"])

    # P2: DayTask — 外键列无自动索引，覆盖 selectin 关系加载
    op.create_index("ix_day_task_plan", "day_tasks", ["plan_id"])

    # 补充已在 models.py 中定义但 001 迁移遗漏的索引
    op.create_index(
        "ix_record_child_created", "records", ["child_id", "created_at"]
    )
    op.create_index(
        "ix_ai_session_child_created", "ai_sessions", ["child_id", "created_at"]
    )
    op.create_index(
        "ix_message_user_read_created",
        "messages",
        ["user_id", "read_status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_message_user_read_created", table_name="messages")
    op.drop_index("ix_ai_session_child_created", table_name="ai_sessions")
    op.drop_index("ix_record_child_created", table_name="records")
    op.drop_index("ix_day_task_plan", table_name="day_tasks")
    op.drop_index("ix_child_user", table_name="children")
    op.drop_index("ix_channel_binding_channel_user", table_name="channel_bindings")
    op.drop_index("ix_weekly_feedback_plan_status", table_name="weekly_feedbacks")
    op.drop_index("ix_device_user_active", table_name="devices")
    op.drop_index("ix_plan_status", table_name="plans")
    op.drop_index("ix_plan_child_status", table_name="plans")
