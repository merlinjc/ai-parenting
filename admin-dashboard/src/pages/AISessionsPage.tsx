import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tag, Select, Button, Row, Col, Loading } from 'tdesign-react'
import { RefreshIcon } from 'tdesign-icons-react'
import { fetchAISessions, fetchAISessionStats, type AdminAISession, type AISessionStats } from '../api/adminApi'

const statusMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' | 'default' }> = {
  completed: { label: '成功', theme: 'success' },
  failed: { label: '失败', theme: 'danger' },
  degraded: { label: '降级', theme: 'warning' },
  pending: { label: '进行中', theme: 'primary' },
}

export default function AISessionsPage() {
  const [sessions, setSessions] = useState<AdminAISession[]>([])
  const [stats, setStats] = useState<AISessionStats | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [sessionsRes, statsRes] = await Promise.all([
        fetchAISessions({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          session_type: typeFilter || undefined,
          status: statusFilter || undefined,
        }),
        fetchAISessionStats(),
      ])
      setSessions(sessionsRes.sessions)
      setTotal(sessionsRes.total)
      setStats(statsRes)
    } catch (err) {
      console.error('Failed to load AI sessions:', err)
    } finally {
      setLoading(false)
    }
  }, [page, typeFilter, statusFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const columns = [
    {
      title: '类型',
      colKey: 'session_type',
      width: 120,
      cell: ({ row }: { row: AdminAISession }) => (
        <Tag variant="outline" size="small">{row.session_type}</Tag>
      ),
    },
    {
      title: '状态',
      colKey: 'status',
      width: 80,
      cell: ({ row }: { row: AdminAISession }) => {
        const s = statusMap[row.status] || { label: row.status, theme: 'default' as const }
        return <Tag variant="light" theme={s.theme} size="small">{s.label}</Tag>
      },
    },
    {
      title: '儿童',
      colKey: 'child_nickname',
      width: 100,
      cell: ({ row }: { row: AdminAISession }) => row.child_nickname || '-',
    },
    {
      title: '输入内容',
      colKey: 'input_text',
      width: 200,
      ellipsis: true,
      cell: ({ row }: { row: AdminAISession }) => (
        <span className="text-gray-600">{row.input_text?.slice(0, 60) || '-'}</span>
      ),
    },
    {
      title: '模型',
      colKey: 'model_provider',
      width: 100,
      cell: ({ row }: { row: AdminAISession }) => row.model_provider || '-',
    },
    {
      title: '延迟',
      colKey: 'latency_ms',
      width: 90,
      cell: ({ row }: { row: AdminAISession }) => {
        if (!row.latency_ms) return '-'
        const color = row.latency_ms > 5000 ? 'text-red-500' : row.latency_ms > 2000 ? 'text-yellow-500' : 'text-green-500'
        return <span className={color}>{row.latency_ms}ms</span>
      },
    },
    {
      title: '重试',
      colKey: 'retry_count',
      width: 60,
      align: 'center' as const,
      cell: ({ row }: { row: AdminAISession }) => row.retry_count || 0,
    },
    {
      title: '错误信息',
      colKey: 'error_info',
      width: 180,
      ellipsis: true,
      cell: ({ row }: { row: AdminAISession }) => (
        row.error_info ? <span className="text-red-500 text-xs">{row.error_info}</span> : '-'
      ),
    },
    {
      title: '创建时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminAISession }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">AI 会话管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 个会话</Tag>
      </div>

      {/* 统计卡片 */}
      {stats ? (
        <Row gutter={[16, 16]}>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">成功率</div>
              <div className="text-2xl font-bold text-green-600">{(stats.success_rate * 100).toFixed(1)}%</div>
              <div className="text-xs text-gray-400 mt-1">{stats.success_count} / {stats.total_sessions}</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">平均延迟</div>
              <div className="text-2xl font-bold text-blue-600">{stats.avg_latency_ms.toFixed(0)}ms</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">失败数</div>
              <div className="text-2xl font-bold text-red-600">{stats.failed_count}</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">降级数</div>
              <div className="text-2xl font-bold text-yellow-600">{stats.degraded_count}</div>
            </Card>
          </Col>
        </Row>
      ) : loading ? <Loading /> : null}

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Select
            value={typeFilter}
            onChange={(val) => { setTypeFilter(val as string); setPage(1) }}
            placeholder="按类型筛选"
            clearable
            style={{ width: 160 }}
            options={[
              { label: '全部', value: '' },
              { label: '即时求助', value: 'instant_help' },
              { label: '计划生成', value: 'plan_generation' },
              { label: '周反馈', value: 'weekly_feedback' },
            ]}
          />
          <Select
            value={statusFilter}
            onChange={(val) => { setStatusFilter(val as string); setPage(1) }}
            placeholder="按状态筛选"
            clearable
            style={{ width: 140 }}
            options={[
              { label: '全部', value: '' },
              { label: '成功', value: 'completed' },
              { label: '失败', value: 'failed' },
              { label: '降级', value: 'degraded' },
            ]}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadData}>刷新</Button>
        </div>

        <Table
          data={sessions}
          columns={columns}
          rowKey="id"
          loading={loading}
          stripe
          hover
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: (pageInfo) => setPage(pageInfo.current),
            showJumper: true,
          }}
        />
      </Card>
    </div>
  )
}
