import { useState, useEffect } from 'react'
import { Card, Loading, Row, Col, Tag } from 'tdesign-react'
import {
  UserCircleIcon,
  UserAddIcon,
  ChartBubbleIcon,
  ChatIcon,
  NotificationIcon,
  RootListIcon,
  ServerIcon,
  LinkIcon,
} from 'tdesign-icons-react'
import { fetchEnhancedStats, type EnhancedStats } from '../api/adminApi'

interface StatCardProps {
  title: string
  value: number
  subValue?: string
  icon: React.ReactNode
  gradient: string
}

function StatCard({ title, value, subValue, icon, gradient }: StatCardProps) {
  return (
    <Card className="hover:shadow-lg transition-shadow" style={{ borderRadius: 12 }}>
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white ${gradient}`}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm text-gray-500">{title}</div>
          <div className="text-2xl font-bold text-gray-800">{value.toLocaleString()}</div>
          {subValue && <div className="text-xs text-gray-400 mt-0.5">{subValue}</div>}
        </div>
      </div>
    </Card>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState<EnhancedStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchEnhancedStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loading size="large" text="加载中..." />
      </div>
    )
  }

  if (!stats) {
    return <div className="text-center text-gray-500 py-20">加载失败，请刷新重试</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">系统概览</h1>
          <p className="text-gray-500 mt-1">实时监控系统运行状态</p>
        </div>
        <Tag theme="success" variant="light" size="large">
          系统正常
        </Tag>
      </div>

      {/* 今日指标 */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">今日动态</h3>
        <Row gutter={[16, 16]}>
          <Col span={3}>
            <StatCard
              title="新增用户"
              value={stats.today_new_users}
              icon={<UserCircleIcon size="24px" />}
              gradient="bg-gradient-to-br from-blue-500 to-blue-600"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="新增记录"
              value={stats.today_new_records}
              icon={<RootListIcon size="24px" />}
              gradient="bg-gradient-to-br from-green-500 to-green-600"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="AI 会话"
              value={stats.today_ai_sessions}
              icon={<ChatIcon size="24px" />}
              gradient="bg-gradient-to-br from-purple-500 to-purple-600"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="推送次数"
              value={stats.today_push_count}
              icon={<NotificationIcon size="24px" />}
              gradient="bg-gradient-to-br from-orange-500 to-orange-600"
            />
          </Col>
        </Row>
      </div>

      {/* 总量统计 */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">总量统计</h3>
        <Row gutter={[16, 16]}>
          <Col span={3}>
            <StatCard
              title="总用户数"
              value={stats.total_users}
              icon={<UserCircleIcon size="24px" />}
              gradient="bg-gradient-to-br from-blue-400 to-blue-500"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="儿童档案"
              value={stats.total_children}
              icon={<UserAddIcon size="24px" />}
              gradient="bg-gradient-to-br from-pink-400 to-pink-500"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="训练计划"
              value={stats.total_plans}
              subValue={`${stats.active_plans} 个活跃中`}
              icon={<ChartBubbleIcon size="24px" />}
              gradient="bg-gradient-to-br from-teal-400 to-teal-500"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="观察记录"
              value={stats.total_records}
              icon={<RootListIcon size="24px" />}
              gradient="bg-gradient-to-br from-green-400 to-green-500"
            />
          </Col>
        </Row>
        <Row gutter={[16, 16]} className="mt-4">
          <Col span={3}>
            <StatCard
              title="消息总量"
              value={stats.total_messages}
              icon={<NotificationIcon size="24px" />}
              gradient="bg-gradient-to-br from-yellow-400 to-yellow-500"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="AI 会话总量"
              value={stats.total_ai_sessions}
              icon={<ChatIcon size="24px" />}
              gradient="bg-gradient-to-br from-purple-400 to-purple-500"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="设备数"
              value={stats.total_devices}
              subValue={`${stats.active_devices} 个活跃`}
              icon={<ServerIcon size="24px" />}
              gradient="bg-gradient-to-br from-gray-400 to-gray-500"
            />
          </Col>
          <Col span={3}>
            <StatCard
              title="渠道绑定"
              value={stats.total_channel_bindings}
              subValue={`${stats.active_bindings} 个活跃`}
              icon={<LinkIcon size="24px" />}
              gradient="bg-gradient-to-br from-indigo-400 to-indigo-500"
            />
          </Col>
        </Row>
      </div>

      {/* 补充统计 */}
      <Row gutter={[16, 16]}>
        <Col span={4}>
          <Card title="周反馈" className="hover:shadow-lg transition-shadow" style={{ borderRadius: 12 }}>
            <div className="text-3xl font-bold text-gray-800">{stats.total_weekly_feedbacks}</div>
            <div className="text-sm text-gray-500 mt-1">累计周反馈报告</div>
          </Card>
        </Col>
        <Col span={4}>
          <Card title="推送日志" className="hover:shadow-lg transition-shadow" style={{ borderRadius: 12 }}>
            <div className="text-3xl font-bold text-gray-800">{stats.total_push_logs}</div>
            <div className="text-sm text-gray-500 mt-1">累计推送记录</div>
          </Card>
        </Col>
        <Col span={4}>
          <Card title="渠道绑定" className="hover:shadow-lg transition-shadow" style={{ borderRadius: 12 }}>
            <div className="text-3xl font-bold text-gray-800">{stats.total_channel_bindings}</div>
            <div className="text-sm text-gray-500 mt-1">累计渠道绑定</div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
