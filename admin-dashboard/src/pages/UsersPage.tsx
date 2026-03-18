import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Input, Button, Tag, Dialog, MessagePlugin, Switch, Space } from 'tdesign-react'
import { SearchIcon, DeleteIcon, RefreshIcon } from 'tdesign-icons-react'
import { fetchUsers, updateUser, deleteUser, type AdminUser } from '../api/adminApi'

export default function UsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [deleteDialogVisible, setDeleteDialogVisible] = useState(false)
  const [userToDelete, setUserToDelete] = useState<AdminUser | null>(null)
  const pageSize = 20

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchUsers({ limit: pageSize, offset: (page - 1) * pageSize, search: search || undefined })
      setUsers(res.users)
      setTotal(res.total)
    } catch (err) {
      console.error('Failed to load users:', err)
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleToggleAdmin = async (user: AdminUser) => {
    try {
      await updateUser(user.id, { is_admin: !user.is_admin })
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, is_admin: !u.is_admin } : u))
      MessagePlugin.success(`已${user.is_admin ? '取消' : '设为'}管理员`)
    } catch (err) {
      MessagePlugin.error(err instanceof Error ? err.message : '操作失败')
    }
  }

  const handleTogglePush = async (user: AdminUser) => {
    try {
      await updateUser(user.id, { push_enabled: !user.push_enabled })
      setUsers(prev => prev.map(u => u.id === user.id ? { ...u, push_enabled: !u.push_enabled } : u))
    } catch {
      MessagePlugin.error('操作失败')
    }
  }

  const handleDelete = async () => {
    if (!userToDelete) return
    try {
      await deleteUser(userToDelete.id)
      setUsers(prev => prev.filter(u => u.id !== userToDelete.id))
      setTotal(prev => prev - 1)
      MessagePlugin.success('用户已删除')
    } catch (err) {
      MessagePlugin.error(err instanceof Error ? err.message : '删除失败')
    } finally {
      setDeleteDialogVisible(false)
      setUserToDelete(null)
    }
  }

  const columns = [
    {
      title: '邮箱',
      colKey: 'email',
      width: 200,
      cell: ({ row }: { row: AdminUser }) => (
        <span className="font-medium">{row.email || '-'}</span>
      ),
    },
    {
      title: '昵称',
      colKey: 'display_name',
      width: 120,
      cell: ({ row }: { row: AdminUser }) => row.display_name || '-',
    },
    {
      title: '角色',
      colKey: 'caregiver_role',
      width: 90,
      cell: ({ row }: { row: AdminUser }) => (
        <Tag variant="light" size="small">{row.caregiver_role || '-'}</Tag>
      ),
    },
    {
      title: '儿童数',
      colKey: 'children_count',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '管理员',
      colKey: 'is_admin',
      width: 90,
      cell: ({ row }: { row: AdminUser }) => (
        <Switch size="small" value={row.is_admin} onChange={() => handleToggleAdmin(row)} />
      ),
    },
    {
      title: '推送',
      colKey: 'push_enabled',
      width: 80,
      cell: ({ row }: { row: AdminUser }) => (
        <Switch size="small" value={row.push_enabled} onChange={() => handleTogglePush(row)} />
      ),
    },
    {
      title: '注册时间',
      colKey: 'created_at',
      width: 160,
      cell: ({ row }: { row: AdminUser }) => new Date(row.created_at).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      colKey: 'action',
      width: 80,
      cell: ({ row }: { row: AdminUser }) => (
        <Button
          variant="text"
          theme="danger"
          size="small"
          icon={<DeleteIcon />}
          onClick={() => { setUserToDelete(row); setDeleteDialogVisible(true) }}
        />
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">用户管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 个用户</Tag>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Input
            prefixIcon={<SearchIcon />}
            placeholder="搜索邮箱或昵称"
            value={search}
            onChange={(val) => { setSearch(val as string); setPage(1) }}
            style={{ width: 300 }}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadUsers}>刷新</Button>
        </div>

        <Table
          data={users}
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
            <span>确定要删除用户 <strong>{userToDelete?.email}</strong> 吗？</span>
            <span className="text-red-500 text-sm">此操作不可撤销，将同时删除该用户的所有关联数据。</span>
          </Space>
        }
        confirmBtn={{ theme: 'danger', content: '确认删除' }}
        onConfirm={handleDelete}
        onClose={() => { setDeleteDialogVisible(false); setUserToDelete(null) }}
      />
    </div>
  )
}
