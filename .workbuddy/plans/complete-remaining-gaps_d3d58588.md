---
name: complete-remaining-gaps
overview: 补齐 iOS 客户端与后端剩余的功能缺失项：(1) "加入本周关注"后端 API + iOS 集成，(2) 文件上传占位 API，(3) iOS APNs 推送集成，(4) iOS 端完整单元测试。
todos:
  - id: gap1-hunyuan-provider
    content: Gap 1：接入混元大模型 — 新建 HunyuanProvider 实现 ModelProvider 接口，config.py 新增 API 配置，deps.py 按 ai_provider 分发，安装 httpx 依赖
    status: completed
  - id: gap2-jwt-auth
    content: Gap 2：JWT 用户认证体系 — 后端新增 auth 路由(注册/登录)、JWT 中间件、密码加密；iOS 端新增 JWTAuthProvider + 登录页面 + Keychain 存储
    status: completed
  - id: gap3-plan-day-advance
    content: Gap 3：Plan 日推进机制 — plan_service 新增 advance_plan_day()，app.py lifespan 中启动 APScheduler 每日零点推进 current_day，计划到期自动标记 completed
    status: completed
  - id: gap4-push-scheduling
    content: Gap 4：定时推送调度 — 新建 scheduler_service.py，配置每日任务提醒(早8点)、记录提示(晚6点)、计划到期提醒(第6天)，集成到 APScheduler
    status: completed
    dependencies:
      - gap3-plan-day-advance
  - id: gap8-record-daytask-sync
    content: Gap 8：记录创建后联动 DayTask — record_service.create_record() 中检测 source_plan_id，自动回写 DayTask 完成状态并更新 synced_to_plan
    status: completed
  - id: gap9-onboarding-auto-plan
    content: Gap 9：Onboarding 完成后自动生成首份计划 — iOS OnboardingView.submitOnboarding() 新增第5步调用 createPlan API
    status: completed
  - id: gap10-auto-weekly-feedback
    content: Gap 10：第7天自动触发周反馈 — 在日推进调度中检测 current_day=7 时自动调用 weekly_feedback_service 生成周反馈并发送消息通知
    status: completed
    dependencies:
      - gap3-plan-day-advance
  - id: gap11-consult-prep-view
    content: Gap 11：咨询准备页面 — iOS 新建 ConsultPrepView.swift，后端新增 GET /consult-prep 端点，InstantHelpView 添加导航跳转
    status: completed
---

# 补齐 AI Parenting 全部 15 个需求 Gap

## 总览

15 个 Gap 中 **7 个已解决**（Gap 5/6/7/12/13/14/15），**8 个待实现**。本计划按优先级逐项落地。

| Gap | 标题 | 状态 | 优先级 |
| --- | --- | --- | --- |
| 1 | 混元大模型接入 | 待实现 | Critical |
| 2 | JWT 用户认证 | 待实现 | Critical |
| 3 | Plan 日推进 | 待实现 | High |
| 4 | 定时推送调度 | 待实现 | High |
| 5 | ProfileView | ✅ 已解决 | — |
| 6 | ChildEditView | ✅ 已解决 | — |
| 7 | RecordListView | ✅ 已解决 | — |
| 8 | 记录联动 DayTask | 待实现 | Medium |
| 9 | Onboarding 自动生成计划 | 待实现 | Medium |
| 10 | 第7天自动周反馈 | 待实现 | Medium |
| 11 | 咨询准备页面 | 待实现 | Medium |
| 12 | CORS Middleware | ✅ 已解决 | — |
| 13 | File Upload | ✅ 已解决 | — |
| 14 | Push Notification iOS | ✅ 已解决 | — |
| 15 | Focus Note endpoint | ✅ 已解决 | — |


---

## Gap 1：混元大模型接入（Critical）

### 需求

将 MockProvider 替换为真实的腾讯混元大模型调用，使三大核心场景（即时求助、计划生成、周反馈）产出真实 AI 内容。

### 混元 API 规格

- **Base URL**: `https://api.hunyuan.cloud.tencent.com/v1`
- **模型**: `hunyuan-lite`
- **认证**: `Authorization: Bearer sk-2I31BWLkc5AZ1yj5MfGxo87n7GBICUB8HmNC8SyXFZYUPDHg`
- **兼容 OpenAI 接口**

