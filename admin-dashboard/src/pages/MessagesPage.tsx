import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tag, Select, Button, Row, Col, Loading } from 'tdesign-react'
import { RefreshIcon } from 'tdesign-icons-react'
import { fetchMessages, fetchMessageStats, type AdminMessage, type MessageStats } from '../api/adminApi'

const readStatusMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' | 'default' }> = {
  read: { label: '已读', theme: 'success' },
  unread: { label: '未读', theme: 'default' },
}

export default function MessagesPage() {
  const [messages, setMessages] = useState<AdminMessage[]>([])
  const [stats, setStats] = useState<MessageStats | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [readFilter, setReadFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [messagesRes, statsRes] = await Promise.all([
        fetchMessages({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          read_status: readFilter || undefined,
          type: typeFilter || undefined,
        }),
        fetchMessageStats(),
      ])
      setMessages(messagesRes.messages)
      setTotal(messagesRes.total)
      setStats(statsRes)
    } catch (err) {
      console.error('Failed to load messages:', err)
    } finally {
      setLoading(false)
    }
  }, [page, readFilter, typeFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const columns = [
    {
      title: '标题',
      colKey: 'title',
      width: 200,
      ellipsis: true,
      cell: ({ row }: { row: AdminMessage }) => <span className="font-medium">{row.title}</span>,
    },
    {
      title: '类型',
      colKey: 'type',
      width: 100,
      cell: ({ row }: { row: AdminMessage }) => <Tag variant="outline" size="small">{row.type}</Tag>,
    },
    {
      title: '用户邮箱',
      colKey: 'user_email',
      width: 160,
      cell: ({ row }: { row: AdminMessage }) => row.user_email || '-',
    },
    {
      title: '内容',
      colKey: 'body',
      width: 200,
      ellipsis: true,
      cell: ({ row }: { row: AdminMessage }) => (
        <span className="text-gray-600">{row.body?.slice(0, 60) || '-'}</span>
      ),
    },
    {
      title: '阅读状态',
      colKey: 'read_status',
      width: 90,
      cell: ({ row }: { row: AdminMessage }) => {
        const s = readStatusMap[row.read_status] || { label: row.read_status, theme: 'default' as const }
        return <Tag variant="light" theme={s.theme} size="small">{s.label}</Tag>
      },
    },
    {
      title: '推送状态',
      colKey: 'push_status',
      width: 90,
      cell: ({ row }: { row: AdminMessage }) => row.push_status || '-',
    },
    {
      title: '创建时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminMessage }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">消息管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 条消息</Tag>
      </div>

      {stats ? (
        <Row gutter={[16, 16]}>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">阅读率</div>
              <div className="text-2xl font-bold text-green-600">{(stats.read_rate * 100).toFixed(1)}%</div>
              <div className="text-xs text-gray-400 mt-1">{stats.read_count} / {stats.total_messages}</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">推送送达率</div>
              <div className="text-2xl font-bold text-blue-600">{(stats.push_delivery_rate * 100).toFixed(1)}%</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">未读消息</div>
              <div className="text-2xl font-bold text-yellow-600">{stats.unread_count}</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">已推送</div>
              <div className="text-2xl font-bold text-gray-600">{stats.push_sent_count}</div>
            </Card>
          </Col>
        </Row>
      ) : loading ? <Loading /> : null}

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Select
            value={readFilter}
            onChange={(val) => { setReadFilter(val as string); setPage(1) }}
            placeholder="阅读状态"
            clearable
            style={{ width: 130 }}
            options={[
              { label: '全部', value: '' },
              { label: '已读', value: 'read' },
              { label: '未读', value: 'unread' },
            ]}
          />
          <Select
            value={typeFilter}
            onChange={(val) => { setTypeFilter(val as string); setPage(1) }}
            placeholder="按类型筛选"
            clearable
            style={{ width: 140 }}
            options={[
              { label: '全部', value: '' },
              { label: '任务提醒', value: 'task_reminder' },
              { label: '反馈通知', value: 'feedback_ready' },
              { label: '风险提醒', value: 'risk_alert' },
              { label: '系统通知', value: 'system' },
            ]}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadData}>刷新</Button>
        </div>

        <Table
          data={messages}
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
