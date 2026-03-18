import { useState, useEffect } from 'react'
import { Card, Statistic, Tag, Badge, Loading } from 'tdesign-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts'
import { fetchChannelStats } from '../api/channelMonitorApi'
import type { ChannelStatus, AlertLog, BindingStats } from '../data/mockData'

const CHANNEL_COLORS: Record<string, string> = {
  APNs: '#0052D9',
  微信: '#2BA471',
  WhatsApp: '#E37318',
  Telegram: '#618DFF',
}

const STATUS_MAP = {
  healthy: { text: '正常', color: 'success' as const },
  degraded: { text: '降级', color: 'warning' as const },
  unavailable: { text: '不可用', color: 'danger' as const },
}

const SEVERITY_MAP = {
  critical: { text: '严重', color: 'danger' as const },
  warning: { text: '警告', color: 'warning' as const },
  info: { text: '信息', color: 'primary' as const },
}

export default function ChannelMonitorPage() {
  const [loading, setLoading] = useState(true)
  const [channelStatuses, setChannelStatuses] = useState<ChannelStatus[]>([])
  const [alertLogs, setAlertLogs] = useState<AlertLog[]>([])
  const [bindingStats, setBindingStats] = useState<BindingStats[]>([])
  const [latencyData, setLatencyData] = useState<Record<string, unknown>[]>([])
  const [bindingData, setBindingData] = useState<Record<string, unknown>[]>([])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      const data = await fetchChannelStats()
      if (!cancelled) {
        setChannelStatuses(data.channels)
        setAlertLogs(data.alerts)
        setBindingStats(data.bindingStats)
        setLatencyData(data.latencyTrend)
        setBindingData(data.bindingTrend)
        setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading text="加载渠道监控数据..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">渠道监控看板</h1>
        <p className="text-sm text-gray-500 mt-1">实时监控各消息渠道的健康状态和推送效能</p>
      </div>

      {/* 渠道状态总览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {channelStatuses.map((ch) => {
          const statusInfo = STATUS_MAP[ch.status]
          return (
            <Card key={ch.channel} bordered className="!rounded-xl !shadow-sm hover:!shadow-md transition-all hover:-translate-y-0.5">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-800">{ch.displayName}</span>
                  <Tag theme={statusInfo.color} variant="light" size="small">{statusInfo.text}</Tag>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs text-gray-400">延迟</div>
                    <div className="text-lg font-semibold" style={{ color: ch.latencyMs > 500 ? '#D54941' : ch.latencyMs > 200 ? '#E37318' : '#2BA471' }}>
                      {ch.latencyMs}<span className="text-xs text-gray-400 ml-0.5">ms</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">今日消息</div>
                    <div className="text-lg font-semibold text-gray-800">
                      {ch.todayMessages.toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-gray-50">
                  <span className="text-xs text-gray-400">失败率</span>
                  <span className={`text-sm font-medium ${ch.failureRate > 0.01 ? 'text-danger' : 'text-success'}`}>
                    {(ch.failureRate * 100).toFixed(1)}%
                  </span>
                </div>

                {/* 状态指示灯动画 */}
                <div className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${
                    ch.status === 'healthy' ? 'bg-success animate-pulse' :
                    ch.status === 'degraded' ? 'bg-warning animate-pulse' :
                    'bg-danger'
                  }`} />
                  <span className="text-xs text-gray-400">
                    最后检查: {new Date(ch.lastCheckAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* 延迟趋势图 */}
      <Card bordered className="!rounded-xl !shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">近 24 小时渠道延迟趋势</h3>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={latencyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="hour" tick={{ fontSize: 12, fill: '#8B8B8B' }} />
            <YAxis tick={{ fontSize: 12, fill: '#8B8B8B' }} unit="ms" />
            <Tooltip
              contentStyle={{ borderRadius: 8, border: '1px solid #eee', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
              formatter={(value: unknown) => [`${Number(value).toFixed(0)}ms`]}
            />
            <Legend />
            <Line type="monotone" dataKey="APNs" stroke={CHANNEL_COLORS['APNs']} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="微信" stroke={CHANNEL_COLORS['微信']} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="WhatsApp" stroke={CHANNEL_COLORS['WhatsApp']} strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="Telegram" stroke={CHANNEL_COLORS['Telegram']} strokeWidth={2} dot={false} strokeDasharray="5 5" />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* 绑定统计 + 告警日志 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 绑定分布饼图 */}
        <Card bordered className="!rounded-xl !shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">用户渠道绑定分布</h3>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width="50%" height={240}>
              <PieChart>
                <Pie
                  data={bindingStats}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  dataKey="count"
                  nameKey="channel"
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  label={(props: any) => `${props.channel} ${props.percentage}%`}
                  labelLine={{ strokeWidth: 1 }}
                >
                  {bindingStats.map((entry) => (
                    <Cell key={entry.channel} fill={CHANNEL_COLORS[entry.channel] || '#8B8B8B'} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: unknown) => [Number(value).toLocaleString(), '绑定数']} />
              </PieChart>
            </ResponsiveContainer>

            <div className="space-y-3 flex-1">
              {bindingStats.map((stat) => (
                <div key={stat.channel} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CHANNEL_COLORS[stat.channel] || '#8B8B8B' }} />
                    <span className="text-sm text-gray-600">{stat.channel}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-semibold text-gray-800">{stat.count.toLocaleString()}</span>
                    <span className="text-xs text-gray-400 ml-1">({stat.percentage}%)</span>
                  </div>
                </div>
              ))}
              <div className="pt-2 border-t border-gray-100">
                <Statistic title="总绑定数" value={bindingStats.reduce((s, b) => s + b.count, 0)} />
              </div>
            </div>
          </div>
        </Card>

        {/* 近 7 天新增绑定趋势 */}
        <Card bordered className="!rounded-xl !shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">近 7 天新增绑定</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={bindingData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#8B8B8B' }} />
              <YAxis tick={{ fontSize: 12, fill: '#8B8B8B' }} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #eee', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' }}
              />
              <Bar dataKey="新增" fill="#0052D9" radius={[4, 4, 0, 0]} barSize={32} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 告警日志 */}
      <Card bordered className="!rounded-xl !shadow-sm">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">告警日志</h3>
        <div className="space-y-3">
          {alertLogs.map((alert) => {
            const severity = SEVERITY_MAP[alert.severity]
            return (
              <div
                key={alert.id}
                className={`flex items-start gap-3 p-3 rounded-lg border-l-4 ${
                  alert.severity === 'critical' ? 'border-l-danger bg-red-50/50' :
                  alert.severity === 'warning' ? 'border-l-warning bg-amber-50/50' :
                  'border-l-primary bg-blue-50/30'
                }`}
              >
                <Badge count={<Tag theme={severity.color} variant="light" size="small">{severity.text}</Tag>} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Tag variant="outline" size="small">{alert.channel.toUpperCase()}</Tag>
                  </div>
                  <p className="text-sm text-gray-700">{alert.message}</p>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap">
                  {new Date(alert.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}
