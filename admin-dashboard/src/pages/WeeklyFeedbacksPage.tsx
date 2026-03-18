import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tag, Select, Button, MessagePlugin } from 'tdesign-react'
import { RefreshIcon, PlayCircleIcon } from 'tdesign-icons-react'
import { fetchWeeklyFeedbacks, retryWeeklyFeedback, type AdminWeeklyFeedback } from '../api/adminApi'

const statusMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' | 'default' }> = {
  pending: { label: '待生成', theme: 'primary' },
  generating: { label: '生成中', theme: 'warning' },
  ready: { label: '已就绪', theme: 'success' },
  viewed: { label: '已查看', theme: 'success' },
  decided: { label: '已决策', theme: 'success' },
  failed: { label: '失败', theme: 'danger' },
}

export default function WeeklyFeedbacksPage() {
  const [feedbacks, setFeedbacks] = useState<AdminWeeklyFeedback[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const loadFeedbacks = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchWeeklyFeedbacks({
        limit: pageSize,
        offset: (page - 1) * pageSize,
        status: statusFilter || undefined,
      })
      setFeedbacks(res.feedbacks)
      setTotal(res.total)
    } catch (err) {
      console.error('Failed to load feedbacks:', err)
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => {
    loadFeedbacks()
  }, [loadFeedbacks])

  const handleRetry = async (feedback: AdminWeeklyFeedback) => {
    try {
      await retryWeeklyFeedback(feedback.id)
      setFeedbacks(prev => prev.map(f =>
        f.id === feedback.id ? { ...f, status: 'pending', error_info: null } : f
      ))
      MessagePlugin.success('已重新加入生成队列')
    } catch (err) {
      MessagePlugin.error(err instanceof Error ? err.message : '重试失败')
    }
  }

  const columns = [
    {
      title: '儿童',
      colKey: 'child_nickname',
      width: 100,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => row.child_nickname || '-',
    },
    {
      title: '状态',
      colKey: 'status',
      width: 90,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => {
        const s = statusMap[row.status] || { label: row.status, theme: 'default' as const }
        return <Tag variant="light" theme={s.theme} size="small">{s.label}</Tag>
      },
    },
    {
      title: '决策',
      colKey: 'selected_decision',
      width: 100,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => row.selected_decision || '-',
    },
    {
      title: '记录数',
      colKey: 'record_count_this_week',
      width: 80,
      align: 'center' as const,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => row.record_count_this_week ?? '-',
    },
    {
      title: '完成率',
      colKey: 'completion_rate_this_week',
      width: 90,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => {
        if (row.completion_rate_this_week === null) return '-'
        return `${Math.round(row.completion_rate_this_week * 100)}%`
      },
    },
    {
      title: '摘要',
      colKey: 'summary_text',
      width: 200,
      ellipsis: true,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => (
        <span className="text-gray-600">{row.summary_text?.slice(0, 60) || '-'}</span>
      ),
    },
    {
      title: '错误信息',
      colKey: 'error_info',
      width: 160,
      ellipsis: true,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => (
        row.error_info ? <span className="text-red-500 text-xs">{row.error_info}</span> : '-'
      ),
    },
    {
      title: '创建时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      colKey: 'action',
      width: 80,
      cell: ({ row }: { row: AdminWeeklyFeedback }) => (
        row.status === 'failed' ? (
          <Button
            variant="text"
            theme="primary"
            size="small"
            icon={<PlayCircleIcon />}
            onClick={() => handleRetry(row)}
          >
            重试
          </Button>
        ) : null
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">周反馈管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 个反馈</Tag>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Select
            value={statusFilter}
            onChange={(val) => { setStatusFilter(val as string); setPage(1) }}
            placeholder="按状态筛选"
            clearable
            style={{ width: 160 }}
            options={[
              { label: '全部', value: '' },
              { label: '待生成', value: 'pending' },
              { label: '已就绪', value: 'ready' },
              { label: '失败', value: 'failed' },
              { label: '已决策', value: 'decided' },
            ]}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadFeedbacks}>刷新</Button>
        </div>

        <Table
          data={feedbacks}
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
