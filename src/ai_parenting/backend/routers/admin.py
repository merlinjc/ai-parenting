"""Admin 管理 API 路由。

提供系统管理员的数据查询和管理端点。
所有端点需要 is_admin=True 的用户认证。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
    Device,
    Message,
    Plan,
    PushLog,
    Record,
    User,
    WeeklyFeedback,
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

    # 获取内置规则（应用运行时覆盖）
    rules: list[PushRuleResponse] = []
    for rule_id in _BUILTIN_RULE_IDS:
        base = _get_builtin_rule(rule_id)
        if base is None:
            continue
        rule = _apply_overrides(base)

        # 合并统计数据
        s = stats_map.get(rule_id, {})
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


# ---------------------------------------------------------------------------
# 推送规则写入（前端 PushRulesPage 对接）
# ---------------------------------------------------------------------------

# 内存中的规则覆盖配置（运行时修改，重启丢失；生产环境可替换为 DB 存储）
_rule_overrides: dict[str, dict[str, Any]] = {}


class PushRuleUpdateRequest(BaseModel):
    """推送规则更新请求。"""

    name: str | None = None
    description: str | None = None
    isActive: bool | None = None
    cooldownMinutes: int | None = None
    channelPriority: list[str] | None = None
    conditionSummary: str | None = None
    cronExpression: str | None = None


class PushRuleToggleRequest(BaseModel):
    """推送规则开关请求。"""

    is_active: bool


# 所有内置规则 ID 白名单
_BUILTIN_RULE_IDS = {
    "rule_morning_task",
    "rule_evening_record",
    "rule_plan_advance",
    "rule_weekly_feedback",
    "rule_risk_alert",
    "rule_milestone_celebration",
    "rule_streak_encourage",
}


def _get_builtin_rule(rule_id: str) -> PushRuleResponse | None:
    """获取内置规则基础定义。"""
    _builtin = {
        "rule_morning_task": PushRuleResponse(
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
        "rule_evening_record": PushRuleResponse(
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
        "rule_plan_advance": PushRuleResponse(
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
        "rule_weekly_feedback": PushRuleResponse(
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
        "rule_risk_alert": PushRuleResponse(
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
        "rule_milestone_celebration": PushRuleResponse(
            id="rule_milestone_celebration",
            name="里程碑庆祝",
            description="儿童达成发育里程碑时推送庆祝消息",
            triggerType="milestone",
            isActive=True,
            cooldownMinutes=0,
            channelPriority=["apns", "wechat"],
            conditionSummary="完成率达到 100% 或连续 7 天",
        ),
        "rule_streak_encourage": PushRuleResponse(
            id="rule_streak_encourage",
            name="连续打卡鼓励",
            description="连续 3/7/14/30 天打卡时推送鼓励消息",
            triggerType="milestone",
            isActive=False,
            cooldownMinutes=0,
            channelPriority=["apns"],
            conditionSummary="连续打卡天数 ∈ {3, 7, 14, 30}",
        ),
    }
    return _builtin.get(rule_id)


def _apply_overrides(rule: PushRuleResponse) -> PushRuleResponse:
    """应用运行时覆盖配置到规则。"""
    overrides = _rule_overrides.get(rule.id)
    if overrides:
        rule = rule.model_copy(update=overrides)
    return rule


@router.put("/push-rules/{rule_id}", response_model=PushRuleResponse)
async def update_push_rule(
    rule_id: str,
    body: PushRuleUpdateRequest,
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> PushRuleResponse:
    """更新推送规则配置。"""
    if rule_id not in _BUILTIN_RULE_IDS:
        raise HTTPException(status_code=404, detail="Push rule not found")

    base = _get_builtin_rule(rule_id)
    if base is None:
        raise HTTPException(status_code=404, detail="Push rule not found")

    # 合并更新到覆盖配置
    updates = body.model_dump(exclude_none=True)
    if rule_id not in _rule_overrides:
        _rule_overrides[rule_id] = {}
    _rule_overrides[rule_id].update(updates)

    return _apply_overrides(base)


@router.put("/push-rules/{rule_id}/toggle", response_model=PushRuleResponse)
async def toggle_push_rule(
    rule_id: str,
    body: PushRuleToggleRequest,
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> PushRuleResponse:
    """切换推送规则启用/禁用状态。"""
    if rule_id not in _BUILTIN_RULE_IDS:
        raise HTTPException(status_code=404, detail="Push rule not found")

    base = _get_builtin_rule(rule_id)
    if base is None:
        raise HTTPException(status_code=404, detail="Push rule not found")

    if rule_id not in _rule_overrides:
        _rule_overrides[rule_id] = {}
    _rule_overrides[rule_id]["isActive"] = body.is_active

    return _apply_overrides(base)


# ---------------------------------------------------------------------------
# 观察记录管理
# ---------------------------------------------------------------------------


class AdminRecordResponse(BaseModel):
    """管理员观察记录响应。"""

    id: uuid.UUID
    child_id: uuid.UUID
    child_nickname: str | None = None
    user_email: str | None = None
    type: str
    tags: list[str] | None = None
    content: str | None = None
    scene: str | None = None
    theme: str | None = None
    voice_url: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class AdminRecordListResponse(BaseModel):
    """观察记录列表分页响应。"""

    records: list[AdminRecordResponse]
    total: int
    has_more: bool


@router.get("/records", response_model=AdminRecordListResponse)
async def list_records(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    child_id: uuid.UUID | None = Query(None, description="按儿童筛选"),
    record_type: str | None = Query(None, alias="type", description="按类型筛选"),
    search: str | None = Query(None, description="按内容搜索"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminRecordListResponse:
    """分页获取观察记录列表。"""
    base_query = select(Record).join(Child, Record.child_id == Child.id)
    count_query = select(func.count(Record.id))

    if child_id:
        base_query = base_query.where(Record.child_id == child_id)
        count_query = count_query.where(Record.child_id == child_id)
    if record_type:
        base_query = base_query.where(Record.type == record_type)
        count_query = count_query.where(Record.type == record_type)
    if search:
        search_filter = Record.content.ilike(f"%{search}%")
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(Record.child).selectinload(Child.user))
        .order_by(Record.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    records = result.scalars().all()

    return AdminRecordListResponse(
        records=[
            AdminRecordResponse(
                id=r.id,
                child_id=r.child_id,
                child_nickname=r.child.nickname if r.child else None,
                user_email=r.child.user.email if r.child and r.child.user else None,
                type=r.type,
                tags=r.tags,
                content=r.content,
                scene=r.scene,
                theme=r.theme,
                voice_url=r.voice_url,
                created_at=str(r.created_at),
            )
            for r in records
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/records/{record_id}", response_model=AdminRecordResponse)
async def get_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminRecordResponse:
    """获取单条观察记录详情。"""
    result = await db.execute(
        select(Record)
        .where(Record.id == record_id)
        .options(selectinload(Record.child).selectinload(Child.user))
    )
    r = result.scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Record not found")

    return AdminRecordResponse(
        id=r.id,
        child_id=r.child_id,
        child_nickname=r.child.nickname if r.child else None,
        user_email=r.child.user.email if r.child and r.child.user else None,
        type=r.type,
        tags=r.tags,
        content=r.content,
        scene=r.scene,
        theme=r.theme,
        voice_url=r.voice_url,
        created_at=str(r.created_at),
    )


@router.delete("/records/{record_id}")
async def delete_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
):
    """删除观察记录。"""
    record = await db.get(Record, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    await db.delete(record)
    await db.flush()
    return {"detail": "Record deleted"}


# ---------------------------------------------------------------------------
# AI 会话管理
# ---------------------------------------------------------------------------


class AdminAISessionResponse(BaseModel):
    """管理员 AI 会话响应。"""

    id: uuid.UUID
    child_id: uuid.UUID
    child_nickname: str | None = None
    session_type: str
    status: str
    input_text: str | None = None
    model_provider: str | None = None
    model_version: str | None = None
    latency_ms: int | None = None
    retry_count: int | None = None
    error_info: str | None = None
    created_at: str
    completed_at: str | None = None

    model_config = {"from_attributes": True}


class AdminAISessionListResponse(BaseModel):
    """AI 会话列表分页响应。"""

    sessions: list[AdminAISessionResponse]
    total: int
    has_more: bool


class AdminAISessionStatsResponse(BaseModel):
    """AI 会话统计。"""

    total_sessions: int
    success_count: int
    failed_count: int
    degraded_count: int
    success_rate: float
    avg_latency_ms: float
    by_type: list[dict[str, Any]]
    by_model: list[dict[str, Any]]


@router.get("/ai-sessions", response_model=AdminAISessionListResponse)
async def list_ai_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session_type: str | None = Query(None, description="按类型筛选"),
    status: str | None = Query(None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminAISessionListResponse:
    """分页获取 AI 会话列表。"""
    base_query = select(AISession)
    count_query = select(func.count(AISession.id))

    if session_type:
        base_query = base_query.where(AISession.session_type == session_type)
        count_query = count_query.where(AISession.session_type == session_type)
    if status:
        base_query = base_query.where(AISession.status == status)
        count_query = count_query.where(AISession.status == status)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(AISession.child))
        .order_by(AISession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()

    return AdminAISessionListResponse(
        sessions=[
            AdminAISessionResponse(
                id=s.id,
                child_id=s.child_id,
                child_nickname=s.child.nickname if s.child else None,
                session_type=s.session_type,
                status=s.status,
                input_text=s.input_text,
                model_provider=s.model_provider,
                model_version=s.model_version,
                latency_ms=s.latency_ms,
                retry_count=s.retry_count,
                error_info=s.error_info,
                created_at=str(s.created_at),
                completed_at=str(s.completed_at) if s.completed_at else None,
            )
            for s in sessions
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/ai-sessions/stats", response_model=AdminAISessionStatsResponse)
async def get_ai_session_stats(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminAISessionStatsResponse:
    """获取 AI 会话统计数据。"""
    total = (await db.execute(select(func.count(AISession.id)))).scalar() or 0
    success = (
        await db.execute(
            select(func.count(AISession.id)).where(AISession.status == "completed")
        )
    ).scalar() or 0
    failed = (
        await db.execute(
            select(func.count(AISession.id)).where(AISession.status == "failed")
        )
    ).scalar() or 0
    degraded = (
        await db.execute(
            select(func.count(AISession.id)).where(AISession.status == "degraded")
        )
    ).scalar() or 0
    avg_latency = (
        await db.execute(
            select(func.avg(AISession.latency_ms)).where(
                AISession.latency_ms.is_not(None)
            )
        )
    ).scalar() or 0

    # 按类型统计
    type_stats_result = await db.execute(
        select(
            AISession.session_type,
            func.count(AISession.id).label("count"),
            func.avg(AISession.latency_ms).label("avg_latency"),
        ).group_by(AISession.session_type)
    )
    by_type = [
        {
            "type": row.session_type,
            "count": row.count,
            "avg_latency": round(float(row.avg_latency or 0), 1),
        }
        for row in type_stats_result
    ]

    # 按模型统计
    model_stats_result = await db.execute(
        select(
            AISession.model_provider,
            func.count(AISession.id).label("count"),
        )
        .where(AISession.model_provider.is_not(None))
        .group_by(AISession.model_provider)
    )
    by_model = [
        {"provider": row.model_provider, "count": row.count}
        for row in model_stats_result
    ]

    return AdminAISessionStatsResponse(
        total_sessions=total,
        success_count=success,
        failed_count=failed,
        degraded_count=degraded,
        success_rate=success / total if total > 0 else 0.0,
        avg_latency_ms=round(float(avg_latency), 1),
        by_type=by_type,
        by_model=by_model,
    )


# ---------------------------------------------------------------------------
# 周反馈管理
# ---------------------------------------------------------------------------


class AdminWeeklyFeedbackResponse(BaseModel):
    """管理员周反馈响应。"""

    id: uuid.UUID
    plan_id: uuid.UUID
    child_id: uuid.UUID
    child_nickname: str | None = None
    status: str
    summary_text: str | None = None
    selected_decision: str | None = None
    record_count_this_week: int | None = None
    completion_rate_this_week: float | None = None
    error_info: str | None = None
    created_at: str
    viewed_at: str | None = None
    decided_at: str | None = None

    model_config = {"from_attributes": True}


class AdminWeeklyFeedbackListResponse(BaseModel):
    """周反馈列表分页响应。"""

    feedbacks: list[AdminWeeklyFeedbackResponse]
    total: int
    has_more: bool


@router.get("/weekly-feedbacks", response_model=AdminWeeklyFeedbackListResponse)
async def list_weekly_feedbacks(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminWeeklyFeedbackListResponse:
    """分页获取周反馈列表。"""
    base_query = select(WeeklyFeedback)
    count_query = select(func.count(WeeklyFeedback.id))

    if status:
        base_query = base_query.where(WeeklyFeedback.status == status)
        count_query = count_query.where(WeeklyFeedback.status == status)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(WeeklyFeedback.child))
        .order_by(WeeklyFeedback.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    feedbacks = result.scalars().all()

    return AdminWeeklyFeedbackListResponse(
        feedbacks=[
            AdminWeeklyFeedbackResponse(
                id=f.id,
                plan_id=f.plan_id,
                child_id=f.child_id,
                child_nickname=f.child.nickname if f.child else None,
                status=f.status,
                summary_text=f.summary_text,
                selected_decision=f.selected_decision,
                record_count_this_week=f.record_count_this_week,
                completion_rate_this_week=f.completion_rate_this_week,
                error_info=f.error_info,
                created_at=str(f.created_at),
                viewed_at=str(f.viewed_at) if f.viewed_at else None,
                decided_at=str(f.decided_at) if f.decided_at else None,
            )
            for f in feedbacks
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.post("/weekly-feedbacks/{feedback_id}/retry")
async def retry_weekly_feedback(
    feedback_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
):
    """重试失败的周反馈生成。"""
    feedback = await db.get(WeeklyFeedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Weekly feedback not found")
    if feedback.status != "failed":
        raise HTTPException(
            status_code=400, detail="Only failed feedbacks can be retried"
        )

    feedback.status = "pending"
    feedback.error_info = None
    await db.flush()
    return {"detail": "Weekly feedback queued for retry"}


# ---------------------------------------------------------------------------
# 消息管理
# ---------------------------------------------------------------------------


class AdminMessageResponse(BaseModel):
    """管理员消息响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    child_id: uuid.UUID | None = None
    type: str
    title: str
    body: str | None = None
    read_status: str
    push_status: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class AdminMessageListResponse(BaseModel):
    """消息列表分页响应。"""

    messages: list[AdminMessageResponse]
    total: int
    has_more: bool


