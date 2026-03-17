"""Admin 管理 API 路由。

提供系统管理员的数据查询和管理端点。
所有端点需要 is_admin=True 的用户认证。
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai_parenting.backend.auth import get_current_admin_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.models import (
    AISession,
    ChannelBinding,
    Child,
    Message,
    Plan,
    PushLog,
    Record,
    User,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------


class AdminUserResponse(BaseModel):
    """管理员用户列表响应。"""

    id: uuid.UUID
    email: str | None = None
    display_name: str | None = None
    caregiver_role: str | None = None
    auth_provider: str
    is_admin: bool
    timezone: str
    push_enabled: bool
    created_at: str
    updated_at: str
    children_count: int = 0

    model_config = {"from_attributes": True}


class AdminChildResponse(BaseModel):
    """管理员儿童列表响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    nickname: str
    birth_year_month: str
    age_months: int
    stage: str
    focus_themes: list[str] | None = None
    risk_level: str
    onboarding_completed: bool
    created_at: str

    model_config = {"from_attributes": True}


class AdminPlanResponse(BaseModel):
    """管理员计划列表响应。"""

    id: uuid.UUID
    child_id: uuid.UUID
    child_nickname: str | None = None
    title: str
    status: str
    focus_theme: str
    current_day: int
    completion_rate: float
    start_date: str
    end_date: str
    created_at: str

    model_config = {"from_attributes": True}


class AdminStatsResponse(BaseModel):
    """系统统计数据。"""

    total_users: int
    total_children: int
    total_plans: int
    total_records: int
    total_messages: int
    total_ai_sessions: int


class AdminUserListResponse(BaseModel):
    """用户列表分页响应。"""

    users: list[AdminUserResponse]
    total: int
    has_more: bool


class AdminChildListResponse(BaseModel):
    """儿童列表分页响应。"""

    children: list[AdminChildResponse]
    total: int
    has_more: bool


class AdminPlanListResponse(BaseModel):
    """计划列表分页响应。"""

    plans: list[AdminPlanResponse]
    total: int
    has_more: bool


class AdminUserUpdate(BaseModel):
    """管理员更新用户请求。"""

    display_name: str | None = None
    is_admin: bool | None = None
    push_enabled: bool | None = None


# ---------------------------------------------------------------------------
# 统计概览
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminStatsResponse:
    """获取系统统计概览。"""
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    children_count = (await db.execute(select(func.count(Child.id)))).scalar() or 0
    plans_count = (await db.execute(select(func.count(Plan.id)))).scalar() or 0
    records_count = (await db.execute(select(func.count(Record.id)))).scalar() or 0
    messages_count = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    ai_sessions_count = (
        await db.execute(select(func.count(AISession.id)))
    ).scalar() or 0

    return AdminStatsResponse(
        total_users=users_count,
        total_children=children_count,
        total_plans=plans_count,
        total_records=records_count,
        total_messages=messages_count,
        total_ai_sessions=ai_sessions_count,
    )


# ---------------------------------------------------------------------------
# 用户管理
# ---------------------------------------------------------------------------


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, description="按邮箱或昵称搜索"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminUserListResponse:
    """分页获取用户列表。"""
    base_query = select(User)
    count_query = select(func.count(User.id))

    if search:
        search_filter = User.email.ilike(f"%{search}%") | User.display_name.ilike(
            f"%{search}%"
        )
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(User.children))
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    users = result.scalars().all()

    user_responses = []
    for u in users:
        user_responses.append(
            AdminUserResponse(
                id=u.id,
                email=u.email,
                display_name=u.display_name,
                caregiver_role=u.caregiver_role,
                auth_provider=u.auth_provider,
                is_admin=u.is_admin,
                timezone=u.timezone,
                push_enabled=u.push_enabled,
                created_at=str(u.created_at),
                updated_at=str(u.updated_at),
                children_count=len(u.children) if u.children else 0,
            )
        )

    return AdminUserListResponse(
        users=user_responses,
        total=total,
        has_more=(offset + limit) < total,
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminUserResponse:
    """更新用户信息（管理员操作）。"""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 防止管理员移除自己的 admin 权限
    if body.is_admin is False and user_id == admin_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove your own admin privileges",
        )

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.push_enabled is not None:
        user.push_enabled = body.push_enabled

    await db.flush()
    await db.refresh(user)

    return AdminUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        caregiver_role=user.caregiver_role,
        auth_provider=user.auth_provider,
        is_admin=user.is_admin,
        timezone=user.timezone,
        push_enabled=user.push_enabled,
        created_at=str(user.created_at),
        updated_at=str(user.updated_at),
        children_count=0,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin_id: uuid.UUID = Depends(get_current_admin_id),
):
    """删除用户（管理员操作）。"""
    if user_id == admin_id:
        raise HTTPException(
            status_code=400, detail="Cannot delete your own account"
        )

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.flush()
    return {"detail": "User deleted"}


