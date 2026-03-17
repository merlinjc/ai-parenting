import { Table, Tag, Switch, Button, Space, Tooltip } from 'tdesign-react'
import { Edit1Icon } from 'tdesign-icons-react'
import type { PushRule } from '../data/mockData'

interface RuleTableProps {
  rules: PushRule[]
  onToggle: (ruleId: string) => void
  onEdit: (rule: PushRule) => void
}

const TRIGGER_TYPE_MAP = {
  cron: { text: 'Cron', theme: 'primary' as const },
  event: { text: '事件', theme: 'success' as const },
  milestone: { text: '里程碑', theme: 'warning' as const },
}

export default function RuleTable({ rules, onToggle, onEdit }: RuleTableProps) {
  const columns = [
    {
      colKey: 'name',
      title: '规则名称',
      width: 200,
      cell: ({ row }: { row: PushRule }) => (
        <div>
          <div className="font-medium text-gray-800">{row.name}</div>
          <div className="text-xs text-gray-400 mt-0.5 line-clamp-1">{row.description}</div>
        </div>
      ),
    },
    {
      colKey: 'triggerType',
      title: '触发类型',
      width: 100,
      cell: ({ row }: { row: PushRule }) => {
        const trigger = TRIGGER_TYPE_MAP[row.triggerType]
        return <Tag theme={trigger.theme} variant="light" size="small">{trigger.text}</Tag>
      },
    },
    {
      colKey: 'isActive',
      title: '状态',
      width: 80,
      cell: ({ row }: { row: PushRule }) => (
        <Switch value={row.isActive} onChange={() => onToggle(row.id)} size="small" />
      ),
    },
    {
      colKey: 'cooldownMinutes',
      title: '冷却时间',
      width: 100,
      cell: ({ row }: { row: PushRule }) => {
        if (row.cooldownMinutes === 0) return <span className="text-gray-400">无</span>
        if (row.cooldownMinutes >= 1440) return `${row.cooldownMinutes / 1440} 天`
        if (row.cooldownMinutes >= 60) return `${row.cooldownMinutes / 60} 小时`
        return `${row.cooldownMinutes} 分钟`
      },
    },
    {
      colKey: 'channelPriority',
      title: '渠道优先级',
      width: 180,
      cell: ({ row }: { row: PushRule }) => (
        <Space size="small" breakLine>
          {row.channelPriority.map((ch, i) => (
            <Tag key={ch} variant="outline" size="small">
              {i + 1}. {ch}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      colKey: 'totalSent',
      title: '累计推送',
      width: 100,
      sorter: true,
      cell: ({ row }: { row: PushRule }) => (
        <span className="font-medium">{row.totalSent.toLocaleString()}</span>
      ),
    },
    {
      colKey: 'deliveryRate',
      title: '送达率',
      width: 90,
      sorter: true,
      cell: ({ row }: { row: PushRule }) => {
        if (row.deliveryRate === 0) return <span className="text-gray-400">-</span>
        const rate = (row.deliveryRate * 100).toFixed(1)
        const color = row.deliveryRate >= 0.95 ? 'text-success' : row.deliveryRate >= 0.9 ? 'text-warning' : 'text-danger'
        return <span className={`font-medium ${color}`}>{rate}%</span>
      },
    },
    {
      colKey: 'lastTriggeredAt',
      title: '上次触发',
      width: 140,
      cell: ({ row }: { row: PushRule }) => {
        if (!row.lastTriggeredAt) return <span className="text-gray-400">从未触发</span>
        const d = new Date(row.lastTriggeredAt)
        return (
          <Tooltip content={d.toLocaleString('zh-CN')}>
            <span className="text-sm text-gray-600">
              {d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}{' '}
              {d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </Tooltip>
        )
      },
    },
    {
      colKey: 'actions',
      title: '操作',
      width: 80,
      fixed: 'right' as const,
      cell: ({ row }: { row: PushRule }) => (
        <Button
          variant="text"
          theme="primary"
          icon={<Edit1Icon />}
          onClick={() => onEdit(row)}
          size="small"
        >
          编辑
        </Button>
      ),
    },
  ]

  return (
    <Table
      data={rules}
      columns={columns}
      rowKey="id"
      stripe
      hover
      size="medium"
      tableLayout="fixed"
      pagination={{
        pageSize: 10,
        total: rules.length,
      }}
    />
  )
}