class AdminMessageStatsResponse(BaseModel):
    """消息统计。"""

    total_messages: int
    read_count: int
    unread_count: int
    read_rate: float
    push_sent_count: int
    push_delivered_count: int
    push_delivery_rate: float
    by_type: list[dict[str, Any]]


@router.get("/messages", response_model=AdminMessageListResponse)
async def list_messages(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: uuid.UUID | None = Query(None, description="按用户筛选"),
    message_type: str | None = Query(None, alias="type", description="按类型筛选"),
    read_status: str | None = Query(None, description="按阅读状态筛选"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminMessageListResponse:
    """分页获取消息列表。"""
    base_query = select(Message)
    count_query = select(func.count(Message.id))

    if user_id:
        base_query = base_query.where(Message.user_id == user_id)
        count_query = count_query.where(Message.user_id == user_id)
    if message_type:
        base_query = base_query.where(Message.type == message_type)
        count_query = count_query.where(Message.type == message_type)
    if read_status:
        _allowed = {"read", "unread"}
        if read_status not in _allowed:
            raise HTTPException(status_code=400, detail="Invalid read_status")
        base_query = base_query.where(Message.read_status == read_status)
        count_query = count_query.where(Message.read_status == read_status)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(Message.user))
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()

    return AdminMessageListResponse(
        messages=[
            AdminMessageResponse(
                id=m.id,
                user_id=m.user_id,
                user_email=m.user.email if m.user else None,
                child_id=m.child_id,
                type=m.type,
                title=m.title,
                body=m.body,
                read_status=m.read_status,
                push_status=m.push_status,
                created_at=str(m.created_at),
            )
            for m in messages
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/messages/stats", response_model=AdminMessageStatsResponse)
async def get_message_stats(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminMessageStatsResponse:
    """获取消息统计数据。"""
    total = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    read_count = (
        await db.execute(
            select(func.count(Message.id)).where(Message.read_status == "read")
        )
    ).scalar() or 0
    unread_count = total - read_count

    push_sent = (
        await db.execute(
            select(func.count(Message.id)).where(
                Message.push_status.in_(["sent", "delivered"])
            )
        )
    ).scalar() or 0
    push_delivered = (
        await db.execute(
            select(func.count(Message.id)).where(Message.push_status == "delivered")
        )
    ).scalar() or 0

    # 按类型统计
    type_result = await db.execute(
        select(
            Message.type,
            func.count(Message.id).label("count"),
        ).group_by(Message.type)
    )
    by_type = [{"type": row.type, "count": row.count} for row in type_result]

    return AdminMessageStatsResponse(
        total_messages=total,
        read_count=read_count,
        unread_count=unread_count,
        read_rate=read_count / total if total > 0 else 0.0,
        push_sent_count=push_sent,
        push_delivered_count=push_delivered,
        push_delivery_rate=push_delivered / push_sent if push_sent > 0 else 0.0,
        by_type=by_type,
    )


# ---------------------------------------------------------------------------
# 设备管理
# ---------------------------------------------------------------------------


class AdminDeviceResponse(BaseModel):
    """管理员设备响应。"""

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str | None = None
    platform: str | None = None
    app_version: str | None = None
    is_active: bool
    last_active_at: str | None = None
    push_token_preview: str | None = None

    model_config = {"from_attributes": True}


class AdminDeviceListResponse(BaseModel):
    """设备列表分页响应。"""

    devices: list[AdminDeviceResponse]
    total: int
    has_more: bool


class AdminDeviceStatsResponse(BaseModel):
    """设备统计。"""

    total_devices: int
    active_devices: int
    inactive_devices: int
    by_platform: list[dict[str, Any]]
    by_version: list[dict[str, Any]]


@router.get("/devices", response_model=AdminDeviceListResponse)
async def list_devices(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    platform: str | None = Query(None, description="按平台筛选"),
    is_active: bool | None = Query(None, description="按活跃状态筛选"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminDeviceListResponse:
    """分页获取设备列表。"""
    base_query = select(Device)
    count_query = select(func.count(Device.id))

    if platform:
        base_query = base_query.where(Device.platform == platform)
        count_query = count_query.where(Device.platform == platform)
    if is_active is not None:
        base_query = base_query.where(Device.is_active == is_active)
        count_query = count_query.where(Device.is_active == is_active)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.options(selectinload(Device.user))
        .order_by(Device.last_active_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    devices = result.scalars().all()

    return AdminDeviceListResponse(
        devices=[
            AdminDeviceResponse(
                id=d.id,
                user_id=d.user_id,
                user_email=d.user.email if d.user else None,
                platform=d.platform,
                app_version=d.app_version,
                is_active=d.is_active,
                last_active_at=str(d.last_active_at) if d.last_active_at else None,
                push_token_preview=(
                    f"{d.push_token[:8]}...{d.push_token[-4:]}"
                    if d.push_token and len(d.push_token) > 12
                    else d.push_token
                ),
            )
            for d in devices
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/devices/stats", response_model=AdminDeviceStatsResponse)
async def get_device_stats(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminDeviceStatsResponse:
    """获取设备统计数据。"""
    total = (await db.execute(select(func.count(Device.id)))).scalar() or 0
    active = (
        await db.execute(
            select(func.count(Device.id)).where(Device.is_active.is_(True))
        )
    ).scalar() or 0

    platform_result = await db.execute(
        select(Device.platform, func.count(Device.id).label("count"))
        .where(Device.platform.is_not(None))
        .group_by(Device.platform)
    )
    by_platform = [
        {"platform": row.platform, "count": row.count} for row in platform_result
    ]

    version_result = await db.execute(
        select(Device.app_version, func.count(Device.id).label("count"))
        .where(Device.app_version.is_not(None))
        .group_by(Device.app_version)
        .order_by(func.count(Device.id).desc())
        .limit(10)
    )
    by_version = [
        {"version": row.app_version, "count": row.count} for row in version_result
    ]

    return AdminDeviceStatsResponse(
        total_devices=total,
        active_devices=active,
        inactive_devices=total - active,
        by_platform=by_platform,
        by_version=by_version,
    )


# ---------------------------------------------------------------------------
# 推送日志管理
# ---------------------------------------------------------------------------


class AdminPushLogResponse(BaseModel):
    """管理员推送日志响应。"""

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    rule_id: str | None = None
    channel: str | None = None
    status: str
    error: str | None = None
    latency_ms: int | None = None
    fallback_used: bool | None = None
    fallback_channel: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class AdminPushLogListResponse(BaseModel):
    """推送日志列表分页响应。"""

    logs: list[AdminPushLogResponse]
    total: int
    has_more: bool


class AdminPushLogStatsResponse(BaseModel):
    """推送日志统计。"""

    total_logs: int
    sent_count: int
    delivered_count: int
    failed_count: int
    delivery_rate: float
    avg_latency_ms: float
    fallback_rate: float
    by_channel: list[dict[str, Any]]
    by_rule: list[dict[str, Any]]


@router.get("/push-logs", response_model=AdminPushLogListResponse)
async def list_push_logs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    channel: str | None = Query(None, description="按渠道筛选"),
    status: str | None = Query(None, description="按状态筛选"),
    rule_id: str | None = Query(None, description="按规则筛选"),
    user_id: uuid.UUID | None = Query(None, description="按用户筛选"),
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminPushLogListResponse:
    """分页获取推送日志列表。"""
    base_query = select(PushLog)
    count_query = select(func.count(PushLog.id))

    if channel:
        base_query = base_query.where(PushLog.channel == channel)
        count_query = count_query.where(PushLog.channel == channel)
    if status:
        base_query = base_query.where(PushLog.status == status)
        count_query = count_query.where(PushLog.status == status)
    if rule_id:
        base_query = base_query.where(PushLog.rule_id == rule_id)
        count_query = count_query.where(PushLog.rule_id == rule_id)
    if user_id:
        base_query = base_query.where(PushLog.user_id == user_id)
        count_query = count_query.where(PushLog.user_id == user_id)

    total = (await db.execute(count_query)).scalar() or 0

    result = await db.execute(
        base_query.order_by(PushLog.created_at.desc()).offset(offset).limit(limit)
    )
    logs = result.scalars().all()

    # 批量获取 user emails
    user_ids = {log.user_id for log in logs if log.user_id}
    user_email_map: dict[uuid.UUID, str] = {}
    if user_ids:
        users_result = await db.execute(
            select(User.id, User.email).where(User.id.in_(user_ids))
        )
        user_email_map = {row.id: row.email for row in users_result}

    return AdminPushLogListResponse(
        logs=[
            AdminPushLogResponse(
                id=log.id,
                user_id=log.user_id,
                user_email=user_email_map.get(log.user_id) if log.user_id else None,
                rule_id=log.rule_id,
                channel=log.channel,
                status=log.status,
                error=log.error,
                latency_ms=log.latency_ms,
                fallback_used=log.fallback_used,
                fallback_channel=log.fallback_channel,
                created_at=str(log.created_at),
            )
            for log in logs
        ],
        total=total,
        has_more=(offset + limit) < total,
    )


@router.get("/push-logs/stats", response_model=AdminPushLogStatsResponse)
async def get_push_log_stats(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminPushLogStatsResponse:
    """获取推送日志统计数据。"""
    total = (await db.execute(select(func.count(PushLog.id)))).scalar() or 0
    sent = (
        await db.execute(
            select(func.count(PushLog.id)).where(PushLog.status == "sent")
        )
    ).scalar() or 0
    delivered = (
        await db.execute(
            select(func.count(PushLog.id)).where(PushLog.status == "delivered")
        )
    ).scalar() or 0
    failed = (
        await db.execute(
            select(func.count(PushLog.id)).where(PushLog.status == "failed")
        )
    ).scalar() or 0
    avg_latency = (
        await db.execute(
            select(func.avg(PushLog.latency_ms)).where(
                PushLog.latency_ms.is_not(None)
            )
        )
    ).scalar() or 0
    fallback_count = (
        await db.execute(
            select(func.count(PushLog.id)).where(PushLog.fallback_used.is_(True))
        )
    ).scalar() or 0

    # 按渠道统计
    channel_result = await db.execute(
        select(
            PushLog.channel,
            func.count(PushLog.id).label("count"),
            func.sum(case((PushLog.status == "failed", 1), else_=0)).label("failed"),
        )
        .where(PushLog.channel.is_not(None))
        .group_by(PushLog.channel)
    )
    by_channel = [
        {
            "channel": row.channel,
            "count": int(row.count),  # pyright: ignore[reportArgumentType]
            "failed": int(row.failed or 0),
            "failure_rate": round(int(row.failed or 0) / max(int(row.count), 1), 3) if int(row.count) > 0 else 0,
        }
        for row in channel_result
    ]

    # 按规则统计
    rule_result = await db.execute(
        select(
            PushLog.rule_id,
            func.count(PushLog.id).label("count"),
        )
        .where(PushLog.rule_id.is_not(None))
        .group_by(PushLog.rule_id)
        .order_by(func.count(PushLog.id).desc())
        .limit(10)
    )
    by_rule = [
        {"rule_id": row.rule_id, "count": row.count} for row in rule_result
    ]

    return AdminPushLogStatsResponse(
        total_logs=total,
        sent_count=sent,
        delivered_count=delivered,
        failed_count=failed,
        delivery_rate=(sent + delivered) / total if total > 0 else 0.0,
        avg_latency_ms=round(float(avg_latency), 1),
        fallback_rate=fallback_count / total if total > 0 else 0.0,
        by_channel=by_channel,
        by_rule=by_rule,
    )


# ---------------------------------------------------------------------------
# 综合统计（增强版 stats，含更多维度）
# ---------------------------------------------------------------------------


class AdminEnhancedStatsResponse(BaseModel):
    """增强版系统统计。"""

    # 基础计数
    total_users: int
    total_children: int
    total_plans: int
    total_records: int
    total_messages: int
    total_ai_sessions: int
    total_devices: int
    total_push_logs: int
    total_weekly_feedbacks: int
    total_channel_bindings: int

    # 活跃指标
    active_plans: int
    active_devices: int
    active_bindings: int

    # 今日指标
    today_new_users: int
    today_new_records: int
    today_ai_sessions: int
    today_push_count: int


@router.get("/enhanced-stats", response_model=AdminEnhancedStatsResponse)
async def get_enhanced_stats(
    db: AsyncSession = Depends(get_db),
    _admin_id: uuid.UUID = Depends(get_current_admin_id),
) -> AdminEnhancedStatsResponse:
    """获取增强版系统统计数据。"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 基础计数
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    children_count = (await db.execute(select(func.count(Child.id)))).scalar() or 0
    plans_count = (await db.execute(select(func.count(Plan.id)))).scalar() or 0
    records_count = (await db.execute(select(func.count(Record.id)))).scalar() or 0
    messages_count = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    ai_sessions_count = (
        await db.execute(select(func.count(AISession.id)))
    ).scalar() or 0
    devices_count = (await db.execute(select(func.count(Device.id)))).scalar() or 0
    push_logs_count = (
        await db.execute(select(func.count(PushLog.id)))
    ).scalar() or 0
    feedbacks_count = (
        await db.execute(select(func.count(WeeklyFeedback.id)))
    ).scalar() or 0
    bindings_count = (
        await db.execute(select(func.count(ChannelBinding.id)))
    ).scalar() or 0

    # 活跃指标
    active_plans = (
        await db.execute(
            select(func.count(Plan.id)).where(Plan.status == "active")
        )
    ).scalar() or 0
    active_devices = (
        await db.execute(
            select(func.count(Device.id)).where(Device.is_active.is_(True))
        )
    ).scalar() or 0
    active_bindings = (
        await db.execute(
            select(func.count(ChannelBinding.id)).where(
                ChannelBinding.is_active.is_(True)
            )
        )
    ).scalar() or 0

    # 今日指标
    today_users = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
    ).scalar() or 0
    today_records = (
        await db.execute(
            select(func.count(Record.id)).where(Record.created_at >= today_start)
        )
    ).scalar() or 0
    today_sessions = (
        await db.execute(
            select(func.count(AISession.id)).where(
                AISession.created_at >= today_start
            )
        )
    ).scalar() or 0
    today_pushes = (
        await db.execute(
            select(func.count(PushLog.id)).where(PushLog.created_at >= today_start)
        )
    ).scalar() or 0

    return AdminEnhancedStatsResponse(
        total_users=users_count,
        total_children=children_count,
        total_plans=plans_count,
        total_records=records_count,
        total_messages=messages_count,
        total_ai_sessions=ai_sessions_count,
        total_devices=devices_count,
        total_push_logs=push_logs_count,
        total_weekly_feedbacks=feedbacks_count,
        total_channel_bindings=bindings_count,
        active_plans=active_plans,
        active_devices=active_devices,
        active_bindings=active_bindings,
        today_new_users=today_users,
        today_new_records=today_records,
        today_ai_sessions=today_sessions,
        today_push_count=today_pushes,
    )
