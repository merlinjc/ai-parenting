# 18—48个月幼儿家长辅助型 AI 产品：数据结构草案 V1

## 一、文档目标

本稿承接《关键页面组件拆解 V1》中定义的 7 个全局状态领域和 9 条跨页面写入链路，目的是把前台组件区的数据消费需求，向后端对象结构方向推进一层。换句话说，本稿要回答的核心问题是：**前台组件区消费的每一份数据，在后端以什么结构存在、通过什么接口被获取、在什么时机被写入或更新。**

之所以在组件拆解之后、工程实现之前做这一步，是因为组件拆解只说明了"前台需要什么数据"，但没有说明"这些数据从哪里来、结构长什么样、有哪些字段是后端维护的、哪些是 AI 生成的"。如果直接跳到编码，前端和后端工程师各自理解的数据形状往往不一致，导致联调阶段出现大量返工。

本稿采用领域对象（Domain Object）+ API 消费契约的方式组织，不直接展开到数据库 DDL 或 ORM 映射，保留后续根据实际技术栈调整的空间。

| 本稿解决的问题 | 本稿暂不展开的问题 |
|---|---|
| 把 7 个全局状态领域映射到后端领域对象 | 数据库表结构、索引策略与分区方案 |
| 明确每个领域对象的核心字段与类型方向 | ORM 映射与框架特定注解 |
| 固定前台组件区与后端对象之间的消费关系 | 完整 REST/gRPC 接口定义与错误码体系 |
| 定义 API 消费契约的粒度与返回结构 | 认证鉴权的完整中间件实现 |
| 说明写入时机与状态流转规则 | 分布式事务与跨服务一致性策略 |

## 二、领域对象总览

基于《组件拆解 V1》中的 7 个全局状态领域和《服务架构草案 V1》中的 7 类核心数据对象，本稿将后端数据结构组织为以下领域对象体系。每个领域对象既对应一个后端业务模块，也对应前台至少一个全局状态切片。

| 领域对象 | 对应全局状态领域 | 对应服务架构模块 | 核心职责 |
|---|---|---|---|
| **User** | Navigation（身份部分） | 账户与身份模块 | 用户身份、认证状态、设备绑定 |
| **Child** | ChildProfile | 家庭与儿童档案模块 | 儿童基础信息、年龄阶段、关注主题 |
| **Record** | Records | 观察与记录模块 | 打点记录、关键事件、语音转写结果 |
| **Plan** | ActivePlan | 微计划与任务模块 | 7 天微计划、日任务、完成状态 |
| **DayTask** | ActivePlan（子对象） | 微计划与任务模块 | 单日任务详情、完成状态、观察点 |
| **WeeklyFeedback** | WeeklyFeedback | 微计划与任务模块（延展） | 周反馈内容、决策选项、查看状态 |
| **AISession** | AISession | AI 会话与编排模块 | 即时求助会话、上下文、结构化结果 |
| **Message** | Messages | 通知与消息模块 | 推送消息、处理状态、深链目标 |

## 三、User（用户）

User 是整个系统的身份锚点。所有业务数据都通过 User 关联到具体家庭。当前阶段一个 User 对应一个家庭，一个家庭可以关联多个 Child。

### 3.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 用户唯一标识 |
| **external_id** | String | 否 | 第三方登录标识（Apple ID / 微信等） |
| **auth_provider** | Enum(apple, wechat, email) | 是 | 认证方式 |
| **display_name** | String | 否 | 家长昵称（前台 TopToolBar 展示） |
| **caregiver_role** | Enum(mother, father, grandparent, other) | 否 | 照护者角色 |
| **timezone** | String | 是 | 用户时区（影响推送调度与日期计算） |
| **push_enabled** | Boolean | 是 | 是否开启推送 |
| **created_at** | Timestamp | 是 | 注册时间 |
| **updated_at** | Timestamp | 是 | 最近更新时间 |

### 3.2 关联关系

| 关联对象 | 关系 | 说明 |
|---|---|---|
| **Device** | 一对多 | 一个用户可绑定多台设备（换机场景） |
| **Child** | 一对多 | 一个家庭可关注多个儿童（当前版本先支持单儿童） |

### 3.3 前台消费关系

