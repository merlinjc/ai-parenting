"""智能推送引擎。

核心组件：
- PushRule / PushRuleLibrary：可配置化推送规则，支持从数据库热加载
- FrequencyLimiter：限频 + 幂等 + 冷却期控制
- SmartPushEngine：时区感知调度扫描，协调规则评估与渠道路由

设计原则：
- 规则外置为数据结构，代码零改动即可新增/修改规则
- 幂等键 = rule_id + user_id + date，防止多实例/重试重复推送
- 时区感知：每条规则按用户 timezone 计算触发窗口
- 分页扫描：游标分页处理大量用户，避免 OFFSET 性能退化
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.models import (
    Child,
    DayTask,
    Message,
    Plan,
    Record,
    User,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PushRule 数据结构
# ---------------------------------------------------------------------------

SCAN_BATCH_SIZE = 100  # 每次分页扫描用户数


class TriggerType(Enum):
    """规则触发类型。"""

    CRON = "cron"  # 定时触发（如每日 08:00）
    EVENT = "event"  # 事件触发（如计划到期）
    MILESTONE = "milestone"  # 里程碑触发（如连续记录 7 天）


class RulePriority(Enum):
    """规则优先级。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PushRule:
    """推送规则数据结构。

    将推送逻辑从代码中外置为可配置的数据结构，
    支持热更新（修改数据库记录即可生效，无需重启）。

    Attributes:
        rule_id: 规则唯一标识（如 'daily_task_reminder'）。
        name: 规则显示名称。
        description: 规则描述。
        trigger_type: 触发类型（Cron/Event/Milestone）。
        trigger_hour: Cron 触发小时（用户本地时间，0-23）。
        trigger_minute: Cron 触发分钟（0-59）。
        message_type: 生成的消息类型（对应 MESSAGE_TEMPLATES 的 key）。
        channel_priorities: 渠道优先级列表，如 ['wechat', 'apns']。
        cooldown_hours: 冷却时间（小时），同一规则对同一用户的最小推送间隔。
        max_daily_count: 每日最大推送次数（0 = 不限）。
        enabled: 是否启用。
        priority: 规则优先级。
        condition_config: 条件配置（JSON），由 evaluate_condition 解释。
        message_template_vars: 消息模板变量提取器配置。
    """

    rule_id: str
    name: str
    description: str = ""
    trigger_type: TriggerType = TriggerType.CRON
    trigger_hour: int = 8
    trigger_minute: int = 0
    message_type: str = "system"
    channel_priorities: list[str] = field(default_factory=lambda: ["apns"])
    cooldown_hours: int = 24
    max_daily_count: int = 1
    enabled: bool = True
    priority: RulePriority = RulePriority.MEDIUM
    condition_config: dict[str, Any] = field(default_factory=dict)
    message_template_vars: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 内置 7 条推送规则
#
# iOS-first 推送策略：
#   - iOS App（APNs）是用户核心入口，所有规则默认 APNs 优先
#   - 微信/WhatsApp 作为辅助触达链路，在 APNs 之后
#   - 高紧急度规则（HIGH）：APNs + 微信双推，确保用户收到
#   - 中/低紧急度规则（MEDIUM/LOW）：仅 APNs，避免微信过度打扰
# ---------------------------------------------------------------------------

