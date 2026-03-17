import { useState, useEffect } from 'react'
import { Statistic, Card, Tag, Space, Loading } from 'tdesign-react'
import {
  ChartLineIcon,
  CheckCircleIcon,
  ErrorCircleIcon,
  CloseCircleIcon,
} from 'tdesign-icons-react'
import { fetchPushRules, togglePushRule, updatePushRule } from '../api/pushRulesApi'
import RuleTable from '../components/RuleTable'
import RuleEditDrawer from '../components/RuleEditDrawer'
import type { PushRule } from '../data/mockData'

export default function PushRulesPage() {
  const [rules, setRules] = useState<PushRule[]>([])
  const [loading, setLoading] = useState(true)
  const [editingRule, setEditingRule] = useState<PushRule | null>(null)
  const [drawerVisible, setDrawerVisible] = useState(false)

  // 加载数据（优先后端 API，降级到 mock）
  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      const data = await fetchPushRules()
      if (!cancelled) {
        setRules(data)
        setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const totalSent = rules.reduce((sum, r) => sum + r.totalSent, 0)
  const avgDeliveryRate = rules.filter(r => r.deliveryRate > 0).reduce((sum, r) => sum + r.deliveryRate, 0)
    / Math.max(rules.filter(r => r.deliveryRate > 0).length, 1)
  const activeRules = rules.filter(r => r.isActive).length

  const handleToggle = (ruleId: string) => {
    setRules(prev =>
      prev.map(r => {
        if (r.id === ruleId) {
          const updated = { ...r, isActive: !r.isActive }
          togglePushRule(ruleId, updated.isActive)
          return updated
        }
        return r
      })
    )
  }

  const handleEdit = (rule: PushRule) => {
    setEditingRule(rule)
    setDrawerVisible(true)
  }

  const handleSave = async (updated: PushRule) => {
    const saved = await updatePushRule(updated)
    setRules(prev => prev.map(r => r.id === saved.id ? saved : r))
    setDrawerVisible(false)
    setEditingRule(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading text="加载推送规则..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">推送规则管理</h1>
        <p className="text-sm text-gray-500 mt-1">配置和管理智能推送规则，优化消息触达效率</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card bordered hoverable className="!rounded-xl !shadow-sm hover:!shadow-md transition-shadow">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-primary-light flex items-center justify-center">
              <ChartLineIcon size="24px" style={{ color: 'white' }} />
            </div>
            <div>
              <Statistic title="今日推送总量" value={totalSent} />
            </div>
          </div>
        </Card>

        <Card bordered hoverable className="!rounded-xl !shadow-sm hover:!shadow-md transition-shadow">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-success to-emerald-400 flex items-center justify-center">
              <CheckCircleIcon size="24px" style={{ color: 'white' }} />
            </div>
            <div>
              <Statistic title="平均送达率" value={avgDeliveryRate * 100} unit="%" decimalPlaces={1} />
            </div>
          </div>
        </Card>

        <Card bordered hoverable className="!rounded-xl !shadow-sm hover:!shadow-md transition-shadow">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-warning to-amber-400 flex items-center justify-center">
              <ErrorCircleIcon size="24px" style={{ color: 'white' }} />
            </div>
            <div>
              <Statistic title="活跃规则" value={activeRules} unit={`/ ${rules.length}`} />
            </div>
          </div>
        </Card>

        <Card bordered hoverable className="!rounded-xl !shadow-sm hover:!shadow-md transition-shadow">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-danger to-red-400 flex items-center justify-center">
              <CloseCircleIcon size="24px" style={{ color: 'white' }} />
            </div>
            <div>
              <Statistic title="退订率" value={0.4} unit="%" decimalPlaces={1} />
            </div>
          </div>
        </Card>
      </div>

      {/* 规则列表 */}
      <Card bordered className="!rounded-xl !shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">规则列表</h2>
          <Space>
            <Tag theme="primary" variant="light">共 {rules.length} 条规则</Tag>
          </Space>
        </div>
        <RuleTable
          rules={rules}
          onToggle={handleToggle}
          onEdit={handleEdit}
        />
      </Card>

      {/* 编辑抽屉 */}
      <RuleEditDrawer
        visible={drawerVisible}
        rule={editingRule}
        onClose={() => { setDrawerVisible(false); setEditingRule(null) }}
        onSave={handleSave}
      />
    </div>
  )
}