| 消费的组件区 | 消费字段 | 说明 |
|---|---|---|
| TopToolBar（所有页面） | display_name | 仅首页展示，其他页面展示页面标题 |
| 消息中心 M-2 | push_enabled | 决定是否展示推送开启引导 |

## 四、Device（设备）

Device 对象用于维护推送令牌与设备绑定关系。它不直接被前台组件消费，但支撑消息闭环的送达能力。

### 4.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 设备记录唯一标识 |
| **user_id** | UUID(FK) | 是 | 所属用户 |
| **push_token** | String | 否 | APNs 推送令牌 |
| **platform** | Enum(ios, android) | 是 | 设备平台 |
| **app_version** | String | 是 | 应用版本号 |
| **last_active_at** | Timestamp | 是 | 最近活跃时间 |
| **is_active** | Boolean | 是 | 是否为活跃设备 |

## 五、Child（儿童档案）

Child 是整个业务体系的上下文中心。几乎所有业务对象——Record、Plan、AISession、WeeklyFeedback——都以 Child 为归属锚点。Child 对象的核心价值不在于"存储儿童信息"，而在于为后续所有生成、推荐和反馈提供稳定的阶段与主题上下文。

### 5.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 儿童唯一标识 |
| **user_id** | UUID(FK) | 是 | 所属家庭（用户） |
| **nickname** | String | 是 | 儿童昵称（前台各页面展示） |
| **birth_year_month** | YearMonth | 是 | 出生年月（用于计算月龄与阶段） |
| **age_months** | Integer | 是 | 当前月龄（系统按月自动更新） |
| **stage** | Enum(18_24m, 24_36m, 36_48m) | 是 | 当前年龄阶段（由 age_months 自动映射） |
| **focus_themes** | Array\<Enum\> | 否 | 当前关注主题（语言表达、社交回应、情绪调节等） |
| **risk_level** | Enum(normal, attention, consult) | 是 | 当前风险层级（正常波动 / 重点关注 / 建议咨询）。初始值由 Onboarding 阶段的简短问卷设定为 normal；后续由周反馈生成时 AI 根据累积记录和计划执行情况建议更新，但需经过编排层边界校验后才写入，不允许模型单方面升级到 consult |
| **onboarding_completed** | Boolean | 是 | 是否完成首次引导 |
| **created_at** | Timestamp | 是 | 创建时间 |
| **updated_at** | Timestamp | 是 | 最近更新时间 |

### 5.2 阶段自动映射规则

系统根据 birth_year_month 计算 age_months，再映射到 stage。这一映射在每次用户登录或打开应用时由后端自动刷新，前台不承担阶段判定逻辑。

| 月龄范围 | 映射阶段 |
|---|---|
| 18—24 | 18_24m |
| 24—36 | 24_36m |
| 36—48 | 36_48m |

### 5.3 前台消费关系

| 消费的组件区 | 消费字段 | 说明 |
|---|---|---|
| 首页 H-1 TopToolBar | nickname, age_months | 展示"小明（26个月）" |
| 首页 H-2 FocusCard | stage, focus_themes, risk_level | 展示当前阶段与状态标签 |
| 即时求助 A-3 ContextCard | age_months, stage, focus_themes | AI 上下文透明展示 |
| 记录页 R-2 QuickCheckPanel | focus_themes | 用于动态生成打点选项的输入之一 |

## 六、Record（观察记录）

Record 是系统中最高频写入的对象。它承载了家长日常观察的所有证据，并作为微计划生成、周反馈聚合和即时求助上下文的主要输入来源。

### 6.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 记录唯一标识 |
| **child_id** | UUID(FK) | 是 | 所属儿童 |
| **type** | Enum(quick_check, event, voice) | 是 | 记录类型：快速打点 / 关键事件 / 语音转写 |
| **tags** | Array\<String\> | 否 | 打点标签集合（快速打点类型使用） |
| **content** | String | 否 | 事件描述文本（关键事件类型使用） |
| **voice_url** | String | 否 | 语音文件地址（语音类型使用） |
| **transcript** | String | 否 | 语音转写结果 |
| **scene** | Enum(dressing, going_out, eating, meeting_people, playing, sleeping, other) | 否 | 场景标签 |
| **time_of_day** | Enum(morning, afternoon, evening, night) | 否 | 时间段标签 |
| **theme** | Enum(language, social, emotion, motor, cognition, self_care) | 否 | 关联主题 |
| **source_plan_id** | UUID(FK) | 否 | 来源计划 ID（从计划页"完成后去记录"跳转时自动关联） |
| **source_session_id** | UUID(FK) | 否 | 来源求助会话 ID（从即时求助"补记为记录"跳转时自动关联） |
| **synced_to_plan** | Boolean | 是 | 是否已被计划模块引用 |
| **created_at** | Timestamp | 是 | 记录时间 |

