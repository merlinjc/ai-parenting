/**
 * Admin 管理 API 服务
 *
 * 对接后端 /admin/* 端点，提供统一的数据获取和管理操作。
 */

import apiClient from './client'

// ---------------------------------------------------------------------------
// 通用类型
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  total: number
  has_more: boolean
  [key: string]: T[] | number | boolean
}

export interface PaginationParams {
  limit?: number
  offset?: number
}

// ---------------------------------------------------------------------------
// 增强统计
// ---------------------------------------------------------------------------

export interface EnhancedStats {
  total_users: number
  total_children: number
  total_plans: number
  total_records: number
  total_messages: number
  total_ai_sessions: number
  total_devices: number
  total_push_logs: number
  total_weekly_feedbacks: number
  total_channel_bindings: number
  active_plans: number
  active_devices: number
  active_bindings: number
  today_new_users: number
  today_new_records: number
  today_ai_sessions: number
  today_push_count: number
}

export async function fetchEnhancedStats(): Promise<EnhancedStats> {
  return apiClient.get<EnhancedStats>('/admin/enhanced-stats')
}

// ---------------------------------------------------------------------------
// 用户管理
// ---------------------------------------------------------------------------

export interface AdminUser {
  id: string
  email: string | null
  display_name: string | null
  caregiver_role: string | null
  auth_provider: string
  is_admin: boolean
  timezone: string
  push_enabled: boolean
  created_at: string
  updated_at: string
  children_count: number
}

export interface AdminUserListResponse {
  users: AdminUser[]
  total: number
  has_more: boolean
}

export async function fetchUsers(params: PaginationParams & { search?: string } = {}): Promise<AdminUserListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.search) query.set('search', params.search)
  return apiClient.get<AdminUserListResponse>(`/admin/users?${query}`)
}

