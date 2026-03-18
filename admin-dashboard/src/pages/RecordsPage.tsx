import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tag, Select, Input, Button, Dialog, MessagePlugin, Space } from 'tdesign-react'
import { SearchIcon, RefreshIcon, DeleteIcon } from 'tdesign-icons-react'
import { fetchRecords, deleteRecord, type AdminRecord } from '../api/adminApi'

const typeMap: Record<string, { label: string; theme: 'primary' | 'success' | 'warning' | 'danger' }> = {
  quick_check: { label: '快速检查', theme: 'primary' },
  event: { label: '事件记录', theme: 'success' },
  voice: { label: '语音记录', theme: 'warning' },
}

export default function RecordsPage() {
  const [records, setRecords] = useState<AdminRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [deleteDialogVisible, setDeleteDialogVisible] = useState(false)
  const [recordToDelete, setRecordToDelete] = useState<AdminRecord | null>(null)
  const pageSize = 20

  const loadRecords = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchRecords({
        limit: pageSize,
        offset: (page - 1) * pageSize,
        type: typeFilter || undefined,
        search: search || undefined,
      })
      setRecords(res.records)
      setTotal(res.total)
    } catch (err) {
      console.error('Failed to load records:', err)
    } finally {
      setLoading(false)
    }
  }, [page, typeFilter, search])

  useEffect(() => {
    loadRecords()
  }, [loadRecords])

  const handleDelete = async () => {
    if (!recordToDelete) return
    try {
      await deleteRecord(recordToDelete.id)
      setRecords(prev => prev.filter(r => r.id !== recordToDelete.id))
      setTotal(prev => prev - 1)
      MessagePlugin.success('记录已删除')
    } catch (err) {
      MessagePlugin.error(err instanceof Error ? err.message : '删除失败')
    } finally {
      setDeleteDialogVisible(false)
      setRecordToDelete(null)
    }
  }

  const columns = [
    {
      title: '类型',
      colKey: 'type',
      width: 100,
      cell: ({ row }: { row: AdminRecord }) => {
        const t = typeMap[row.type] || { label: row.type, theme: 'primary' as const }
        return <Tag variant="light" theme={t.theme} size="small">{t.label}</Tag>
      },
    },
    {
      title: '儿童',
      colKey: 'child_nickname',
      width: 100,
      cell: ({ row }: { row: AdminRecord }) => row.child_nickname || '-',
    },
    {
      title: '家长邮箱',
      colKey: 'user_email',
      width: 160,
      cell: ({ row }: { row: AdminRecord }) => row.user_email || '-',
    },
    {
      title: '内容',
      colKey: 'content',
      width: 250,
      ellipsis: true,
      cell: ({ row }: { row: AdminRecord }) => (
        <span className="text-gray-600">{row.content?.slice(0, 80) || '-'}</span>
      ),
    },
    {
      title: '场景',
      colKey: 'scene',
      width: 90,
      cell: ({ row }: { row: AdminRecord }) => row.scene ? <Tag variant="outline" size="small">{row.scene}</Tag> : '-',
    },
    {
      title: '标签',
      colKey: 'tags',
      width: 140,
      cell: ({ row }: { row: AdminRecord }) => (
        <div className="flex flex-wrap gap-1">
          {row.tags?.slice(0, 3).map(t => (
            <Tag key={t} variant="outline" size="small">{t}</Tag>
          )) || '-'}
        </div>
      ),
    },
    {
      title: '创建时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminRecord }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      colKey: 'action',
      width: 80,
      cell: ({ row }: { row: AdminRecord }) => (
        <Button
          variant="text"
          theme="danger"
          size="small"
          icon={<DeleteIcon />}
          onClick={() => { setRecordToDelete(row); setDeleteDialogVisible(true) }}
        />
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">观察记录管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 条记录</Tag>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Input
            prefixIcon={<SearchIcon />}
            placeholder="搜索记录内容"
            value={search}
            onChange={(val) => { setSearch(val as string); setPage(1) }}
            style={{ width: 250 }}
          />
          <Select
            value={typeFilter}
            onChange={(val) => { setTypeFilter(val as string); setPage(1) }}
            placeholder="按类型筛选"
            clearable
            style={{ width: 140 }}
            options={[
              { label: '全部', value: '' },
              { label: '快速检查', value: 'quick_check' },
              { label: '事件记录', value: 'event' },
              { label: '语音记录', value: 'voice' },
            ]}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadRecords}>刷新</Button>
        </div>

        <Table
          data={records}
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

      <Dialog
        visible={deleteDialogVisible}
        header="确认删除"
        body={
          <Space direction="vertical">
            <span>确定要删除这条观察记录吗？</span>
            <span className="text-red-500 text-sm">此操作不可撤销。</span>
          </Space>
        }
        confirmBtn={{ theme: 'danger', content: '确认删除' }}
        onConfirm={handleDelete}
        onClose={() => { setDeleteDialogVisible(false); setRecordToDelete(null) }}
      />
    </div>
  )
}