### 6.2 写入时机与来源

| 写入来源 | 对应前台组件区 | 写入字段 |
|---|---|---|
| 快速打点提交 | R-2 QuickCheckPanel | type=quick_check, tags |
| 关键事件提交 | R-3 EventRecordForm | type=event, content, scene, time_of_day, theme |
| 语音录入完成 | R-4 VoiceInputSection | type=voice, voice_url, transcript |
| 从计划页跳转记录 | P-5 → R-2 | 自动填入 source_plan_id |
| 从即时求助补记 | A-5 → R-2/R-3 | 自动填入 source_session_id |

### 6.3 前台消费关系

| 消费的组件区 | 消费方式 | 说明 |
|---|---|---|
| 首页 H-4 RecentRecordSummary | 最近 1—2 条记录摘要 | 读取最新记录的 content/tags + synced_to_plan |
| 记录页 R-5 RecordTimeline | 按时间倒序的记录列表 | 分页加载，初始取最近 7 天 |
| 即时求助 A-3 ContextCard | 最近记录关键词 | 提取最近 3 条记录的 tags/theme 作为 AI 上下文 |

## 七、Plan（微计划）

Plan 是系统中结构最复杂的领域对象，因为它既是 AI 生成的产物，又是前台消费量最大的数据来源。一个 Plan 对应一个完整的 7 天微计划周期，包含 7 个 DayTask 子对象。

### 7.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 计划唯一标识 |
| **child_id** | UUID(FK) | 是 | 所属儿童 |
| **version** | Integer | 是 | 计划版本号（同一儿童可有多个历史计划） |
| **status** | Enum(active, completed, superseded) | 是 | 计划状态：活跃 / 已完成 / 已被新计划替代 |
| **title** | String | 是 | 计划标题（AI 生成） |
| **primary_goal** | String | 是 | 本周主目标文本（AI 生成） |
| **focus_theme** | Enum | 是 | 本周焦点主题 |
| **priority_scenes** | Array\<String\> | 是 | 优先场景列表（AI 生成） |
| **stage** | Enum(18_24m, 24_36m, 36_48m) | 是 | 计划对应的年龄阶段 |
| **risk_level_at_creation** | Enum(normal, attention, consult) | 是 | 创建时的风险层级 |
| **start_date** | Date | 是 | 计划起始日期 |
| **end_date** | Date | 是 | 计划结束日期 |
| **current_day** | Integer(1-7) | 是 | 当前进行到第几天 |
| **completion_rate** | Float(0-1) | 是 | 整体完成率 |
| **observation_candidates** | Array\<ObservationCandidate\> | 是 | 快速打点候选列表（随计划返回，供记录页 R-2 消费） |
| **next_week_context** | String | 否 | 下周计划生成上下文（由即时求助"加入本周关注"回写） |
| **next_week_direction** | Enum(continue, lower_difficulty, change_focus) | 否 | 下周方向（由周反馈 F-4 决策回写） |
| **weekend_review_prompt** | String | 否 | Day 6-7 的复盘引导文本（AI 生成时写入） |
| **conservative_note** | String | 否 | 如果本周困难时的保守路径预置文本（AI 生成时写入） |
| **ai_generation_id** | UUID(FK) | 是 | 生成此计划的 AI 会话 ID |
| **created_at** | Timestamp | 是 | 创建时间 |
| **updated_at** | Timestamp | 是 | 最近更新时间 |

### 7.2 ObservationCandidate（打点候选项）

这是 Plan 的嵌套值对象，随计划一起返回，不独立存储。它解决的是《组件拆解 V1》中审阅指出的"QuickCheckPanel 打点选项从哪来"的问题。

