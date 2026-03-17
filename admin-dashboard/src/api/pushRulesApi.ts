/**
 * 推送规则 API 服务
 *
 * 对接后端 /admin/push-rules 端点。
 * 后端不可用时自动降级到 mock 数据。
 */

import apiClient, { ApiError } from './client'
import { mockPushRules } from '../data/mockData'
import type { PushRule } from '../data/mockData'

/**
 * 获取推送规则列表
 *
 * 优先从后端加载，失败时降级到 mock 数据。
 */
export async function fetchPushRules(): Promise<PushRule[]> {
  try {
    const data = await apiClient.get<{ rules: PushRule[] }>('/admin/push-rules')
    return data.rules
  } catch (err) {
    if (err instanceof ApiError) {
      console.warn(`[PushRulesApi] Backend unavailable (${err.status}), using mock data`)
    } else {
      console.warn('[PushRulesApi] Network error, using mock data')
    }
    return [...mockPushRules]
  }
}

/**
 * 更新推送规则
 */
export async function updatePushRule(rule: PushRule): Promise<PushRule> {
  try {
    return await apiClient.put<PushRule>(`/admin/push-rules/${rule.id}`, rule)
  } catch (err) {
    console.warn('[PushRulesApi] Update failed, returning local copy')
    return rule
  }
}

/**
 * 切换规则启用/禁用状态
 */
export async function togglePushRule(ruleId: string, isActive: boolean): Promise<void> {
  try {
    await apiClient.put(`/admin/push-rules/${ruleId}/toggle`, { is_active: isActive })
  } catch {
    console.warn('[PushRulesApi] Toggle failed, state updated locally only')
  }
}
