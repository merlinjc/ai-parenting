# 项目全局里程碑规划

## 一、当前状态总览

本项目从产品设计到工程实现，已形成 **12 份设计文档**（约 332 KB）和 **3 个已通过测试的功能阶段**（MS1 AI 编排层 243 tests + MS2 核心数据链路 61 tests + MS3 闭环与可靠性 70 tests = **374 tests pass**）。

| 维度 | 完成情况 |
|---|---|
| 产品定位与边界 | ✅ 产品设计草案 |
| 领域观测模型 | ✅ 观测模型 V1.1 + 三阶段观察项清单 |
| 微计划模板 | ✅ 7 天微计划模板 + 示范样稿 |
| 系统架构 | ✅ 服务架构 + 页面信息架构 + 组件拆解 + 组件接口 |
| AI 规格 | ✅ 数据结构 + AI 输出结构 + Prompt 模板（三类） |
| **AI 编排层** | **✅ MS1 全部完成：三类渲染器 + 统一编排 + MockProvider（243 tests）** |
| **业务后端核心** | **✅ MS2 核心链路完成：ORM + 档案/记录/计划/AI 会话 API（61 tests）** |
| **后端闭环可靠性** | **✅ MS3 全部完成：消息/推送/周反馈/首页/审计/风险升级（70 tests）** |

---

## 二、里程碑总览

```
MS0 ✅ 设计文档体系（已完成）
  │
MS1 ✅ AI 编排层核心（已完成 — 243 tests）
  │    ├─ 即时求助 Prompt 模板代码
  │    ├─ 计划生成 Prompt 模板代码
  │    ├─ 周反馈 Prompt 模板代码
  │    ├─ 统一编排调度器
  │    └─ 模型供应商适配
  │
MS2 🔧 业务后端 — 核心数据链路（核心链路已完成 — 61 tests）
  │    ├─ ✅ 数据库 Schema + ORM（9 个领域对象）
  │    ├─ ⬜ 账户与身份（后续补充）
  │    ├─ ✅ 儿童档案 API
  │    ├─ ✅ 观察记录 API
  │    ├─ ✅ 微计划 + AI 调用集成
  │    ├─ ✅ AI 会话管理（即时求助端到端）
  │    └─ ⬜ 周反馈 API（后续补充）
  │
MS3    业务后端 — 闭环与可靠性
  │
MS4    iOS 客户端 MVP
  │
MS5    端到端集成与内测
```

---

## 三、各里程碑详情

### Milestone 0：设计文档体系 ✅ 已完成

12 份设计文档全部就绪，覆盖产品定位、领域模型、系统架构、AI 规格四大板块。后续实现可直接对照文档进行。

---

### Milestone 1：AI 编排层核心实现 ✅ 已完成

**目标**：三类 AI 功能的 Prompt 模板代码全部可用，统一调度器可被后端直接调用。

| 任务 | 描述 | 状态 |
|---|---|---|
| 即时求助 Prompt 模板代码 | 数据模型 + 常量 + 引擎 + 边界检查 + 渲染器 | ✅ 已完成 |
| 计划生成 Prompt 模板代码 | PlanGenerationResult 模型、模板常量、条件分支、计划级边界检查、降级结果 | ✅ 已完成 |
| 周反馈 Prompt 模板代码 | WeeklyFeedbackResult 模型、模板常量、条件分支、反馈级边界检查、降级结果 | ✅ 已完成 |
| 统一编排调度器 | `orchestrate(session_type, context)` 入口，集成模型路由、超时、校验、降级、审计 | ✅ 已完成 |
| 模型供应商适配层 | 抽象 `ModelProvider` 接口 + MockProvider 测试实现 | ✅ 已完成 |

**交付标准**：三类渲染器独立可用 ✅；调度器处理正常/超时/不合格/违规四种情况 ✅；单元测试 243 个全部通过 ✅。

---

### Milestone 2：业务后端 — 核心数据链路 🔧 核心链路已完成

**技术栈**：FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL（测试使用 SQLite）

**目标**：实现核心领域对象的持久化和 API，打通建档→记录→计划→AI→存储的完整链路。

| 任务 | 描述 | 状态 |
|---|---|---|
| 数据库 Schema + ORM | User、Device、Child、Record、Plan/DayTask、AISession、Message、WeeklyFeedback 9 个 ORM 模型 | ✅ 已完成 |
| 项目基础设施 | FastAPI 应用、数据库连接、依赖注入、配置管理 | ✅ 已完成 |
| 儿童档案 API | 创建/编辑/列表/阶段自动计算/关注主题管理/完成引导 | ✅ 已完成 |
| 观察记录 API | 三种记录类型创建/列表（分页+类型过滤）/按周聚合 | ✅ 已完成 |
| 微计划 API | 计划创建（调用 AI 生成）/活跃计划查询/日任务完成状态回写/完成率自动计算 | ✅ 已完成 |
| AI 会话 API | 即时求助请求→Orchestrator 调用→结果入库端到端/会话状态查询 | ✅ 已完成 |
| 账户与身份 | 注册、登录、Token 鉴权、设备绑定 | ⬜ 后续补充 |
| 周反馈 API | 反馈生成（调用 AI）、查看、决策回写 | ⬜ 后续补充 |