| 字段名 | 类型方向 | 说明 |
|---|---|---|
| **id** | String | 候选项唯一标识 |
| **text** | String | 候选项显示文本（如"今天完成了计划动作"） |
| **theme** | Enum | 关联主题 |
| **default_selected** | Boolean | 是否默认选中 |

### 7.3 前台消费关系

| 消费的组件区 | 消费字段 | 说明 |
|---|---|---|
| 首页 H-2 FocusCard | title, primary_goal, focus_theme, priority_scenes, risk_level_at_creation | 当前周焦点展示 |
| 首页 H-3 TodayTaskCard | 当天 DayTask 的 title + summary | 今日任务摘要 |
| 计划页 P-2 WeekOverviewCard | title, primary_goal, priority_scenes, current_day | 本周主线信息 |
| 计划页 P-3 DaySelector | 7 个 DayTask 的 completion_status | 各天完成状态 |
| 记录页 R-2 QuickCheckPanel | observation_candidates | 动态打点选项 |

## 八、DayTask（日任务）

DayTask 是 Plan 的子对象，每个 Plan 包含固定 7 个 DayTask。它承载了单日的具体执行内容。

### 8.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 日任务唯一标识 |
| **plan_id** | UUID(FK) | 是 | 所属计划 |
| **day_number** | Integer(1-7) | 是 | 第几天 |
| **main_exercise_title** | String | 是 | 主练习标题（AI 生成） |
| **main_exercise_description** | String | 是 | 主练习说明（AI 生成） |
| **natural_embed_title** | String | 是 | 自然嵌入标题（AI 生成） |
| **natural_embed_description** | String | 是 | 自然嵌入说明（AI 生成） |
| **demo_script** | String | 是 | 示范话术（AI 生成） |
| **observation_point** | String | 是 | 观察点文本（AI 生成） |
| **completion_status** | Enum(pending, executed, partial, needs_record) | 是 | 完成状态 |
| **completed_at** | Timestamp | 否 | 完成时间 |

### 8.2 写入时机

| 写入来源 | 对应前台组件区 | 写入字段 |
|---|---|---|
| AI 生成计划时批量创建 | 系统内部 | 所有 AI 生成字段 |
| 家长选中完成状态 | P-5 CompletionPanel | completion_status, completed_at |

### 8.3 前台消费关系

| 消费的组件区 | 消费字段 | 说明 |
|---|---|---|
| 计划页 P-4 DailyTaskPanel | main_exercise_*, natural_embed_*, demo_script, observation_point | 当日任务完整内容 |
| 计划页 P-5 CompletionPanel | completion_status | 当日完成状态 |
| 首页 H-3 TodayTaskCard | main_exercise_title, natural_embed_title, completion_status | 今日任务摘要 |

## 九、WeeklyFeedback（周反馈）

WeeklyFeedback 是 Plan 的延展产物。一个 Plan 完成 7 天周期后，系统基于该周记录和计划执行情况由 AI 生成一份周反馈。它不仅是回顾性文档，更是下一个 Plan 生成的输入。

### 9.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 周反馈唯一标识 |
| **plan_id** | UUID(FK) | 是 | 关联计划 |
| **child_id** | UUID(FK) | 是 | 所属儿童 |
| **status** | Enum(generating, ready, viewed, decided) | 是 | 状态：生成中 / 已就绪 / 已查看 / 已决策 |
| **positive_changes** | Array\<FeedbackItem\> | 是 | 积极变化列表（AI 生成） |
| **opportunities** | Array\<FeedbackItem\> | 是 | 仍需机会方向列表（AI 生成） |
| **summary_text** | String | 是 | 整体摘要文本（AI 生成） |
| **decision_options** | Array\<DecisionOption\> | 是 | 下周决策选项（AI 生成） |
| **selected_decision** | Enum(continue, lower_difficulty, change_focus) | 否 | 家长选择的下周方向 |
| **conservative_path_note** | String | 是 | 更保守路径说明文本（AI 生成） |
| **record_count_this_week** | Integer | 是 | 本周记录条数（生成时快照） |
| **completion_rate_this_week** | Float(0-1) | 是 | 本周计划完成率（生成时快照） |
| **ai_generation_id** | UUID(FK) | 是 | 生成此反馈的 AI 会话 ID |
| **created_at** | Timestamp | 是 | 生成时间 |
| **viewed_at** | Timestamp | 否 | 首次查看时间 |
| **decided_at** | Timestamp | 否 | 决策时间 |