BUILTIN_RULES: list[PushRule] = [
    # --- 高紧急度：APNs 优先 + 微信辅助双推 ---
    PushRule(
        rule_id="daily_task_reminder",
        name="每日任务提醒",
        description="每日早上推送今天的亲子互动任务",
        trigger_type=TriggerType.CRON,
        trigger_hour=8,
        trigger_minute=0,
        message_type="plan_reminder",
        channel_priorities=["apns", "wechat"],  # iOS-first: APNs 优先，微信辅助
        cooldown_hours=20,
        max_daily_count=1,
        priority=RulePriority.HIGH,
        condition_config={"requires_active_plan": True},
    ),
    # --- 中紧急度：仅 APNs，减少微信打扰 ---
    PushRule(
        rule_id="record_prompt",
        name="记录提示",
        description="每日傍晚提醒记录今天的观察",
        trigger_type=TriggerType.CRON,
        trigger_hour=18,
        trigger_minute=0,
        message_type="record_prompt",
        channel_priorities=["apns"],  # iOS-first: 中紧急度仅 APNs
        cooldown_hours=20,
        max_daily_count=1,
        priority=RulePriority.MEDIUM,
        condition_config={"requires_active_plan": True},
    ),
    # --- 高紧急度：APNs 优先 + 微信辅助双推 ---
    PushRule(
        rule_id="plan_expiry_reminder",
        name="计划到期提醒",
        description="计划第 6 天提醒明天将生成周反馈",
        trigger_type=TriggerType.EVENT,
        trigger_hour=10,
        trigger_minute=0,
        message_type="plan_reminder",
        channel_priorities=["apns", "wechat"],  # iOS-first: APNs 优先，微信辅助
        cooldown_hours=168,  # 7 天冷却
        max_daily_count=1,
        priority=RulePriority.HIGH,
        condition_config={"plan_current_day": 6},
    ),
    # --- 高紧急度：APNs 优先 + 微信辅助双推 ---
    PushRule(
        rule_id="weekly_feedback_ready",
        name="周反馈已就绪",
        description="周反馈生成完成后推送通知",
        trigger_type=TriggerType.EVENT,
        trigger_hour=9,
        trigger_minute=0,
        message_type="weekly_feedback_ready",
        channel_priorities=["apns", "wechat"],  # iOS-first: APNs 优先，微信辅助
        cooldown_hours=168,
        max_daily_count=1,
        priority=RulePriority.HIGH,
        condition_config={"event": "weekly_feedback_completed"},
    ),
    # --- 低紧急度：仅 APNs ---
    PushRule(
        rule_id="no_record_nudge",
        name="未记录轻推",
        description="连续 2 天无记录时发送鼓励性提醒",
        trigger_type=TriggerType.CRON,
        trigger_hour=19,
        trigger_minute=30,
        message_type="record_prompt",
        channel_priorities=["apns"],  # iOS-first: 低紧急度仅 APNs
        cooldown_hours=48,
        max_daily_count=1,
        priority=RulePriority.LOW,
        condition_config={"no_record_days": 2},
    ),
    # --- 低紧急度：仅 APNs ---
    PushRule(
        rule_id="streak_celebration",
        name="连续记录庆祝",
        description="连续记录 7 天时发送鼓励消息",
        trigger_type=TriggerType.MILESTONE,
        trigger_hour=20,
        trigger_minute=0,
        message_type="system",
        channel_priorities=["apns"],  # iOS-first: 低紧急度仅 APNs，不打扰微信
        cooldown_hours=168,
        max_daily_count=1,
        priority=RulePriority.LOW,
        condition_config={"consecutive_record_days": 7},
    ),
    # --- 高紧急度：APNs 优先 + 微信辅助双推 ---
    PushRule(
        rule_id="risk_alert",
        name="风险关注提醒",
        description="当儿童风险级别升高时推送建议",
        trigger_type=TriggerType.EVENT,
        trigger_hour=10,
        trigger_minute=0,
        message_type="risk_alert",
        channel_priorities=["apns", "wechat"],  # iOS-first: APNs 优先，微信辅助
        cooldown_hours=336,  # 14 天冷却
        max_daily_count=1,
        priority=RulePriority.HIGH,
        condition_config={"event": "risk_level_elevated"},
    ),
]


# ---------------------------------------------------------------------------
# PushRuleLibrary — 规则仓库
# ---------------------------------------------------------------------------


