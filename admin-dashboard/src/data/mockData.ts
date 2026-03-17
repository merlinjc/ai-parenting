// Mock data for push rules and channel monitoring

export interface PushRule {
  id: string
  name: string
  description: string
  triggerType: 'cron' | 'event' | 'milestone'
  cronExpression?: string
  eventType?: string
  isActive: boolean
  cooldownMinutes: number
  channelPriority: string[]
  conditionSummary: string
  lastTriggeredAt: string | null
  totalSent: number
  deliveryRate: number
}

export interface ChannelStatus {
  channel: string
  displayName: string
  status: 'healthy' | 'degraded' | 'unavailable'
  latencyMs: number
  todayMessages: number
  failureRate: number
  lastCheckAt: string
}

export interface AlertLog {
  id: string
  channel: string
  severity: 'critical' | 'warning' | 'info'
  message: string
  timestamp: string
}

export interface BindingStats {
  channel: string
  count: number
  percentage: number
}

export const mockPushRules: PushRule[] = [
  {
    id: 'rule_morning_task',
    name: '早安任务提醒',
    description: '每日 08:00 推送今日训练任务（按用户时区）',
    triggerType: 'cron',
    cronExpression: '0 8 * * *',
    isActive: true,
    cooldownMinutes: 1440,
    channelPriority: ['apns', 'wechat'],
    conditionSummary: '有活跃计划且今日未执行',
    lastTriggeredAt: '2026-03-17T08:00:00Z',
    totalSent: 12847,
    deliveryRate: 0.967,
  },
  {
    id: 'rule_evening_record',
    name: '晚间记录提醒',
    description: '每日 20:30 提醒记录今日观察',
    triggerType: 'cron',
    cronExpression: '30 20 * * *',
    isActive: true,
    cooldownMinutes: 1440,
    channelPriority: ['wechat', 'apns'],
    conditionSummary: '今日已执行但未记录',
    lastTriggeredAt: '2026-03-16T20:30:00Z',
    totalSent: 9632,
    deliveryRate: 0.941,
  },
  {
    id: 'rule_plan_advance',
    name: '计划推进提醒',
    description: '每日 00:01 自动推进计划到下一天',
    triggerType: 'cron',
    cronExpression: '1 0 * * *',
    isActive: true,
    cooldownMinutes: 1440,
    channelPriority: ['apns'],
    conditionSummary: '有活跃计划且当前天 < 7',
    lastTriggeredAt: '2026-03-17T00:01:00Z',
    totalSent: 15210,
    deliveryRate: 0.993,
  },
  {
    id: 'rule_weekly_feedback',
    name: '周反馈通知',
    description: '周反馈生成后立即推送',
    triggerType: 'event',
    eventType: 'weekly_feedback_created',
    isActive: true,
    cooldownMinutes: 10080,
    channelPriority: ['wechat', 'apns'],
    conditionSummary: '周反馈状态变为 ready',
    lastTriggeredAt: '2026-03-16T10:00:00Z',
    totalSent: 2156,
    deliveryRate: 0.988,
  },
  {
    id: 'rule_risk_alert',
    name: '风险提醒',
    description: '识别到发育风险后推送专业建议',
    triggerType: 'event',
    eventType: 'risk_detected',
    isActive: true,
    cooldownMinutes: 4320,
    channelPriority: ['apns', 'wechat'],
    conditionSummary: '风险等级 >= watch',
    lastTriggeredAt: '2026-03-15T14:22:00Z',
    totalSent: 387,
    deliveryRate: 0.995,
  },
  {
    id: 'rule_milestone_celebration',
    name: '里程碑庆祝',
    description: '儿童达成发育里程碑时推送庆祝消息',
    triggerType: 'milestone',
    isActive: true,
    cooldownMinutes: 0,
    channelPriority: ['apns', 'wechat'],
    conditionSummary: '完成率达到 100% 或连续 7 天',
    lastTriggeredAt: '2026-03-14T16:45:00Z',
    totalSent: 1243,
    deliveryRate: 0.979,
  },
  {
    id: 'rule_streak_encourage',
    name: '连续打卡鼓励',
    description: '连续 3/7/14/30 天打卡时推送鼓励消息',
    triggerType: 'milestone',
    isActive: false,
    cooldownMinutes: 0,
    channelPriority: ['apns'],
    conditionSummary: '连续打卡天数 ∈ {3, 7, 14, 30}',
    lastTriggeredAt: null,
    totalSent: 0,
    deliveryRate: 0,
  },
]