### 9.2 嵌套值对象

**FeedbackItem**

| 字段名 | 类型方向 | 说明 |
|---|---|---|
| **title** | String | 变化项标题 |
| **description** | String | 变化项说明 |
| **supporting_evidence** | String | 支撑证据文本摘要（AI 从记录中提取，前台 F-2 PositiveChangeCard 的 evidenceText 消费此字段） |
| **supporting_records** | Array\<UUID\> | 支撑该结论的记录 ID 列表 |

**DecisionOption**

| 字段名 | 类型方向 | 说明 |
|---|---|---|
| **id** | String | 选项标识 |
| **text** | String | 选项显示文本 |
| **value** | Enum(continue, lower_difficulty, change_focus) | 选项值 |
| **rationale** | String | 选择该选项的理由说明（AI 生成，前台 F-4 可展示为选项副文本） |

### 9.3 前台消费关系

| 消费的组件区 | 消费字段 | 说明 |
|---|---|---|
| 周反馈 F-2 PositiveChangeCard | positive_changes | 积极变化展示 |
| 周反馈 F-3 OpportunityCard | opportunities | 仍需机会展示 |
| 周反馈 F-4 NextWeekDecisionPanel | decision_options, selected_decision | 决策选项与当前选择 |
| 周反馈 F-5 ConservativePathNote | conservative_path_note | 保守路径说明 |
| 首页 H-5 PendingReturnCard | status（是否为 ready 且未 viewed） | 待处理回流事项 |
| 计划页 P-6 WeekExtensionEntry | status（是否存在已生成的周反馈） | 入口展示 |

## 十、AISession（AI 会话）

AISession 对象承载每一次 AI 交互的完整生命周期。它不仅用于即时求助场景，也用于微计划生成和周反馈生成。不同场景的 AISession 通过 session_type 区分。

### 10.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 会话唯一标识 |
| **child_id** | UUID(FK) | 是 | 所属儿童 |
| **session_type** | Enum(instant_help, plan_generation, weekly_feedback) | 是 | 会话类型 |
| **status** | Enum(pending, processing, completed, failed, degraded) | 是 | 会话状态 |
| **input_scenario** | String | 否 | 即时求助：用户选择的问题场景 |
| **input_text** | String | 否 | 即时求助：用户自由输入文本 |
| **context_snapshot** | ContextSnapshot | 是 | 上下文快照（AI 编排层使用） |
| **result** | AIResult(JSONB) | 否 | 结构化结果（参见《AI 输出结构草案》）。存储为 JSONB 列，具体 schema 由 session_type 决定 |
| **error_info** | String | 否 | 失败信息 |
| **degraded_result** | AIResult | 否 | 降级结果（失败时的保守方案） |
| **model_provider** | String | 是 | 使用的模型供应商标识 |
| **model_version** | String | 是 | 使用的模型版本 |
| **prompt_template_id** | String | 是 | 使用的 Prompt 模板标识 |
| **latency_ms** | Integer | 否 | 响应延迟（毫秒） |
| **created_at** | Timestamp | 是 | 会话创建时间 |
| **completed_at** | Timestamp | 否 | 会话完成时间 |

### 10.2 ContextSnapshot（上下文快照）

这是 AISession 的嵌套值对象，记录 AI 编排层在请求时实际使用的上下文。它的价值在于支持审计回溯——当需要理解"AI 为什么给出这个建议"时，可以从这里还原当时的输入。

| 字段名 | 类型方向 | 说明 |
|---|---|---|
| **child_age_months** | Integer | 请求时的儿童月龄 |
| **child_stage** | Enum | 请求时的年龄阶段 |
| **child_focus_themes** | Array\<Enum\> | 请求时的关注主题 |
| **child_risk_level** | Enum | 请求时的风险层级 |
| **active_plan_id** | UUID | 请求时的活跃计划 ID |
| **active_plan_day** | Integer | 请求时的计划进行天数 |
| **recent_record_ids** | Array\<UUID\> | 请求时引用的最近记录 ID 列表 |
| **recent_record_keywords** | Array\<String\> | 提取的关键词摘要 |

