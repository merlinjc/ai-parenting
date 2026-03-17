import { useState, useEffect } from 'react'
import { Drawer, Form, Input, Select, Switch, Textarea, InputNumber, Button, Space, Tag } from 'tdesign-react'
import type { PushRule } from '../data/mockData'

const { FormItem } = Form

interface RuleEditDrawerProps {
  visible: boolean
  rule: PushRule | null
  onClose: () => void
  onSave: (rule: PushRule) => void
}

const channelOptions = [
  { label: 'APNs (iOS推送)', value: 'apns' },
  { label: '微信服务号', value: 'wechat' },
  { label: 'WhatsApp', value: 'whatsapp' },
  { label: 'Telegram', value: 'telegram' },
]

const triggerTypeOptions = [
  { label: 'Cron 定时', value: 'cron' },
  { label: '事件驱动', value: 'event' },
  { label: '里程碑', value: 'milestone' },
]

export default function RuleEditDrawer({ visible, rule, onClose, onSave }: RuleEditDrawerProps) {
  const [formData, setFormData] = useState<PushRule | null>(null)

  useEffect(() => {
    if (rule) {
      setFormData({ ...rule })
    }
  }, [rule])

  if (!formData) return null

  const handleFieldChange = <K extends keyof PushRule>(key: K, value: PushRule[K]) => {
    setFormData(prev => prev ? { ...prev, [key]: value } : null)
  }

  const handleSubmit = () => {
    if (formData) {
      onSave(formData)
    }
  }

  return (
    <Drawer
      visible={visible}
      onClose={onClose}
      header={
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold">编辑推送规则</span>
          <Tag theme={formData.isActive ? 'success' : 'default'} variant="light" size="small">
            {formData.isActive ? '已启用' : '已禁用'}
          </Tag>
        </div>
      }
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button theme="primary" onClick={handleSubmit}>保存</Button>
        </div>
      }
      size="large"
      closeOnOverlayClick
    >
      <Form layout="vertical" className="p-2">
        {/* 基本信息 */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">基本信息</h3>

          <FormItem label="规则名称">
            <Input
              value={formData.name}
              onChange={(val) => handleFieldChange('name', val as string)}
              placeholder="输入规则名称"
            />
          </FormItem>

          <FormItem label="规则描述">
            <Textarea
              value={formData.description}
              onChange={(val) => handleFieldChange('description', val as string)}
              placeholder="描述规则的用途和触发条件"
              autosize={{ minRows: 2, maxRows: 4 }}
            />
          </FormItem>

          <FormItem label="启用状态">
            <Switch
              value={formData.isActive}
              onChange={(val) => handleFieldChange('isActive', val as boolean)}
            />
          </FormItem>
        </div>

        {/* 触发配置 */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">触发配置</h3>

          <FormItem label="触发类型">
            <Select
              value={formData.triggerType}
              options={triggerTypeOptions}
              onChange={(val) => handleFieldChange('triggerType', val as PushRule['triggerType'])}
            />
          </FormItem>

          {formData.triggerType === 'cron' && (
            <FormItem label="Cron 表达式" help="示例: 0 8 * * * (每天 08:00)">
              <Input
                value={formData.cronExpression || ''}
                onChange={(val) => handleFieldChange('cronExpression', val as string)}
                placeholder="0 8 * * *"
              />
            </FormItem>
          )}

          {formData.triggerType === 'event' && (
            <FormItem label="事件类型">
              <Input
                value={formData.eventType || ''}
                onChange={(val) => handleFieldChange('eventType', val as string)}
                placeholder="weekly_feedback_created"
              />
            </FormItem>
          )}

          <FormItem label="冷却时间（分钟）" help="同一规则对同一用户的最小间隔">
            <InputNumber
              value={formData.cooldownMinutes}
              onChange={(val) => handleFieldChange('cooldownMinutes', (val || 0) as number)}
              min={0}
              max={43200}
              step={60}
              theme="normal"
            />
          </FormItem>
        </div>

        {/* 条件与渠道 */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">条件与渠道</h3>

          <FormItem label="触发条件摘要">
            <Textarea
              value={formData.conditionSummary}
              onChange={(val) => handleFieldChange('conditionSummary', val as string)}
              placeholder="描述触发条件"
              autosize={{ minRows: 2, maxRows: 3 }}
            />
          </FormItem>

          <FormItem label="渠道优先级" help="选择渠道并按优先级排序">
            <Select
              value={formData.channelPriority}
              options={channelOptions}
              multiple
              onChange={(val) => handleFieldChange('channelPriority', val as string[])}
              placeholder="选择推送渠道"
            />
          </FormItem>
        </div>

        {/* 统计数据（只读展示） */}
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">运行统计</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-400">累计推送</div>
              <div className="text-xl font-bold text-gray-800 mt-1">{formData.totalSent.toLocaleString()}</div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-xs text-gray-400">送达率</div>
              <div className="text-xl font-bold text-success mt-1">
                {formData.deliveryRate > 0 ? `${(formData.deliveryRate * 100).toFixed(1)}%` : '-'}
              </div>
            </div>
          </div>
          {formData.lastTriggeredAt && (
            <div className="mt-3 text-xs text-gray-400">
              上次触发: {new Date(formData.lastTriggeredAt).toLocaleString('zh-CN')}
            </div>
          )}
        </div>
      </Form>
    </Drawer>
  )
}
