import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Input, Button, Tag } from 'tdesign-react'
import { SearchIcon, RefreshIcon } from 'tdesign-icons-react'
import { fetchChildren, type AdminChild } from '../api/adminApi'

const stageMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' }> = {
  early: { label: '早期', theme: 'primary' },
  mid: { label: '中期', theme: 'success' },
  late: { label: '后期', theme: 'warning' },
}

const riskMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' }> = {
  normal: { label: '正常', theme: 'success' },
  watch: { label: '关注', theme: 'warning' },
  alert: { label: '警示', theme: 'danger' },
}

export default function ChildrenPage() {
  const [children, setChildren] = useState<AdminChild[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const loadChildren = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchChildren({ limit: pageSize, offset: (page - 1) * pageSize, search: search || undefined })
      setChildren(res.children)
      setTotal(res.total)
    } catch (err) {
      console.error('Failed to load children:', err)
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    loadChildren()
  }, [loadChildren])

  const columns = [
    {
      title: '昵称',
      colKey: 'nickname',
      width: 120,
      cell: ({ row }: { row: AdminChild }) => (
        <span className="font-medium">{row.nickname}</span>
      ),
    },
    {
      title: '家长邮箱',
      colKey: 'user_email',
      width: 180,
      cell: ({ row }: { row: AdminChild }) => row.user_email || '-',
    },
    {
      title: '出生年月',
      colKey: 'birth_year_month',
      width: 100,
    },
    {
      title: '月龄',
      colKey: 'age_months',
      width: 70,
      align: 'center' as const,
      cell: ({ row }: { row: AdminChild }) => `${row.age_months}月`,
    },
    {
      title: '阶段',
      colKey: 'stage',
      width: 80,
      cell: ({ row }: { row: AdminChild }) => {
        const s = stageMap[row.stage] || { label: row.stage, theme: 'primary' as const }
        return <Tag variant="light" theme={s.theme} size="small">{s.label}</Tag>
      },
    },
    {
      title: '风险等级',
      colKey: 'risk_level',
      width: 90,
      cell: ({ row }: { row: AdminChild }) => {
        const r = riskMap[row.risk_level] || { label: row.risk_level, theme: 'primary' as const }
        return <Tag variant="light" theme={r.theme} size="small">{r.label}</Tag>
      },
    },
    {
      title: '关注领域',
      colKey: 'focus_themes',
      width: 160,
      cell: ({ row }: { row: AdminChild }) => (
        <div className="flex flex-wrap gap-1">
          {row.focus_themes?.map(t => (
            <Tag key={t} variant="outline" size="small">{t}</Tag>
          )) || '-'}
        </div>
      ),
    },
    {
      title: 'Onboarding',
      colKey: 'onboarding_completed',
      width: 100,
      cell: ({ row }: { row: AdminChild }) => (
        <Tag variant="light" theme={row.onboarding_completed ? 'success' : 'default'} size="small">
          {row.onboarding_completed ? '已完成' : '未完成'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminChild }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">儿童管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 个儿童</Tag>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Input
            prefixIcon={<SearchIcon />}
            placeholder="搜索儿童昵称"
            value={search}
            onChange={(val) => { setSearch(val as string); setPage(1) }}
            style={{ width: 300 }}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadChildren}>刷新</Button>
        </div>

        <Table
          data={children}
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