### 实现方案

**1. 安装依赖**：`pyproject.toml` 新增 `httpx>=0.27.0`

**2. config.py 新增配置**：

```python
hunyuan_api_key: str = ""
hunyuan_base_url: str = "https://api.hunyuan.cloud.tencent.com/v1"
hunyuan_model: str = "hunyuan-lite"
```

**3. 新建 `providers/hunyuan_provider.py`**：

- 继承 `ModelProvider`，实现 `generate()` 方法
- 使用 `httpx.AsyncClient` 调用 `/chat/completions`
- system message 指导输出纯 JSON
- 超时控制 + 错误处理

**4. deps.py 按 `settings.ai_provider` 分发**：

- `"mock"` → MockProvider
- `"hunyuan"` → HunyuanProvider

**5. 项目根目录 `.env` 配置**：

```
AIP_AI_PROVIDER=hunyuan
AIP_HUNYUAN_API_KEY=sk-2I31BWLkc5AZ1yj5MfGxo87n7GBICUB8HmNC8SyXFZYUPDHg
```

### 涉及文件

- `pyproject.toml` [MODIFY]
- `src/ai_parenting/backend/config.py` [MODIFY]
- `src/ai_parenting/providers/hunyuan_provider.py` [NEW]
- `src/ai_parenting/providers/__init__.py` [MODIFY]
- `src/ai_parenting/backend/deps.py` [MODIFY]
- `.env` [NEW]

---

## Gap 2：JWT 用户认证体系（Critical）

### 需求

替换 X-User-Id Header 模拟身份为真实的 JWT 认证，含注册、登录、Token 刷新。

### 实现方案

**1. 安装依赖**：`python-jose[cryptography]`, `passlib[bcrypt]`

**2. User 模型扩展**：新增 `email`、`hashed_password` 字段

**3. 新建 `backend/auth.py`**：JWT 创建/验证、密码 hash 工具函数、`get_current_user` 依赖

**4. 新建 `backend/routers/auth.py`**：

- `POST /api/v1/auth/register` — 注册
- `POST /api/v1/auth/login` — 登录返回 JWT
- `POST /api/v1/auth/refresh` — Token 刷新

**5. 现有路由迁移**：渐进式替换，保留 `X-User-Id` 兼容模式（header 优先，JWT 次之），通过统一 `get_current_user_id` 依赖实现

**6. iOS 端**：新建 `JWTAuthProvider`，登录页面，Keychain 存储 Token

### 涉及文件

- `pyproject.toml` [MODIFY]
- `src/ai_parenting/backend/models.py` [MODIFY]
- `src/ai_parenting/backend/auth.py` [NEW]
- `src/ai_parenting/backend/routers/auth.py` [NEW]
- `src/ai_parenting/backend/app.py` [MODIFY]
- `src/ai_parenting/backend/deps.py` [MODIFY]
- iOS `Core/Auth/JWTAuthProvider.swift` [NEW]
- iOS `Features/Auth/LoginView.swift` [NEW]

---

## Gap 3：Plan current_day 自动推进（High）

### 需求

每日零点自动将活跃计划的 `current_day` 从 1→2→...→7，第 7 天结束后标记计划为 completed。

### 实现方案

**1. 安装依赖**：`apscheduler>=3.10.0`

**2. plan_service.py 新增 `advance_all_plans()`**：

- 查询所有 status="active" 的 Plan
- 对每个 Plan：若 current_day < 7 则 +1；若 current_day >= 7 则 status="completed"

**3. 新建 `backend/scheduler.py`**：

- 初始化 `AsyncIOScheduler`
- 注册 cron job：每天 00:01 调用 `advance_all_plans()`
- 提供 `start_scheduler()` / `stop_scheduler()` 函数

**4. app.py lifespan 集成**：startup 时 `start_scheduler()`，shutdown 时 `stop_scheduler()`

### 涉及文件

- `pyproject.toml` [MODIFY]
- `src/ai_parenting/backend/services/plan_service.py` [MODIFY]
- `src/ai_parenting/backend/scheduler.py` [NEW]
- `src/ai_parenting/backend/app.py` [MODIFY]