### 10.3 前台消费关系

| 消费的组件区 | 消费字段 | 说明 |
|---|---|---|
| 即时求助 A-3 ContextCard | context_snapshot 中的阶段、计划、记录关键词 | 上下文透明展示 |
| 即时求助 A-4 ThreeStepResultCard | result（即时求助类型的结构化结果） | 三步支持结果展示 |
| 即时求助 A-5 FollowUpActionBar | result + session_type + status | 后续动作可用性判断 |

## 十一、Message（消息）

Message 对象承载系统向用户发送的所有触达消息。消息不仅是一条通知文本，更是一个带有目标页面、处理状态和回流追踪能力的业务对象。

### 11.1 核心字段

| 字段名 | 类型方向 | 必填 | 说明 |
|---|---|---|---|
| **id** | UUID | 是 | 消息唯一标识 |
| **user_id** | UUID(FK) | 是 | 目标用户 |
| **child_id** | UUID(FK) | 否 | 关联儿童（部分消息可能不绑定特定儿童） |
| **type** | Enum(plan_reminder, record_prompt, weekly_feedback_ready, risk_alert, system) | 是 | 消息类型 |
| **title** | String | 是 | 消息标题 |
| **body** | String | 是 | 消息正文 |
| **summary** | String | 是 | 摘要文本（前台列表展示） |
| **target_page** | String | 否 | 深链目标页标识 |
| **target_params** | JSON | 否 | 深链目标参数 |
| **requires_preview** | Boolean | 是 | 是否需要先预览再跳转（对应消息展开规则） |
| **read_status** | Enum(unread, read, processed) | 是 | 处理状态 |
| **push_status** | Enum(pending, sent, delivered, failed) | 是 | 推送送达状态 |
| **push_sent_at** | Timestamp | 否 | 推送发送时间 |
| **push_delivered_at** | Timestamp | 否 | 推送送达时间 |
| **clicked_at** | Timestamp | 否 | 用户点击时间 |
| **created_at** | Timestamp | 是 | 消息创建时间 |

### 11.2 消息类型与展开规则映射

这里直接落实《组件拆解 V1》中明确的消息展开规则：

| 消息类型 | requires_preview | 说明 |
|---|---|---|
| plan_reminder | false | 目标动作明确，直接深链到计划页当日任务 |
| record_prompt | false | 目标动作明确，直接深链到记录页 |
| weekly_feedback_ready | true | 需要预览正文后再跳转到周反馈详情 |
| risk_alert | true | 需要预览正文后再决策 |
| system | true | 系统通知，预览后可关闭 |

### 11.3 前台消费关系

| 消费的组件区 | 消费字段 | 说明 |
|---|---|---|
| TopToolBar（所有页面） | 未读消息计数（read_status=unread 的 count） | 未读徽标 |
| 首页 H-5 PendingReturnCard | 最近未处理消息摘要 | 待处理回流展示 |
| 消息中心 M-2 MessageList | 消息列表（排序：未处理优先，同状态内按时间倒序） | 消息列表 |
| 消息中心 M-3 MessageDetail | 单条消息完整内容 | 消息详情预览 |
| 消息中心 M-4 ProcessingStatus | 各状态消息计数 | 处理状态概览 |

## 十二、API 消费契约概览

基于以上领域对象定义，以下按前台页面组织 API 消费契约。每个契约说明前台需要什么数据、以什么粒度获取、在什么时机触发。本节不展开到 URL 路径与参数格式，而是固定"前台期望的数据形状"。

### 12.1 首页 API 契约

首页采用聚合接口模式——一次请求返回首页所有组件区需要的数据，避免前台发起多个并行请求。当前版本一个用户只关联一个活跃儿童，child_id 由后端根据登录用户自动选取唯一活跃 Child；后续支持多儿童时，前台需要在请求参数中显式传入 child_id。

**GET /home/summary**