**交付标准**：API 可通过 HTTP 测试走通 ✅；AI 调用链路端到端可用（MockProvider）✅；OpenAPI 文档自动生成 ✅；61 个新增测试全部通过 ✅。

---

### Milestone 3：业务后端 — 闭环与可靠性

**目标**：补齐消息推送、异步任务、降级与审计，使后端成为完整可靠的服务系统。

| 任务 | 描述 |
|---|---|
| 通知与消息 | 消息模板、APNs 集成、调度、送达/点击回流 |
| 异步任务 | 周反馈异步生成、AI 重试、推送调度、周期聚合 |
| 降级与恢复 | AI 超时降级、幂等重试、状态回写补偿 |
| 审计与运营 | AI 输出日志脱敏、边界检查审计、关键链路监控 |
| 风险升级 | "建议咨询"状态自动切换为保守输出模式 |

**交付标准**：推送端到端可达；三种异常有正确降级；异步任务失败可重试无重复；审计可追溯。

---

### Milestone 4：iOS 客户端 MVP

**目标**：SwiftUI 实现 iOS 原生客户端，覆盖五大功能模块完整用户流程。

| 任务 | 描述 |
|---|---|
| 通用组件库 | 9 个通用组件（StatusTagGroup / SelectableTagGroup / ActionButtonGroup / SummaryCard / SplitInfoPanel / TimelineList / BottomTabBar / TopToolBar / InputFormSection） |
| 进入层 | 注册/登录、儿童档案初建、阶段初筛、通知授权 |
| 首页 | FocusCard / TodayTaskCard / RecentRecordSummary / PendingReturnCard / QuickHelpEntry |
| 计划页 | WeekOverviewCard / DaySelector / DailyTaskPanel / CompletionPanel / WeekExtensionEntry |
| 记录页 | QuickCheckPanel / EventRecordForm / VoiceInputSection / RecordTimeline |
| 即时求助页 | ScenarioSelector / ContextCard / ThreeStepResultCard / FollowUpActionBar / BoundaryNote |
| 消息中心 + 周反馈 | MessageList / MessageDetail / PositiveChangeCard / NextWeekDecisionPanel |
| 全局状态管理 | 7 个状态领域（ChildProfile / ActivePlan / Records / Messages / WeeklyFeedback / AISession / Navigation） |

**交付标准**：所有核心页面可渲染并对接后端 API；推送落地与深链跳转正常；离线记录暂存可恢复。

---

### Milestone 5：端到端集成与内测

**目标**：接入真实模型，完成全链路验收，发布 TestFlight 内测版本。

| 任务 | 描述 |
|---|---|
| 真实模型接入 | 替换 mock 为真实 AI 服务商 OpenAPI，调优 Prompt 输出质量 |
| 全链路集成测试 | 注册→建档→记录→AI计划→执行→记录→周反馈→下周决策 完整链路 |
| 边界场景验证 | 网络异常、AI 超时、结构不合格、边界违规、推送失败等异常路径 |
| 性能与成本评估 | AI 调用延迟（首次 < 8s）、Token 消耗、APNs 送达率 |
| TestFlight 内测 | 邀请 10-20 名目标家长试用，收集行为数据与反馈 |
| 迭代调优 | 基于内测反馈调整 Prompt 模板、UI 文案和交互细节 |

**交付标准**：全链路无阻断性缺陷；AI 输出通过人工抽检质量标准；TestFlight 版本稳定可用。

---

## 四、里程碑依赖关系与建议节奏

| 里程碑 | 依赖 | 估算工作量 | 建议顺序 |
|---|---|---|---|
| **MS0** 设计文档 | — | — | ✅ 已完成 |
| **MS1** AI 编排层 | MS0 | 中（约 2-3 周） | **立即开始** |
| **MS2** 后端核心 | MS1 | 大（约 3-4 周） | MS1 完成后 |
| **MS3** 后端闭环 | MS2 | 中（约 2-3 周） | 可与 MS4 部分并行 |
| **MS4** iOS 客户端 | MS2（核心 API）, MS3（推送） | 大（约 4-5 周） | MS2 完成后启动，与 MS3 并行 |
| **MS5** 集成内测 | MS3 + MS4 | 中（约 2-3 周） | 最后阶段 |

> **关键路径**：MS0 → MS1 → MS2 → (MS3 ‖ MS4) → MS5

**当前推荐的下一步行动**：
1. 补充 MS2 剩余任务：账户鉴权（JWT）和周反馈 API
2. 或进入 MS3（后端闭环：推送、异步任务、降级恢复）
3. 或启动 MS4 iOS 客户端开发（MS2 核心 API 已具备对接条件）
