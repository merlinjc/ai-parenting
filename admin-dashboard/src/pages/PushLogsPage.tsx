import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tag, Select, Button, Row, Col, Loading } from 'tdesign-react'
import { RefreshIcon } from 'tdesign-icons-react'
import { fetchPushLogs, fetchPushLogStats, type AdminPushLog, type PushLogStats } from '../api/adminApi'

const statusMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' | 'default' }> = {
  sent: { label: '已发送', theme: 'primary' },
  delivered: { label: '已送达', theme: 'success' },
  failed: { label: '失败', theme: 'danger' },
  skipped: { label: '跳过', theme: 'default' },
}

export default function PushLogsPage() {
  const [logs, setLogs] = useState<AdminPushLog[]>([])
  const [stats, setStats] = useState<PushLogStats | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [channelFilter, setChannelFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [logsRes, statsRes] = await Promise.all([
        fetchPushLogs({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          channel: channelFilter || undefined,
          status: statusFilter || undefined,
        }),
        fetchPushLogStats(),
      ])
      setLogs(logsRes.logs)
      setTotal(logsRes.total)
      setStats(statsRes)
    } catch (err) {
      console.error('Failed to load push logs:', err)
    } finally {
      setLoading(false)
    }
  }, [page, channelFilter, statusFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const columns = [
    {
      title: '渠道',
      colKey: 'channel',
      width: 100,
      cell: ({ row }: { row: AdminPushLog }) => (
        <Tag variant="outline" size="small">{row.channel || '-'}</Tag>
      ),
    },
    {
      title: '状态',
      colKey: 'status',
      width: 90,
      cell: ({ row }: { row: AdminPushLog }) => {
        const s = statusMap[row.status] || { label: row.status, theme: 'default' as const }
        return <Tag variant="light" theme={s.theme} size="small">{s.label}</Tag>
      },
    },
    {
      title: '用户邮箱',
      colKey: 'user_email',
      width: 160,
      cell: ({ row }: { row: AdminPushLog }) => row.user_email || '-',
    },
    {
      title: '规则',
      colKey: 'rule_id',
      width: 140,
      cell: ({ row }: { row: AdminPushLog }) => row.rule_id || '-',
    },
    {
      title: '延迟',
      colKey: 'latency_ms',
      width: 90,
      cell: ({ row }: { row: AdminPushLog }) => {
        if (!row.latency_ms) return '-'
        const color = row.latency_ms > 500 ? 'text-red-500' : row.latency_ms > 200 ? 'text-yellow-500' : 'text-green-500'
        return <span className={color}>{row.latency_ms}ms</span>
      },
    },
    {
      title: '降级',
      colKey: 'fallback_used',
      width: 80,
      cell: ({ row }: { row: AdminPushLog }) => (
        row.fallback_used ? (
          <Tag variant="light" theme="warning" size="small">{row.fallback_channel}</Tag>
        ) : '-'
      ),
    },
    {
      title: '错误信息',
      colKey: 'error',
      width: 180,
      ellipsis: true,
      cell: ({ row }: { row: AdminPushLog }) => (
        row.error ? <span className="text-red-500 text-xs">{row.error}</span> : '-'
      ),
    },
    {
      title: '时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminPushLog }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">推送日志</h1>
        <Tag theme="primary" variant="light" size="large">{total} 条日志</Tag>
      </div>

      {stats ? (
        <Row gutter={[16, 16]}>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">送达率</div>
              <div className="text-2xl font-bold text-green-600">{(stats.delivery_rate * 100).toFixed(1)}%</div>
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
              <div className="text-sm text-gray-500">降级率</div>
              <div className="text-2xl font-bold text-yellow-600">{(stats.fallback_rate * 100).toFixed(1)}%</div>
            </Card>
          </Col>
        </Row>
      ) : loading ? <Loading /> : null}

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Select
            value={channelFilter}
            onChange={(val) => { setChannelFilter(val as string); setPage(1) }}
            placeholder="按渠道筛选"
            clearable
            style={{ width: 140 }}
            options={[
              { label: '全部', value: '' },
              { label: 'APNs', value: 'apns' },
              { label: '微信', value: 'wechat' },
              { label: 'WhatsApp', value: 'whatsapp' },
              { label: 'Telegram', value: 'telegram' },
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
              { label: '已发送', value: 'sent' },
              { label: '已送达', value: 'delivered' },
              { label: '失败', value: 'failed' },
            ]}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadData}>刷新</Button>
        </div>

        <Table
          data={logs}
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