| 返回字段块 | 包含数据 | 消费组件区 |
|---|---|---|
| **child** | nickname, age_months, stage, risk_level | H-1 TopToolBar, H-2 FocusCard |
| **active_plan** | title, primary_goal, focus_theme, priority_scenes, current_day | H-2 FocusCard |
| **today_task** | main_exercise_title, natural_embed_title, completion_status | H-3 TodayTaskCard |
| **recent_records** | 最近 2 条记录的 content/tags, synced_to_plan | H-4 RecentRecordSummary |
| **pending_messages** | 最近 2 条未处理消息的 type, summary, target_page | H-5 PendingReturnCard |
| **unread_count** | 未读消息总数 | H-1 TopToolBar 徽标 |

### 12.2 计划页 API 契约

计划页初始加载获取完整计划对象（含 7 个 DayTask），后续日切换由前台本地完成，无需额外请求。

**GET /plans/active**

| 返回字段块 | 包含数据 | 消费组件区 |
|---|---|---|
| **plan** | 完整 Plan 对象（含 title, primary_goal, priority_scenes, current_day, observation_candidates） | P-2, P-3, P-6 |
| **day_tasks** | 7 个 DayTask 的完整数据 | P-3, P-4, P-5 |
| **weekly_feedback_status** | 是否有已生成的周反馈 | P-6 |

**POST /plans/{plan_id}/days/{day_number}/completion**

| 请求字段 | 说明 |
|---|---|
| **completion_status** | 选中的完成状态 |

| 返回字段 | 说明 |
|---|---|
| **updated_day_task** | 更新后的 DayTask 对象 |
| **updated_plan** | 更新后的 Plan 完成率 |

### 12.3 记录页 API 契约

**GET /records?child_id={id}&limit=20&before={cursor}**

| 返回字段块 | 包含数据 | 消费组件区 |
|---|---|---|
| **records** | 记录列表（按时间倒序） | R-5 RecordTimeline |
| **has_more** | 是否有更多历史记录 | R-5 分页加载 |

**GET /plans/active/observation-candidates**

| 返回字段块 | 包含数据 | 消费组件区 |
|---|---|---|
| **candidates** | 当前计划的打点候选项列表 | R-2 QuickCheckPanel |

**POST /records**

| 请求字段 | 说明 |
|---|---|
| **type** | 记录类型 |
| **tags** | 打点标签（quick_check 类型） |
| **content** | 事件描述（event 类型） |
| **scene, time_of_day, theme** | 场景、时间、主题标签 |
| **source_plan_id** | 可选，来源计划 |
| **source_session_id** | 可选，来源求助会话 |

| 返回字段 | 说明 |
|---|---|
| **record** | 创建成功的 Record 对象 |

**语音记录的上传流程**：语音记录采用分步上传方式。前台先调用 **POST /records/voice/upload-url** 获取预签名上传 URL，将音频文件直传至对象存储；上传完成后，前台将返回的 voice_url 和其他字段一起通过 POST /records（type=voice）提交。后端收到后异步触发语音转写任务，转写完成后回写 Record.transcript 字段，并通过轮询或推送通知前台更新。

### 12.4 即时求助 API 契约

**POST /ai/instant-help**

| 请求字段 | 说明 |
|---|---|
| **child_id** | 儿童 ID |
| **scenario** | 选择的问题场景（可选） |
| **input_text** | 自由输入文本（可选） |
| **plan_id** | 当前活跃计划 ID（可选） |

| 返回字段 | 说明 |
|---|---|
| **session** | AISession 对象（含 context_snapshot 和 result） |

由于 AI 请求可能耗时较长，建议采用以下策略：

1. **乐观返回**：先返回 session（status=processing），前台展示骨架屏。
2. **轮询或推送更新**：前台通过短轮询（GET /ai/sessions/{id}）或 WebSocket 获取结果。
3. **超时降级**：超过阈值后返回 degraded_result。

### 12.5 消息中心 API 契约

**GET /messages?limit=20&before={cursor}**

| 返回字段块 | 包含数据 | 消费组件区 |
|---|---|---|
| **messages** | 消息列表（未处理优先，时间倒序） | M-2 MessageList |
| **unread_count** | 未读总数 | M-1 TopToolBar, M-4 ProcessingStatus |
| **has_more** | 是否有更多消息 | M-2 分页 |

**PATCH /messages/{id}**

| 请求字段 | 说明 |
|---|---|
| **read_status** | 更新为 read 或 processed |

### 12.6 周反馈 API 契约

