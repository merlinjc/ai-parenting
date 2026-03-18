import { useState, useEffect, useCallback } from 'react'
import { Card, Table, Tag, Select, Button, Row, Col, Loading } from 'tdesign-react'
import { RefreshIcon } from 'tdesign-icons-react'
import { fetchDevices, fetchDeviceStats, type AdminDevice, type DeviceStats } from '../api/adminApi'

export default function DevicesPage() {
  const [devices, setDevices] = useState<AdminDevice[]>([])
  const [stats, setStats] = useState<DeviceStats | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [platformFilter, setPlatformFilter] = useState<string>('')
  const [activeFilter, setActiveFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [devicesRes, statsRes] = await Promise.all([
        fetchDevices({
          limit: pageSize,
          offset: (page - 1) * pageSize,
          platform: platformFilter || undefined,
          is_active: activeFilter === '' ? undefined : activeFilter === 'true',
        }),
        fetchDeviceStats(),
      ])
      setDevices(devicesRes.devices)
      setTotal(devicesRes.total)
      setStats(statsRes)
    } catch (err) {
      console.error('Failed to load devices:', err)
    } finally {
      setLoading(false)
    }
  }, [page, platformFilter, activeFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const columns = [
    {
      title: '平台',
      colKey: 'platform',
      width: 90,
      cell: ({ row }: { row: AdminDevice }) => (
        <Tag variant="outline" size="small">{row.platform || '-'}</Tag>
      ),
    },
    {
      title: '状态',
      colKey: 'is_active',
      width: 80,
      cell: ({ row }: { row: AdminDevice }) => (
        <Tag variant="light" theme={row.is_active ? 'success' : 'default'} size="small">
          {row.is_active ? '活跃' : '离线'}
        </Tag>
      ),
    },
    {
      title: '用户邮箱',
      colKey: 'user_email',
      width: 180,
      cell: ({ row }: { row: AdminDevice }) => row.user_email || '-',
    },
    {
      title: '版本',
      colKey: 'app_version',
      width: 100,
      cell: ({ row }: { row: AdminDevice }) => row.app_version || '-',
    },
    {
      title: 'Push Token',
      colKey: 'push_token_preview',
      width: 160,
      cell: ({ row }: { row: AdminDevice }) => (
        <span className="text-gray-500 font-mono text-xs">{row.push_token_preview || '-'}</span>
      ),
    },
    {
      title: '最后活跃',
      colKey: 'last_active_at',
      width: 160,
      cell: ({ row }: { row: AdminDevice }) => (
        row.last_active_at ? new Date(row.last_active_at).toLocaleString('zh-CN') : '-'
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">设备管理</h1>
        <Tag theme="primary" variant="light" size="large">{total} 个设备</Tag>
      </div>

      {stats ? (
        <Row gutter={[16, 16]}>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">总设备</div>
              <div className="text-2xl font-bold text-gray-800">{stats.total_devices}</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">活跃设备</div>
              <div className="text-2xl font-bold text-green-600">{stats.active_devices}</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">离线设备</div>
              <div className="text-2xl font-bold text-gray-400">{stats.inactive_devices}</div>
            </Card>
          </Col>
          <Col span={3}>
            <Card style={{ borderRadius: 12 }}>
              <div className="text-sm text-gray-500">平台分布</div>
              <div className="flex gap-2 mt-1">
                {stats.by_platform.map(p => (
                  <Tag key={p.platform} variant="light" size="small">{p.platform}: {p.count}</Tag>
                ))}
              </div>
            </Card>
          </Col>
        </Row>
      ) : loading ? <Loading /> : null}

      <Card style={{ borderRadius: 12 }}>
        <div className="flex items-center gap-3 mb-4">
          <Select
            value={platformFilter}
            onChange={(val) => { setPlatformFilter(val as string); setPage(1) }}
            placeholder="按平台筛选"
            clearable
            style={{ width: 130 }}
            options={[
              { label: '全部', value: '' },
              { label: 'iOS', value: 'ios' },
              { label: 'Android', value: 'android' },
            ]}
          />
          <Select
            value={activeFilter}
            onChange={(val) => { setActiveFilter(val as string); setPage(1) }}
            placeholder="活跃状态"
            clearable
            style={{ width: 130 }}
            options={[
              { label: '全部', value: '' },
              { label: '活跃', value: 'true' },
              { label: '离线', value: 'false' },
            ]}
          />
          <Button icon={<RefreshIcon />} variant="outline" onClick={loadData}>刷新</Button>
        </div>

        <Table
          data={devices}
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