---

## Gap 4：定时推送调度（High）

### 需求

定时发送任务提醒、记录提示、计划到期提醒。

### 实现方案

**1. scheduler.py 新增定时任务**：

- 每日 08:00 — 「今日任务提醒」（遍历活跃计划，发送当天 DayTask 摘要）
- 每日 18:00 — 「记录提示」（提醒家长记录今天的观察）
- 计划第 6 天 — 「周反馈即将就绪」提醒

**2. 新建 `backend/services/scheduler_service.py`**：

- `send_daily_task_reminders()` — 创建 plan_reminder 消息 + 推送
- `send_record_prompts()` — 创建 record_prompt 消息 + 推送
- `send_plan_expiry_reminder()` — 创建 plan_reminder 消息

### 涉及文件

- `src/ai_parenting/backend/services/scheduler_service.py` [NEW]
- `src/ai_parenting/backend/scheduler.py` [MODIFY]

---

## Gap 8：记录创建后联动 DayTask 完成状态（Medium）

### 需求

创建记录时如果关联了 `source_plan_id`，自动将当天 DayTask 标记为已完成。

### 实现方案

在 `record_service.create_record()` 末尾新增：

- 检查 `data.source_plan_id` 是否存在
- 若存在，获取活跃计划的当前 day_task
- 调用 `plan_service.update_day_task_completion()` 将状态设为 `executed`
- 将 record 的 `synced_to_plan` 设为 True

### 涉及文件

- `src/ai_parenting/backend/services/record_service.py` [MODIFY]

---

## Gap 9：Onboarding 完成后自动生成首份计划（Medium）

### 需求

用户完成引导流程后，自动调用后端 API 生成第一份 7 天微计划。

### 实现方案

iOS `OnboardingView.submitOnboarding()` 在步骤 4（刷新 AppState）后新增步骤 5：

- 获取新创建的 child ID
- 调用 `POST /api/v1/plans?child_id=xxx` 生成首份计划
- 失败时静默处理（不阻塞 Onboarding 完成，后续可在首页手动触发）

### 涉及文件

- `ios/Sources/AIParenting/Features/Onboarding/OnboardingView.swift` [MODIFY]

---

## Gap 10：第 7 天自动触发周反馈（Medium）

### 需求

计划推进到第 7 天时自动触发周反馈生成，而非等待用户手动触发。

### 实现方案

在 Gap 3 的 `advance_all_plans()` 中，当 `current_day` 推进到 7 时：

- 自动调用 `weekly_feedback_service.create_weekly_feedback()` 在后台生成周反馈
- 生成完成后自动创建 `weekly_feedback_ready` 消息 + 推送通知

### 涉及文件

- `src/ai_parenting/backend/services/plan_service.py` [MODIFY]（advance 逻辑中触发）
- `src/ai_parenting/backend/scheduler.py` [MODIFY]

---

## Gap 11：咨询准备页面（Medium）

### 需求

当 AI 建议就诊/咨询时，用户可跳转到咨询准备页面查看摘要和建议。

### 实现方案

**1. iOS 新建 `Features/AI/ConsultPrepView.swift`**：

- 展示：已收集的观察记录摘要、建议咨询要点、就诊准备清单
- 支持分享/导出功能

**2. 后端新增端点** `GET /api/v1/consult-prep?child_id=xxx`：

- 聚合最近记录、风险升级日志、AI 会话中的咨询建议
- 返回结构化的就诊准备数据

**3. InstantHelpView 导航**：将静态的"建议查看咨询准备"改为 NavigationLink 跳转到 ConsultPrepView

### 涉及文件

- `ios/Sources/AIParenting/Features/AI/ConsultPrepView.swift` [NEW]
- `src/ai_parenting/backend/routers/consult_prep.py` [NEW]
- `src/ai_parenting/backend/services/consult_prep_service.py` [NEW]
- `src/ai_parenting/backend/schemas.py` [MODIFY]
- `src/ai_parenting/backend/app.py` [MODIFY]
- `ios/Sources/AIParenting/Features/AI/InstantHelpView.swift` [MODIFY]
- `ios/Sources/AIParenting/Core/Network/Endpoint.swift` [MODIFY]