**GET /weekly-feedbacks/{id}**

| 返回字段块 | 包含数据 | 消费组件区 |
|---|---|---|
| **feedback** | 完整 WeeklyFeedback 对象 | F-2, F-3, F-4, F-5 |

**POST /weekly-feedbacks/{id}/decision**

| 请求字段 | 说明 |
|---|---|
| **selected_decision** | 选择的下周方向 |

| 返回字段 | 说明 |
|---|---|
| **updated_feedback** | 更新后的 WeeklyFeedback 对象 |

## 十三、跨页面写入链路的数据结构映射

为了与《组件拆解 V1》中的跨页面写入链路总表完全对齐，以下逐条说明每条链路在数据结构层面的实现路径。

| 链路 | 源组件区操作 | 数据结构操作 | 影响的目标数据 |
|---|---|---|---|
| 计划→完成 | P-5 选中"已执行" | PATCH DayTask.completion_status | Plan.completion_rate 重算；首页聚合接口刷新 |
| 计划→记录 | P-5 "完成后去记录" | 导航参数传递 source_plan_id + 预填 tags | 新建 Record 时自动关联 Plan |
| 计划→求助 | P-5 "现在求助" | 导航参数传递 plan_id | AISession.context_snapshot 引用 Plan |
| 记录→全局 | R-2/R-3/R-4 提交 | POST Record | 首页聚合接口中的 recent_records 刷新 |
| 求助→记录 | A-5 "补记为记录" | POST Record（含 source_session_id） | RecordTimeline 新增条目 |
| 求助→关注 | A-5 "加入本周关注" | PATCH Plan.next_week_context | 下周计划生成时 AI 引用 |
| 反馈→方向 | F-4 选中决策 | POST WeeklyFeedback.selected_decision | Plan.next_week_direction 同步更新 |
| 消息→已读 | M-2/M-3 操作 | PATCH Message.read_status | 首页 unread_count 刷新 |
| 进入层→初始化 | 完成最小必填 | POST Child + 触发首个 Plan 生成 | 所有页面首次渲染数据就位 |

## 十四、数据生命周期与清理策略

| 对象 | 保留策略 | 说明 |
|---|---|---|
| **User** | 长期保留 | 除非用户主动注销 |
| **Child** | 长期保留 | 年龄超过 48 个月后标记为归档 |
| **Record** | 长期保留 | 历史记录是产品核心价值 |
| **Plan** | 长期保留（superseded 计划降级存储） | 历史计划支持回看 |
| **DayTask** | 跟随 Plan 生命周期 | 与所属 Plan 一同管理 |
| **WeeklyFeedback** | 长期保留 | 支持纵向趋势回看 |
| **AISession** | 90 天活跃保留，之后归档摘要 | 完整上下文和结果保留 90 天，之后仅保留 context_snapshot 和 result 摘要 |
| **Message** | 已处理消息 30 天后归档 | 未处理消息不自动归档 |
| **Device** | 6 个月无活跃后清理 | 避免向过期设备推送 |

## 十五、结论

到这一版为止，7 个全局状态领域已经被映射到 9 个后端领域对象（User、Device、Child、Record、Plan、DayTask、WeeklyFeedback、AISession、Message），每个对象都有明确的核心字段、写入时机和前台消费关系。同时，API 消费契约已按页面维度固定了数据形状和交互模式，跨页面写入链路也逐条映射到了具体的数据操作。

| 结论项 | 结果 |
|---|---|
| **领域对象数** | 9 个（含 Device） |
| **嵌套值对象数** | 4 个（ObservationCandidate、FeedbackItem、DecisionOption、ContextSnapshot） |
| **API 契约数** | 6 组（首页聚合、计划、记录、即时求助、消息、周反馈） |
| **跨页面写入链路映射** | 9 条全部覆盖 |
| **与组件拆解 V1 的对齐** | 所有组件区的消费字段均有对应后端来源 |

| 推荐下一步 | 产出目标 |
|---|---|
| **AI 输出结构草案 V1** | 固定微计划、即时求助、周反馈三类 AI 结果的结构化输出格式 |
| **通用组件接口定义** | 为 9 个通用组件补充伪类型签名 |
| **数据库表结构 V1** | 把领域对象映射到具体 DDL |