export const mockChannelStatuses: ChannelStatus[] = [
  {
    channel: 'apns',
    displayName: 'APNs (iOS推送)',
    status: 'healthy',
    latencyMs: 45,
    todayMessages: 8743,
    failureRate: 0.003,
    lastCheckAt: '2026-03-17T14:30:00Z',
  },
  {
    channel: 'wechat',
    displayName: '微信服务号',
    status: 'healthy',
    latencyMs: 120,
    todayMessages: 5621,
    failureRate: 0.008,
    lastCheckAt: '2026-03-17T14:30:00Z',
  },
  {
    channel: 'whatsapp',
    displayName: 'WhatsApp',
    status: 'degraded',
    latencyMs: 890,
    todayMessages: 234,
    failureRate: 0.032,
    lastCheckAt: '2026-03-17T14:30:00Z',
  },
  {
    channel: 'telegram',
    displayName: 'Telegram',
    status: 'unavailable',
    latencyMs: 0,
    todayMessages: 0,
    failureRate: 1.0,
    lastCheckAt: '2026-03-17T14:25:00Z',
  },
]

export const mockAlertLogs: AlertLog[] = [
  { id: '1', channel: 'telegram', severity: 'critical', message: 'OpenClaw WebSocket 连接断开，Telegram 渠道不可用', timestamp: '2026-03-17T14:25:00Z' },
  { id: '2', channel: 'whatsapp', severity: 'warning', message: 'WhatsApp 延迟升高至 890ms（阈值 500ms），触发降级策略', timestamp: '2026-03-17T14:20:00Z' },
  { id: '3', channel: 'wechat', severity: 'info', message: '微信模板消息今日配额剩余 38%', timestamp: '2026-03-17T12:00:00Z' },
  { id: '4', channel: 'apns', severity: 'info', message: 'APNs 证书将在 25 天后过期，请及时更新', timestamp: '2026-03-17T09:00:00Z' },
  { id: '5', channel: 'telegram', severity: 'critical', message: 'Circuit Breaker 触发，Telegram 消息自动降级至 APNs', timestamp: '2026-03-17T14:26:00Z' },
]

export const mockBindingStats: BindingStats[] = [
  { channel: 'APNs', count: 12450, percentage: 48.5 },
  { channel: '微信', count: 9830, percentage: 38.3 },
  { channel: 'WhatsApp', count: 2340, percentage: 9.1 },
  { channel: 'Telegram', count: 1050, percentage: 4.1 },
]

// 24h latency trend data for charts
export const latencyTrendData = Array.from({ length: 24 }, (_, i) => ({
  hour: `${String(i).padStart(2, '0')}:00`,
  APNs: 30 + Math.random() * 40,
  微信: 80 + Math.random() * 80,
  WhatsApp: 200 + Math.random() * 800,
  Telegram: i >= 14 ? 0 : 150 + Math.random() * 200,
}))

// 7-day binding trend data
export const bindingTrendData = [
  { date: '03-11', 新增: 156 },
  { date: '03-12', 新增: 189 },
  { date: '03-13', 新增: 234 },
  { date: '03-14', 新增: 178 },
  { date: '03-15', 新增: 267 },
  { date: '03-16', 新增: 312 },
  { date: '03-17', 新增: 145 },
]