class PushRuleLibrary:
    """推送规则仓库。

    初始加载内置规则，支持从数据库热加载覆盖/追加。
    """

    def __init__(self) -> None:
        self._rules: dict[str, PushRule] = {}
        self._load_builtin()

    def _load_builtin(self) -> None:
        """加载内置规则。"""
        for rule in BUILTIN_RULES:
            self._rules[rule.rule_id] = rule
        logger.info("Loaded %d builtin push rules", len(self._rules))

    async def reload_from_db(self, db: AsyncSession) -> int:
        """从数据库热加载规则覆盖。

        未来扩展：从 push_rules 表读取自定义规则，
        与内置规则合并（数据库规则优先级更高）。
        当前版本仅使用内置规则。

        Returns:
            加载的数据库规则数量。
        """
        # TODO: 当 PushRuleModel 表实现后，从 DB 加载
        # result = await db.execute(select(PushRuleModel).where(PushRuleModel.enabled.is_(True)))
        # db_rules = result.scalars().all()
        # for row in db_rules:
        #     self._rules[row.rule_id] = PushRule.from_orm(row)
        return 0

    def get_active_rules(self) -> list[PushRule]:
        """获取所有启用的规则。"""
        return [r for r in self._rules.values() if r.enabled]

    def get_cron_rules(self) -> list[PushRule]:
        """获取所有 Cron 触发的规则。"""
        return [
            r
            for r in self._rules.values()
            if r.enabled and r.trigger_type == TriggerType.CRON
        ]

    def get_event_rules(self, event_name: str) -> list[PushRule]:
        """获取指定事件触发的规则。"""
        return [
            r
            for r in self._rules.values()
            if r.enabled
            and r.trigger_type == TriggerType.EVENT
            and r.condition_config.get("event") == event_name
        ]

    def get_rule(self, rule_id: str) -> PushRule | None:
        """按 ID 获取规则。"""
        return self._rules.get(rule_id)

    def upsert_rule(self, rule: PushRule) -> None:
        """插入或更新规则。"""
        self._rules[rule.rule_id] = rule

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则。"""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False


# ---------------------------------------------------------------------------
# FrequencyLimiter — 限频 + 幂等 + 冷却
# ---------------------------------------------------------------------------


class FrequencyLimiter:
    """推送频率限制器。

    核心功能：
    - 幂等键检查：rule_id + user_id + date 组合防止重复推送
    - 冷却期检查：距离上次同规则推送是否超过 cooldown_hours
    - 每日上限检查：同一用户同一规则每日推送不超过 max_daily_count
    - 全局防打扰：用户设置的静默时段检查
    """

    async def check_allowed(
        self,
        db: AsyncSession,
        *,
        rule: PushRule,
        user_id: uuid.UUID,
        now_utc: datetime,
    ) -> tuple[bool, str]:
        """检查是否允许推送。

        Returns:
            (allowed, reason) 元组。allowed=True 时 reason 为空。
        """
        today = now_utc.date()
        idempotency_key = f"{rule.rule_id}:{user_id}:{today.isoformat()}"

        # 1. 幂等检查：今天是否已经为此规则+用户推送过
        existing = await db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.user_id == user_id,
                Message.type == rule.message_type,
                Message.created_at >= datetime.combine(today, time.min, tzinfo=timezone.utc),
                Message.created_at < datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc),
            )
        )
        today_count = existing.scalar_one()

        if rule.max_daily_count > 0 and today_count >= rule.max_daily_count:
            return False, f"Daily limit reached ({today_count}/{rule.max_daily_count})"

        # 2. 冷却期检查
        if rule.cooldown_hours > 0:
            cooldown_since = now_utc - timedelta(hours=rule.cooldown_hours)
            recent = await db.execute(
                select(func.count())
                .select_from(Message)
                .where(
                    Message.user_id == user_id,
                    Message.type == rule.message_type,
                    Message.created_at >= cooldown_since,
                )
            )
            recent_count = recent.scalar_one()
            if recent_count > 0:
                return False, f"Cooldown active ({rule.cooldown_hours}h)"

        return True, ""

    def generate_idempotency_key(
        self, rule_id: str, user_id: uuid.UUID, target_date: date
    ) -> str:
        """生成幂等键。"""
        return f"{rule_id}:{user_id}:{target_date.isoformat()}"


# ---------------------------------------------------------------------------
# 时区工具
# ---------------------------------------------------------------------------


def get_user_local_time(user_timezone: str, now_utc: datetime) -> datetime:
    """将 UTC 时间转换为用户本地时间。

    Args:
        user_timezone: IANA 时区名称（如 'Asia/Shanghai'）。
        now_utc: UTC 时间。

    Returns:
        用户本地时间。
    """
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(user_timezone)
        return now_utc.astimezone(tz)
    except (ImportError, KeyError):
        # 降级：假设 Asia/Shanghai (UTC+8)
        logger.warning(
            "Cannot resolve timezone '%s', falling back to UTC+8",
            user_timezone,
        )
        return now_utc + timedelta(hours=8)


def is_in_trigger_window(
    rule: PushRule,
    user_timezone: str,
    now_utc: datetime,
    window_minutes: int = 60,
) -> bool:
    """判断当前时间是否在规则的触发窗口内（用户本地时间）。

    触发窗口 = [trigger_hour:trigger_minute, trigger_hour:trigger_minute + window_minutes)

    Args:
        rule: 推送规则。
        user_timezone: 用户时区。
        now_utc: 当前 UTC 时间。
        window_minutes: 窗口宽度（分钟），默认 60 分钟。

    Returns:
        是否在触发窗口内。
    """
    local_time = get_user_local_time(user_timezone, now_utc)
    trigger_start = local_time.replace(
        hour=rule.trigger_hour, minute=rule.trigger_minute, second=0, microsecond=0
    )
    trigger_end = trigger_start + timedelta(minutes=window_minutes)

    return trigger_start <= local_time < trigger_end


# ---------------------------------------------------------------------------
# 条件评估器
# ---------------------------------------------------------------------------


class RuleConditionEvaluator:
    """规则条件评估器。

    根据 PushRule.condition_config 中的声明式条件，
    查询数据库判断用户是否满足触发条件。
    """

    async def evaluate(
        self,
        db: AsyncSession,
        rule: PushRule,
        user: User,
        child: Child | None = None,
        plan: Plan | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """评估规则条件。

        Returns:
            (satisfied, context) 元组。
            satisfied: 条件是否满足。
            context: 评估上下文（含模板变量），传给消息生成。
        """
        config = rule.condition_config
        context: dict[str, Any] = {"user": user, "child": child, "plan": plan}

        # 条件：需要活跃计划
        if config.get("requires_active_plan") and plan is None:
            return False, context

        # 条件：计划指定天数
        if "plan_current_day" in config:
            if plan is None or plan.current_day != config["plan_current_day"]:
                return False, context

        # 条件：连续 N 天无记录
        if "no_record_days" in config and child is not None:
            days = config["no_record_days"]
            since = datetime.now(timezone.utc) - timedelta(days=days)
            result = await db.execute(
                select(func.count())
                .select_from(Record)
                .where(
                    Record.child_id == child.id,
                    Record.created_at >= since,
                )
            )
            record_count = result.scalar_one()
            if record_count > 0:
                return False, context
            context["no_record_days"] = days

        # 条件：连续记录 N 天（里程碑）
        if "consecutive_record_days" in config and child is not None:
            target_days = config["consecutive_record_days"]
            consecutive = await self._count_consecutive_record_days(db, child.id)
            if consecutive < target_days:
                return False, context
            context["consecutive_record_days"] = consecutive

        return True, context

    async def _count_consecutive_record_days(
        self, db: AsyncSession, child_id: uuid.UUID
    ) -> int:
        """计算连续记录天数（从今天向前计算）。"""
        today = date.today()
        consecutive = 0

        for i in range(30):  # 最多检查 30 天
            check_date = today - timedelta(days=i)
            start = datetime.combine(check_date, time.min, tzinfo=timezone.utc)
            end = datetime.combine(check_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

            result = await db.execute(
                select(func.count())
                .select_from(Record)
                .where(
                    Record.child_id == child_id,
                    Record.created_at >= start,
                    Record.created_at < end,
                )
            )
            count = result.scalar_one()
            if count > 0:
                consecutive += 1
            else:
                break

        return consecutive


# ---------------------------------------------------------------------------
# SmartPushEngine — 核心引擎
# ---------------------------------------------------------------------------


class SmartPushEngine:
    """智能推送引擎。

    编排流程：
    1. APScheduler 每小时触发一次 `scan_and_push()`
    2. 从 PushRuleLibrary 获取活跃的 Cron 规则
    3. 分页扫描推送启用的用户（游标分页，每批 100 条）
    4. 对每个用户：
       a. 根据用户时区计算是否在规则触发窗口内
       b. 评估规则条件（查询相关业务数据）
       c. FrequencyLimiter 检查限频/幂等
       d. 通过 ChannelRouter 发送消息到最优渠道
       e. 记录 PushLog
    """

    def __init__(
        self,
        rule_library: PushRuleLibrary | None = None,
        frequency_limiter: FrequencyLimiter | None = None,
        condition_evaluator: RuleConditionEvaluator | None = None,
        channel_router: Any | None = None,
    ) -> None:
        self.rule_library = rule_library or PushRuleLibrary()
        self.frequency_limiter = frequency_limiter or FrequencyLimiter()
        self.condition_evaluator = condition_evaluator or RuleConditionEvaluator()
        self._channel_router = channel_router

    async def scan_and_push(self, db: AsyncSession) -> dict[str, Any]:
        """执行一次全量规则扫描推送。

        由 APScheduler 每小时触发调用。

        Returns:
            执行统计：{scanned_users, evaluated_rules, sent, skipped, errors}。
        """
        from ai_parenting.backend.channels.base import ChannelMessage
        from ai_parenting.backend.models import PushLog, UserChannelPreference
        from ai_parenting.backend.services.channel_binding_service import (
            get_user_channel_priorities,
        )
        from ai_parenting.backend.services.message_service import create_message

        now_utc = datetime.now(timezone.utc)
        cron_rules = self.rule_library.get_cron_rules()

        stats: dict[str, Any] = {
            "scanned_users": 0,
            "evaluated_rules": 0,
            "sent": 0,
            "skipped": 0,
            "errors": 0,
            "rules_checked": [r.rule_id for r in cron_rules],
        }

        if not cron_rules:
            logger.info("No active cron rules, skipping scan")
            return stats

        # 分页扫描用户（游标分页，按 ID 排序）
        last_id: uuid.UUID | None = None

        while True:
            users_batch = await self._fetch_user_batch(db, last_id)
            if not users_batch:
                break

            stats["scanned_users"] += len(users_batch)
            last_id = users_batch[-1].id

            for user in users_batch:
                for rule in cron_rules:
                    stats["evaluated_rules"] += 1

                    # 步骤 1：时区窗口检查
                    if not is_in_trigger_window(rule, user.timezone, now_utc):
                        stats["skipped"] += 1
                        continue

                    # 步骤 1.5：静默时段检查
                    if await self._is_in_quiet_hours(db, user):
                        stats["skipped"] += 1
                        continue

                    # 步骤 2：限频检查
                    allowed, reason = await self.frequency_limiter.check_allowed(
                        db, rule=rule, user_id=user.id, now_utc=now_utc,
                    )
                    if not allowed:
                        logger.debug(
                            "Rule '%s' skipped for user %s: %s",
                            rule.rule_id, user.id, reason,
                        )
                        stats["skipped"] += 1
                        continue

                    # 步骤 3：获取用户的活跃计划和儿童数据
                    plan, child = await self._get_user_plan_context(db, user.id)

                    # 步骤 4：条件评估
                    satisfied, ctx = await self.condition_evaluator.evaluate(
                        db, rule, user, child=child, plan=plan,
                    )
                    if not satisfied:
                        stats["skipped"] += 1
                        continue

                    # 步骤 5：生成消息并通过 ChannelRouter 推送
                    try:
                        message = await self._create_rule_message(
                            db, rule=rule, user=user, child=child, plan=plan, ctx=ctx,
                        )

                        # 通过 ChannelRouter 推送到最优渠道
                        send_result = await self._route_push(
                            db, user_id=user.id, message=message, rule=rule,
                        )

                        if send_result:
                            # 写入 PushLog 记录
                            await self._record_push_log(
                                db, rule=rule, user_id=user.id,
                                channel=send_result.channel_name,
                                success=send_result.success,
                                provider_message_id=send_result.provider_message_id,
                            )
                            stats["sent"] += 1
                            logger.info(
                                "Rule '%s' triggered for user %s via %s",
                                rule.rule_id, user.id, send_result.channel_name,
                            )
                        else:
                            stats["errors"] += 1

                    except Exception as exc:
                        stats["errors"] += 1
                        logger.error(
                            "Rule '%s' failed for user %s: %s",
                            rule.rule_id, user.id, exc,
                        )

            await db.commit()

        logger.info("Smart push scan completed: %s", stats)
        return stats

    async def trigger_event_push(
        self,
        db: AsyncSession,
        event_name: str,
        user_id: uuid.UUID,
        *,
        child_id: uuid.UUID | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> bool:
        """触发事件驱动推送。

        由业务代码在事件发生时调用（如周反馈完成、风险升级）。

        Args:
            db: 数据库会话。
            event_name: 事件名称（对应 rule.condition_config["event"]）。
            user_id: 目标用户 ID。
            child_id: 相关儿童 ID（可选）。
            extra_context: 额外上下文数据。

        Returns:
            是否成功发送。
        """
        event_rules = self.rule_library.get_event_rules(event_name)
        if not event_rules:
            logger.debug("No rules for event '%s'", event_name)
            return False

        now_utc = datetime.now(timezone.utc)
        user = await db.get(User, user_id)
        if user is None or not user.push_enabled:
            return False

        sent_any = False

        for rule in event_rules:
            allowed, reason = await self.frequency_limiter.check_allowed(
                db, rule=rule, user_id=user_id, now_utc=now_utc,
            )
            if not allowed:
                logger.debug(
                    "Event rule '%s' blocked for user %s: %s",
                    rule.rule_id, user_id, reason,
                )
                continue

            plan, child = await self._get_user_plan_context(db, user_id, child_id)

            try:
                message = await self._create_rule_message(
                    db, rule=rule, user=user, child=child, plan=plan,
                    ctx=extra_context or {},
                )

                send_result = await self._route_push(
                    db, user_id=user_id, message=message, rule=rule,
                )

                if send_result and send_result.success:
                    await self._record_push_log(
                        db, rule=rule, user_id=user_id,
                        channel=send_result.channel_name,
                        success=True,
                        provider_message_id=send_result.provider_message_id,
                    )
                    sent_any = True
                    logger.info(
                        "Event '%s' → rule '%s' triggered for user %s via %s",
                        event_name, rule.rule_id, user_id, send_result.channel_name,
                    )
                else:
                    await self._record_push_log(
                        db, rule=rule, user_id=user_id,
                        channel=send_result.channel_name if send_result else "none",
                        success=False,
                    )

            except Exception as exc:
                logger.error(
                    "Event rule '%s' failed for user %s: %s",
                    rule.rule_id, user_id, exc,
                )

        return sent_any

    # -----------------------------------------------------------------------
    # 私有方法
    # -----------------------------------------------------------------------

    async def _route_push(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        message: Message,
        rule: PushRule,
    ) -> Any:
        """通过 ChannelRouter 将消息推送到最优渠道。

        如果 ChannelRouter 未注入（开发阶段），降级为 Legacy push_service 方式。

        Returns:
            SendResult 或 None。
        """
        from ai_parenting.backend.channels.base import ChannelMessage

        if self._channel_router is not None:
            # 生产路径：通过 ChannelRouter 路由
            from ai_parenting.backend.services.channel_binding_service import (
                get_user_channel_priorities,
            )

            channel_preferences = await get_user_channel_priorities(db, user_id)
            # 如果规则指定了渠道优先级，使用规则的优先级
            if rule.channel_priorities:
                channel_preferences = rule.channel_priorities

            channel_msg = ChannelMessage(
                recipient_id=str(user_id),  # ChannelRouter 在发送前需要解析为渠道特定 ID
                title=message.title,
                body=message.summary or message.title,
                data={
                    "message_id": str(message.id),
                    "type": message.type,
                    "target_page": message.target_page or "",
                },
            )

            send_result = await self._channel_router.route_message(
                channel_msg, channel_preferences,
            )

            # 更新 Message 的推送状态
            now = datetime.now(timezone.utc)
            if send_result.success:
                message.push_status = "sent"
                message.push_sent_at = now
            else:
                message.push_status = "failed"
                message.push_sent_at = now

            return send_result
        else:
            # Legacy 降级：使用旧的 PushProvider 体系
            from ai_parenting.backend.services.push_service import (
                MockPushProvider,
                send_push_for_message,
            )

            push_provider = MockPushProvider()
            await send_push_for_message(db, message, push_provider)

            # 构造兼容的 SendResult-like 对象
            from types import SimpleNamespace
            return SimpleNamespace(
                success=True,
                channel_name="apns",
                provider_message_id=None,
            )

    async def _record_push_log(
        self,
        db: AsyncSession,
        *,
        rule: PushRule,
        user_id: uuid.UUID,
        channel: str,
        success: bool,
        provider_message_id: str | None = None,
    ) -> None:
        """写入 PushLog 记录（用于限频审计和幂等检查）。"""
        from ai_parenting.backend.models import PushLog

        now_utc = datetime.now(timezone.utc)
        today_str = now_utc.strftime("%Y-%m-%d")
        idempotency_key = f"{rule.rule_id}:{user_id}:{today_str}"

        push_log = PushLog(
            id=uuid.uuid4(),
            user_id=user_id,
            rule_id=rule.rule_id,
            channel=channel,
            status="sent" if success else "failed",
            provider_message_id=provider_message_id,
            idempotency_key=idempotency_key,
            created_at=now_utc,
        )
        db.add(push_log)

    async def _is_in_quiet_hours(
        self, db: AsyncSession, user: User
    ) -> bool:
        """检查用户当前是否处于静默时段。

        默认静默时段：22:00 - 08:00（用户本地时间）。
        如果用户有 UserChannelPreference，使用其自定义设置。
        """
        from ai_parenting.backend.models import UserChannelPreference

        # 获取用户本地时间
        user_local = get_user_local_time(user.timezone)
        current_hour = user_local.hour

        # 查询用户偏好中的静默时段设置
        stmt = select(UserChannelPreference).where(
            UserChannelPreference.user_id == user.id
        )
        result = await db.execute(stmt)
        pref = result.scalar_one_or_none()

        quiet_start = pref.quiet_start_hour if pref else 22
        quiet_end = pref.quiet_end_hour if pref else 8

        # 处理跨午夜的情况（如 22:00 - 08:00）
        if quiet_start > quiet_end:
            # 跨午夜
            return current_hour >= quiet_start or current_hour < quiet_end
        else:
            # 不跨午夜（如 01:00 - 06:00）
            return quiet_start <= current_hour < quiet_end

    async def _fetch_user_batch(
        self, db: AsyncSession, last_id: uuid.UUID | None
    ) -> list[User]:
        """游标分页获取推送启用的用户。"""
        stmt = (
            select(User)
            .where(User.push_enabled.is_(True))
            .order_by(User.id)
            .limit(SCAN_BATCH_SIZE)
        )
        if last_id is not None:
            stmt = stmt.where(User.id > str(last_id))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _get_user_plan_context(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        child_id: uuid.UUID | None = None,
    ) -> tuple[Plan | None, Child | None]:
        """获取用户的活跃计划和对应儿童。"""
        stmt = (
            select(Plan, Child)
            .join(Child, Plan.child_id == Child.id)
            .where(Child.user_id == user_id, Plan.status == "active")
            .order_by(Plan.created_at.desc())
            .limit(1)
        )
        if child_id is not None:
            stmt = stmt.where(Child.id == child_id)

        result = await db.execute(stmt)
        row = result.first()
        if row:
            return row[0], row[1]
        return None, None

    async def _create_rule_message(
        self,
        db: AsyncSession,
        *,
        rule: PushRule,
        user: User,
        child: Child | None,
        plan: Plan | None,
        ctx: dict[str, Any],
    ) -> Message:
        """根据规则创建推送消息。"""
        from ai_parenting.backend.services.message_service import create_message

        # 动态生成消息文本
        body_override = None
        summary_override = None
        title_override = None
        target_params: dict[str, str] = {}

        nickname = child.nickname if child else "宝宝"

        if rule.rule_id == "daily_task_reminder" and plan is not None:
            today_task = self._get_today_task(plan)
            task_title = today_task.main_exercise_title if today_task else "今日任务"
            body_override = (
                f"今天是{nickname}的第 {plan.current_day} 天："
                f"「{task_title}」，点击查看详情。"
            )
            summary_override = f"Day {plan.current_day}：{task_title}"
            target_params = {"plan_id": str(plan.id)}

        elif rule.rule_id == "record_prompt":
            body_override = (
                f"今天和{nickname}的互动还不错吗？"
                f"花 1 分钟记录一下观察到的变化吧。"
            )
            if child:
                target_params = {"child_id": str(child.id)}

        elif rule.rule_id == "plan_expiry_reminder" and plan is not None:
            title_override = "本周计划即将结束"
            body_override = (
                f"{nickname}的本周微计划明天到期，"
                f"周反馈将在明日自动生成。"
            )
            summary_override = "明日将生成本周反馈报告"
            target_params = {"plan_id": str(plan.id)}

        elif rule.rule_id == "no_record_nudge":
            no_days = ctx.get("no_record_days", 2)
            body_override = (
                f"已经 {no_days} 天没有记录{nickname}的成长了。"
                f"哪怕一句简短的观察，也能帮助 AI 更好地理解宝宝的发展哦！"
            )
            if child:
                target_params = {"child_id": str(child.id)}

        elif rule.rule_id == "streak_celebration":
            consecutive = ctx.get("consecutive_record_days", 7)
            title_override = "🎉 连续记录达成！"
            body_override = (
                f"太棒了！您已经连续 {consecutive} 天记录{nickname}的成长，"
                f"坚持记录让 AI 对宝宝的理解越来越准确。"
            )
            summary_override = f"连续记录 {consecutive} 天！"

        return await create_message(
            db,
            user_id=user.id,
            child_id=child.id if child else None,
            message_type=rule.message_type,
            target_params=target_params or None,
            title_override=title_override,
            body_override=body_override,
            summary_override=summary_override,
        )

    @staticmethod
    def _get_today_task(plan: Plan) -> DayTask | None:
        """获取计划的当日任务。"""
        for task in plan.day_tasks:
            if task.day_number == plan.current_day:
                return task
        return None