export async function updateUser(userId: string, data: { display_name?: string; is_admin?: boolean; push_enabled?: boolean }): Promise<AdminUser> {
  return apiClient.patch<AdminUser>(`/admin/users/${userId}`, data)
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}`)
}

// ---------------------------------------------------------------------------
// 儿童管理
// ---------------------------------------------------------------------------

export interface AdminChild {
  id: string
  user_id: string
  user_email: string | null
  nickname: string
  birth_year_month: string
  age_months: number
  stage: string
  focus_themes: string[] | null
  risk_level: string
  onboarding_completed: boolean
  created_at: string
}

export interface AdminChildListResponse {
  children: AdminChild[]
  total: number
  has_more: boolean
}

export async function fetchChildren(params: PaginationParams & { search?: string } = {}): Promise<AdminChildListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.search) query.set('search', params.search)
  return apiClient.get<AdminChildListResponse>(`/admin/children?${query}`)
}

// ---------------------------------------------------------------------------
// 计划管理
// ---------------------------------------------------------------------------

export interface AdminPlan {
  id: string
  child_id: string
  child_nickname: string | null
  title: string
  status: string
  focus_theme: string
  current_day: number
  completion_rate: number
  start_date: string
  end_date: string
  created_at: string
}

export interface AdminPlanListResponse {
  plans: AdminPlan[]
  total: number
  has_more: boolean
}

export async function fetchPlans(params: PaginationParams & { status?: string } = {}): Promise<AdminPlanListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.status) query.set('status', params.status)
  return apiClient.get<AdminPlanListResponse>(`/admin/plans?${query}`)
}

// ---------------------------------------------------------------------------
// 观察记录管理
// ---------------------------------------------------------------------------

export interface AdminRecord {
  id: string
  child_id: string
  child_nickname: string | null
  user_email: string | null
  type: string
  tags: string[] | null
  content: string | null
  scene: string | null
  theme: string | null
  voice_url: string | null
  created_at: string
}

export interface AdminRecordListResponse {
  records: AdminRecord[]
  total: number
  has_more: boolean
}

export async function fetchRecords(params: PaginationParams & { child_id?: string; type?: string; search?: string } = {}): Promise<AdminRecordListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.child_id) query.set('child_id', params.child_id)
  if (params.type) query.set('type', params.type)
  if (params.search) query.set('search', params.search)
  return apiClient.get<AdminRecordListResponse>(`/admin/records?${query}`)
}

export async function deleteRecord(recordId: string): Promise<void> {
  await apiClient.delete(`/admin/records/${recordId}`)
}

// ---------------------------------------------------------------------------
// AI 会话管理
// ---------------------------------------------------------------------------

export interface AdminAISession {
  id: string
  child_id: string
  child_nickname: string | null
  session_type: string
  status: string
  input_text: string | null
  model_provider: string | null
  model_version: string | null
  latency_ms: number | null
  retry_count: number | null
  error_info: string | null
  created_at: string
  completed_at: string | null
}

export interface AdminAISessionListResponse {
  sessions: AdminAISession[]
  total: number
  has_more: boolean
}

export interface AISessionStats {
  total_sessions: number
  success_count: number
  failed_count: number
  degraded_count: number
  success_rate: number
  avg_latency_ms: number
  by_type: Array<{ type: string; count: number; avg_latency: number }>
  by_model: Array<{ provider: string; count: number }>
}

export async function fetchAISessions(params: PaginationParams & { session_type?: string; status?: string } = {}): Promise<AdminAISessionListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.session_type) query.set('session_type', params.session_type)
  if (params.status) query.set('status', params.status)
  return apiClient.get<AdminAISessionListResponse>(`/admin/ai-sessions?${query}`)
}

export async function fetchAISessionStats(): Promise<AISessionStats> {
  return apiClient.get<AISessionStats>('/admin/ai-sessions/stats')
}

// ---------------------------------------------------------------------------
// 周反馈管理
// ---------------------------------------------------------------------------

export interface AdminWeeklyFeedback {
  id: string
  plan_id: string
  child_id: string
  child_nickname: string | null
  status: string
  summary_text: string | null
  selected_decision: string | null
  record_count_this_week: number | null
  completion_rate_this_week: number | null
  error_info: string | null
  created_at: string
  viewed_at: string | null
  decided_at: string | null
}

export interface AdminWeeklyFeedbackListResponse {
  feedbacks: AdminWeeklyFeedback[]
  total: number
  has_more: boolean
}

export async function fetchWeeklyFeedbacks(params: PaginationParams & { status?: string } = {}): Promise<AdminWeeklyFeedbackListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.status) query.set('status', params.status)
  return apiClient.get<AdminWeeklyFeedbackListResponse>(`/admin/weekly-feedbacks?${query}`)
}

export async function retryWeeklyFeedback(feedbackId: string): Promise<void> {
  await apiClient.post(`/admin/weekly-feedbacks/${feedbackId}/retry`)
}

// ---------------------------------------------------------------------------
// 消息管理
// ---------------------------------------------------------------------------

export interface AdminMessage {
  id: string
  user_id: string
  user_email: string | null
  child_id: string | null
  type: string
  title: string
  body: string | null
  read_status: string
  push_status: string | null
  created_at: string
}

export interface AdminMessageListResponse {
  messages: AdminMessage[]
  total: number
  has_more: boolean
}

export interface MessageStats {
  total_messages: number
  read_count: number
  unread_count: number
  read_rate: number
  push_sent_count: number
  push_delivered_count: number
  push_delivery_rate: number
  by_type: Array<{ type: string; count: number }>
}

export async function fetchMessages(params: PaginationParams & { user_id?: string; type?: string; read_status?: string } = {}): Promise<AdminMessageListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.user_id) query.set('user_id', params.user_id)
  if (params.type) query.set('type', params.type)
  if (params.read_status) query.set('read_status', params.read_status)
  return apiClient.get<AdminMessageListResponse>(`/admin/messages?${query}`)
}

export async function fetchMessageStats(): Promise<MessageStats> {
  return apiClient.get<MessageStats>('/admin/messages/stats')
}

// ---------------------------------------------------------------------------
// 设备管理
// ---------------------------------------------------------------------------

export interface AdminDevice {
  id: string
  user_id: string
  user_email: string | null
  platform: string | null
  app_version: string | null
  is_active: boolean
  last_active_at: string | null
  push_token_preview: string | null
}

export interface AdminDeviceListResponse {
  devices: AdminDevice[]
  total: number
  has_more: boolean
}

export interface DeviceStats {
  total_devices: number
  active_devices: number
  inactive_devices: number
  by_platform: Array<{ platform: string; count: number }>
  by_version: Array<{ version: string; count: number }>
}

export async function fetchDevices(params: PaginationParams & { platform?: string; is_active?: boolean } = {}): Promise<AdminDeviceListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.platform) query.set('platform', params.platform)
  if (params.is_active !== undefined) query.set('is_active', String(params.is_active))
  return apiClient.get<AdminDeviceListResponse>(`/admin/devices?${query}`)
}

export async function fetchDeviceStats(): Promise<DeviceStats> {
  return apiClient.get<DeviceStats>('/admin/devices/stats')
}

// ---------------------------------------------------------------------------
// 推送日志管理
// ---------------------------------------------------------------------------

export interface AdminPushLog {
  id: string
  user_id: string | null
  user_email: string | null
  rule_id: string | null
  channel: string | null
  status: string
  error: string | null
  latency_ms: number | null
  fallback_used: boolean | null
  fallback_channel: string | null
  created_at: string
}

export interface AdminPushLogListResponse {
  logs: AdminPushLog[]
  total: number
  has_more: boolean
}

export interface PushLogStats {
  total_logs: number
  sent_count: number
  delivered_count: number
  failed_count: number
  delivery_rate: number
  avg_latency_ms: number
  fallback_rate: number
  by_channel: Array<{ channel: string; count: number; failed: number; failure_rate: number }>
  by_rule: Array<{ rule_id: string; count: number }>
}

export async function fetchPushLogs(params: PaginationParams & { channel?: string; status?: string; rule_id?: string; user_id?: string } = {}): Promise<AdminPushLogListResponse> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))
  if (params.channel) query.set('channel', params.channel)
  if (params.status) query.set('status', params.status)
  if (params.rule_id) query.set('rule_id', params.rule_id)
  if (params.user_id) query.set('user_id', params.user_id)
  return apiClient.get<AdminPushLogListResponse>(`/admin/push-logs?${query}`)
}

export async function fetchPushLogStats(): Promise<PushLogStats> {
  return apiClient.get<PushLogStats>('/admin/push-logs/stats')
}

// ---------------------------------------------------------------------------
// 认证 (复用 /auth 端点)
// ---------------------------------------------------------------------------

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export async function adminLogin(email: string, password: string): Promise<LoginResponse> {
  return apiClient.post<LoginResponse>('/auth/login', { email, password })
}