# ---------------------------------------------------------------------------
# 儿童管理
# ---------------------------------------------------------------------------


@router.get("/children", response_model=AdminChildListResponse)
async def list_children(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, description="按昵称搜索"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminChildListResponse:
    """分页获取所有儿童列表。"""
    base_query = select(Child).join(User, Child.user_id == User.id)
    count_query = select(func.count(Child.id))

    if search:
        search_filter = Child.nickname.ilike(f"%{search}%")
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(Child.user))
        .order_by(Child.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    children = result.scalars().all()

    child_responses = []
    for c in children:
        child_responses.append(
            AdminChildResponse(
                id=c.id,
                user_id=c.user_id,
                user_email=c.user.email if c.user else None,
                nickname=c.nickname,
                birth_year_month=c.birth_year_month,
                age_months=c.age_months,
                stage=c.stage,
                focus_themes=c.focus_themes,
                risk_level=c.risk_level,
                onboarding_completed=c.onboarding_completed,
                created_at=str(c.created_at),
            )
        )

    return AdminChildListResponse(
        children=child_responses,
        total=total,
        has_more=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# 计划管理
# ---------------------------------------------------------------------------


@router.get("/plans", response_model=AdminPlanListResponse)
async def list_plans(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminPlanListResponse:
    """分页获取所有计划列表。"""
    base_query = select(Plan).join(Child, Plan.child_id == Child.id)
    count_query = select(func.count(Plan.id))

    if status:
        base_query = base_query.where(Plan.status == status)
        count_query = count_query.where(Plan.status == status)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(Plan.child))
        .order_by(Plan.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    plans = result.scalars().all()

    plan_responses = []
    for p in plans:
        plan_responses.append(
            AdminPlanResponse(
                id=p.id,
                child_id=p.child_id,
                child_nickname=p.child.nickname if p.child else None,
                title=p.title,
                status=p.status,
                focus_theme=p.focus_theme,
                current_day=p.current_day,
                completion_rate=p.completion_rate,
                start_date=str(p.start_date),
                end_date=str(p.end_date),
                created_at=str(p.created_at),
            )
        )

    return AdminPlanListResponse(
        plans=plan_responses,
        total=total,
        has_more=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# 推送规则管理（管理后台看板使用）
# ---------------------------------------------------------------------------


class PushRuleResponse(BaseModel):
    """推送规则响应（管理后台展示用）。"""

    id: str
    name: str
    description: str
    triggerType: str  # cron / event / milestone
    cronExpression: str | None = None
    eventType: str | None = None
    isActive: bool
    cooldownMinutes: int
    channelPriority: list[str]
    conditionSummary: str
    lastTriggeredAt: str | None = None
    totalSent: int = 0
    deliveryRate: float = 0.0


class PushRulesListResponse(BaseModel):
    """推送规则列表响应。"""

    rules: list[PushRuleResponse]


@router.get("/push-rules", response_model=PushRulesListResponse)
async def list_push_rules(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> PushRulesListResponse:
    """获取推送规则列表（含统计数据）。

    从 push_logs 表聚合每条规则的推送量和送达率。
    规则定义来自 SmartPushEngine 配置。
    """
    # 聚合 push_logs 统计数据（按 rule_id 分组）

    stats_query = (
        select(
            PushLog.rule_id,
            func.count(PushLog.id).label("total_sent"),
            func.sum(
                case(
                    (PushLog.status.in_(["sent", "delivered"]), 1),
                    else_=0,
                )
            ).label("delivered_count"),
            func.max(PushLog.created_at).label("last_triggered"),
        )
        .where(PushLog.rule_id.is_not(None))
        .group_by(PushLog.rule_id)
    )
    stats_result = await db.execute(stats_query)
    stats_map: dict[str, dict[str, Any]] = {}
    for row in stats_result:
        total = row.total_sent or 0
        delivered = row.delivered_count or 0
        stats_map[row.rule_id] = {
            "total_sent": total,
            "delivery_rate": delivered / total if total > 0 else 0.0,
            "last_triggered": str(row.last_triggered) if row.last_triggered else None,
        }

    # 内置规则定义（对应 SmartPushEngine 配置）
    builtin_rules: list[PushRuleResponse] = [
        PushRuleResponse(
            id="rule_morning_task",
            name="早安任务提醒",
            description="每日 08:00 推送今日训练任务（按用户时区）",
            triggerType="cron",
            cronExpression="0 8 * * *",
            isActive=True,
            cooldownMinutes=1440,
            channelPriority=["apns", "wechat"],
            conditionSummary="有活跃计划且今日未执行",
        ),
        PushRuleResponse(
            id="rule_evening_record",
            name="晚间记录提醒",
            description="每日 20:30 提醒记录今日观察",
            triggerType="cron",
            cronExpression="30 20 * * *",
            isActive=True,
            cooldownMinutes=1440,
            channelPriority=["wechat", "apns"],
            conditionSummary="今日已执行但未记录",
        ),
        PushRuleResponse(
            id="rule_plan_advance",
            name="计划推进提醒",
            description="每日 00:01 自动推进计划到下一天",
            triggerType="cron",
            cronExpression="1 0 * * *",
            isActive=True,
            cooldownMinutes=1440,
            channelPriority=["apns"],
            conditionSummary="有活跃计划且当前天 < 7",
        ),
        PushRuleResponse(
            id="rule_weekly_feedback",
            name="周反馈通知",
            description="周反馈生成后立即推送",
            triggerType="event",
            eventType="weekly_feedback_created",
            isActive=True,
            cooldownMinutes=10080,
            channelPriority=["wechat", "apns"],
            conditionSummary="周反馈状态变为 ready",
        ),
        PushRuleResponse(
            id="rule_risk_alert",
            name="风险提醒",
            description="识别到发育风险后推送专业建议",
            triggerType="event",
            eventType="risk_detected",
            isActive=True,
            cooldownMinutes=4320,
            channelPriority=["apns", "wechat"],
            conditionSummary="风险等级 >= watch",
        ),
        PushRuleResponse(
            id="rule_milestone_celebration",
            name="里程碑庆祝",
            description="儿童达成发育里程碑时推送庆祝消息",
            triggerType="milestone",
            isActive=True,
            cooldownMinutes=0,
            channelPriority=["apns", "wechat"],
            conditionSummary="完成率达到 100% 或连续 7 天",
        ),
        PushRuleResponse(
            id="rule_streak_encourage",
            name="连续打卡鼓励",
            description="连续 3/7/14/30 天打卡时推送鼓励消息",
            triggerType="milestone",
            isActive=False,
            cooldownMinutes=0,
            channelPriority=["apns"],
            conditionSummary="连续打卡天数 ∈ {3, 7, 14, 30}",
        ),
    ]

    # 合并统计数据到规则
    rules: list[PushRuleResponse] = []
    for rule in builtin_rules:
        s = stats_map.get(rule.id, {})
        if s:
            rule = rule.model_copy(update={
                "totalSent": s.get("total_sent", 0),
                "deliveryRate": s.get("delivery_rate", 0.0),
                "lastTriggeredAt": s.get("last_triggered"),
            })
        rules.append(rule)

    return PushRulesListResponse(rules=rules)


# ---------------------------------------------------------------------------
# 渠道监控看板（管理后台看板使用）
# ---------------------------------------------------------------------------


class ChannelStatusResponse(BaseModel):
    """渠道状态响应。"""

    channel: str
    displayName: str
    status: str  # healthy / degraded / unavailable
    latencyMs: int
    todayMessages: int
    failureRate: float
    lastCheckAt: str


class ChannelStatsResponse(BaseModel):
    """渠道监控全量数据响应。"""

    channels: list[ChannelStatusResponse]
    alerts: list[dict[str, Any]]
    bindingStats: list[dict[str, Any]]
    latencyTrend: list[dict[str, Any]]
    bindingTrend: list[dict[str, Any]]


@router.get("/channel-stats", response_model=ChannelStatsResponse)
async def get_channel_stats(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> ChannelStatsResponse:
    """获取渠道监控统计数据。

    聚合 channel_bindings、push_logs 数据，
    结合 ChannelRouter 健康状态信息。
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. 渠道绑定统计
    binding_stats_query = (
        select(
            ChannelBinding.channel,
            func.count(ChannelBinding.id).label("binding_count"),
        )
        .where(ChannelBinding.is_active.is_(True))
        .group_by(ChannelBinding.channel)
    )
    binding_result = await db.execute(binding_stats_query)
    total_bindings = 0
    binding_counts: dict[str, int] = {}
    for row in binding_result:
        binding_counts[row.channel] = row.binding_count
        total_bindings += row.binding_count

    binding_stats = []
    channel_display = {"apns": "APNs", "wechat": "微信", "whatsapp": "WhatsApp", "telegram": "Telegram"}
    for ch, display in channel_display.items():
        count = binding_counts.get(ch, 0)
        binding_stats.append({
            "channel": display,
            "count": count,
            "percentage": round(count / total_bindings * 100, 1) if total_bindings > 0 else 0,
        })

    # 2. 今日推送统计（按渠道）
    push_stats_query = (
        select(
            PushLog.channel,
            func.count(PushLog.id).label("total"),
            func.sum(
                case(
                    (PushLog.status == "failed", 1),
                    else_=0,
                )
            ).label("failed"),
            func.avg(PushLog.latency_ms).label("avg_latency"),
        )
        .where(PushLog.created_at >= today_start)
        .group_by(PushLog.channel)
    )
    push_result = await db.execute(push_stats_query)
    push_map: dict[str, dict[str, Any]] = {}
    for row in push_result:
        total = row.total or 0
        failed = row.failed or 0
        push_map[row.channel] = {
            "today_messages": total,
            "failure_rate": failed / total if total > 0 else 0.0,
            "avg_latency": int(row.avg_latency) if row.avg_latency else 0,
        }

    # 3. 构造渠道状态（结合健康信息）
    channels = []
    for ch, display in channel_display.items():
        stats = push_map.get(ch, {"today_messages": 0, "failure_rate": 0, "avg_latency": 0})
        # 根据失败率判断健康状态
        failure_rate = stats["failure_rate"]
        if failure_rate >= 0.5:
            status = "unavailable"
        elif failure_rate >= 0.05:
            status = "degraded"
        else:
            status = "healthy"

        channels.append(ChannelStatusResponse(
            channel=ch,
            displayName=display,
            status=status,
            latencyMs=stats["avg_latency"],
            todayMessages=stats["today_messages"],
            failureRate=round(failure_rate, 3),
            lastCheckAt=now.isoformat() + "Z",
        ))

    # 4. 空告警和趋势数据（后续可接入真实告警系统）
    alerts: list[dict[str, Any]] = []
    latency_trend: list[dict[str, Any]] = []
    binding_trend: list[dict[str, Any]] = []

    return ChannelStatsResponse(
        channels=channels,
        alerts=alerts,
        bindingStats=binding_stats,
        latencyTrend=latency_trend,
        bindingTrend=binding_trend,
    )
