import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tag, Select, Button } from 'tdesign-react'
import { RefreshIcon } from 'tdesign-icons-react'
import { fetchPlans, type AdminPlan } from '../api/adminApi'

const statusMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' | 'default' }> = {
  active: { label: '进行中', theme: 'primary' },
  completed: { label: '已完成', theme: 'success' },
  superseded: { label: '已替代', theme: 'default' },
  paused: { label: '已暂停', theme: 'warning' },
}

export default function PlansPage() {
  const [plans, setPlans] = useState<AdminPlan[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const loadPlans = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchPlans({ limit: pageSize, offset: (page - 1) * pageSize, status: statusFilter || undefined })
      setPlans(res.plans)
      setTotal(res.total)
    } catch (err) {
      console.error('Failed to load plans:', err)
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => {
    loadPlans()
  }, [loadPlans])

  const columns = [
    {
      title: '计划名称',
      colKey: 'title',
      width: 200,
      cell: ({ row }: { row: AdminPlan }) => <span className="font-medium">{row.title}</span>,
    },
    {
      title: '儿童',
      colKey: 'child_nickname',
      width: 100,
      cell: ({ row }: { row: AdminPlan }) => row.child_nickname || '-',
    },
    {
      title: '状态',
      colKey: 'status',
      width: 90,
      cell: ({ row }: { row: AdminPlan }) => {
        const s = statusMap[row.status] || { label: row.status, theme: 'default' as const }
        return <Tag variant="light" theme={s.theme} size="small">{s.label}</Tag>
      },
    },
    {
      title: '主题',
      colKey: 'focus_theme',
      width: 100,
      cell: ({ row }: { row: AdminPlan }) => <Tag variant="outline" size="small">{row.focus_theme}</Tag>,
    },
    {
      title: '进度',
      colKey: 'current_day',
      width: 80,
      cell: ({ row }: { row: AdminPlan }) => `第${row.current_day}/7天`,
    },
    {
      title: '完成率',
      colKey: 'completion_rate',
      width: 90,
      cell: ({ row }: { row: AdminPlan }) => {
        const rate = Math.round(row.completion_rate * 100)
        const color = rate >= 80 ? 'text-green-600' : rate >= 50 ? 'text-yellow-600' : 'text-gray-600'
        return <span className={`font-medium ${color}`}>{rate}%</span>
      },
    },
    {
      title: '开始日期',
      colKey: 'start_date',
      width: 110,
    },
    {
      title: '结束日期',
      colKey: 'end_date',
      width: 110,
    },
    {
      title: '创建时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminPlan }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">计划管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 个计划</Tag>
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
              { label: '进行中', value: 'active' },
              { label: '已完成', value: 'completed' },
              { label: '已替代', value: 'superseded' },
            ]}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadPlans}>刷新</Button>
        </div>

        <Table
          data={plans}
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
