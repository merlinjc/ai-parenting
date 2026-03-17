/**
 * 渠道监控 API 服务
 *
 * 对接后端 /admin/channel-stats 端点。
 * 后端不可用时自动降级到 mock 数据。
 */

import apiClient, { ApiError } from './client'
import {
  mockChannelStatuses,
  mockAlertLogs,
  mockBindingStats,
  latencyTrendData,
  bindingTrendData,
} from '../data/mockData'
import type { ChannelStatus, AlertLog, BindingStats } from '../data/mockData'

interface ChannelStatsResponse {
  channels: ChannelStatus[]
  alerts: AlertLog[]
  bindingStats: BindingStats[]
  latencyTrend: typeof latencyTrendData
  bindingTrend: typeof bindingTrendData
}

/**
 * 获取渠道监控全量数据
 *
 * 优先从后端加载，失败时降级到 mock 数据。
 */
export async function fetchChannelStats(): Promise<ChannelStatsResponse> {
  try {
    return await apiClient.get<ChannelStatsResponse>('/admin/channel-stats')
  } catch (err) {
    if (err instanceof ApiError) {
      console.warn(`[ChannelMonitorApi] Backend unavailable (${err.status}), using mock data`)
    } else {
      console.warn('[ChannelMonitorApi] Network error, using mock data')
    }
    return {
      channels: [...mockChannelStatuses],
      alerts: [...mockAlertLogs],
      bindingStats: [...mockBindingStats],
      latencyTrend: latencyTrendData,
      bindingTrend: bindingTrendData,
    }
  }
}

/**
 * 获取渠道状态列表
 */
export async function fetchChannelStatuses(): Promise<ChannelStatus[]> {
  const stats = await fetchChannelStats()
  return stats.channels
}

/**
 * 获取告警日志
 */
export async function fetchAlertLogs(): Promise<AlertLog[]> {
  const stats = await fetchChannelStats()
  return stats.alerts
}

/**
 * 获取绑定统计
 */
export async function fetchBindingStats(): Promise<BindingStats[]> {
  const stats = await fetchChannelStats()
  return stats.bindingStats
}
