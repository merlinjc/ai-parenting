# 18—48个月幼儿家长辅助型 AI 产品：AI 输出结构草案 V1

## 一、文档目标

本稿承接《数据结构草案 V1》中定义的 AISession 对象和《关键页面组件拆解 V1》中三类 AI 驱动的页面组件区（即时求助三步结果卡、微计划日任务面板、周反馈内容卡），目的是把 AI 编排层的输出从"自由格式长文本"推进到"**结构化、可展示、可回写、可审查**"的标准格式。

这一步的必要性在于：前台组件区已经定义了固定的数据消费结构（三步式结果、7 日计划日任务、积极变化+机会+决策），如果 AI 输出没有明确的字段约束和格式规范，编排层就无法稳定地将模型返回解析成前台可直接渲染的数据对象。同时，结构化输出也是边界校验、降级处理和审计回溯的前提。

| 本稿解决的问题 | 本稿暂不展开的问题 |
|---|---|
| 固定三类 AI 输出的字段结构与类型约束 | 具体 Prompt 模板的完整文本 |
| 定义输出校验规则与降级策略 | 模型选型与供应商比较 |
| 说明结构化输出与前台组件区的映射关系 | Fine-tuning 策略与训练数据准备 |
| 明确非诊断化边界在输出结构中的检查点 | 多语言适配与国际化 |
| 为编排层实现提供可直接对照的规格 | Token 成本优化与缓存策略 |

## 二、AI 输出结构的设计原则

在定义具体结构之前，需要先固定几条贯穿三类输出的通用原则。

**第一，输出必须是结构化 JSON，不是自由文本。** AI 编排层在收到模型返回后，必须将其解析为固定 schema 的 JSON 对象。如果模型返回无法被解析，则判定为结构不合格，触发重试或降级。这意味着 Prompt 模板中必须包含明确的输出格式约束，模型选型也需要优先考虑支持 JSON mode 或 function calling 的供应商。

**第二，每个输出字段都必须有对应的前台消费者。** 不生成前台不消费的冗余字段。这既避免了过度生成导致的成本浪费，也避免了前台因为不知道如何渲染某个字段而产生的展示混乱。

**第三，非诊断化边界必须在结构层而非展示层检查。** 也就是说，不能等 AI 输出到了前台才发现"这句话像诊断"。编排层在解析结构化输出时，就应该对关键文本字段进行边界检查。检查不通过的字段应该被替换为保守表达或触发人工审核。

**第四，每类输出都必须有完整的降级版本。** 当模型超时、结构不合格或边界检查不通过时，系统应能返回一个内容安全但信息量较少的降级结果，而不是让前台显示空白或错误。

**第五，输出结构包含元数据字段，支持审计回溯。** 每个输出都应记录使用的 Prompt 模板版本、模型版本和边界检查结果，便于后续质量回溯。

| 设计原则 | 对输出结构的直接要求 |
|---|---|
| **结构化 JSON** | 模型返回必须可被解析为固定 schema |
| **字段对齐前台** | 每个字段都有明确的组件区消费者 |
| **结构层边界检查** | 编排层解析时检查非诊断化边界 |
| **完整降级版本** | 每类输出都有安全的降级替代方案 |
| **元数据可审计** | 输出包含模板版本、模型版本和检查结果 |

## 三、即时求助输出结构（InstantHelpResult）

即时求助是用户体感上最"AI"的功能。用户在即时求助页选择问题场景或输入描述后，系统需要返回一个结构化的"三步支持结果"，直接被前台 A-4 ThreeStepResultCard 消费。

### 3.1 输出 Schema

```
InstantHelpResult {
  // —— 三步支持结构（前台核心消费区） ——
  step_one: StepContent        // 先说什么
  step_two: StepContent        // 接着做什么
  step_three: StepContent      // 没接住怎么办

  // —— 场景理解摘要 ——
  scenario_summary: String     // 一句话概括 AI 对当前场景的理解

  // —— 后续动作建议 ——
  suggest_record: Boolean      // 是否建议"补记为记录"
  suggest_add_focus: Boolean   // 是否建议"加入本周关注"
  suggest_consult_prep: Boolean // 是否建议"查看咨询准备"
  consult_prep_reason: String? // 如果建议咨询准备，简述原因

  // —— 边界说明 ——
  boundary_note: String        // 非诊断化提示文本

  // —— 元数据 ——
  metadata: OutputMetadata
}

StepContent {
  title: String                // 步骤标题（如"先稳住自己"）
  body: String                 // 步骤正文（2-4句话）
  example_script: String?      // 可选：示范话术
}

OutputMetadata {
  prompt_template_version: String
  model_provider: String
  model_version: String
  boundary_check_passed: Boolean
  boundary_check_flags: Array<String>   // 被标记的检查项
  generation_timestamp: Timestamp
  latency_ms: Integer
}
```

### 3.2 字段约束

| 字段 | 约束 | 说明 |
|---|---|---|
| **step_one.title** | 最长 20 字符 | 高压时刻需要极短标题 |
| **step_one.body** | 最长 200 字符 | 2-4 句话 |
| **step_two.title** | 最长 20 字符 | |
| **step_two.body** | 最长 300 字符 | 可以比第一步稍长 |
| **step_three.title** | 最长 20 字符 | |
| **step_three.body** | 最长 300 字符 | |
| **example_script** | 最长 100 字符 | 必须是家长可以直接说出口的话 |
| **scenario_summary** | 最长 80 字符 | 用于 ContextCard 辅助展示 |
| **boundary_note** | 最长 150 字符 | 固定格式的非诊断化提示 |

### 3.3 与前台组件区的映射

| 前台组件区 | 消费字段 | 渲染方式 |
|---|---|---|
| A-4 ThreeStepResultCard 第一步 | step_one.title, step_one.body, step_one.example_script | 标题 + 正文 + 可选话术卡 |
| A-4 ThreeStepResultCard 第二步 | step_two.title, step_two.body, step_two.example_script | 同上 |
| A-4 ThreeStepResultCard 第三步 | step_three.title, step_three.body, step_three.example_script | 同上 |
| A-5 FollowUpActionBar | suggest_record, suggest_add_focus, suggest_consult_prep | 控制三个按钮的可见性与强调程度 |
| A-6 BoundaryNote | boundary_note | 固定位置展示 |

### 3.4 非诊断化边界检查点

编排层在生成 InstantHelpResult 后，必须对以下文本字段执行边界检查：

| 检查项 | 检查规则 | 不通过时处理 |
|---|---|---|
| **诊断性标签** | step_*.body 和 step_*.title 中不得包含疾病名称、诊断代码或明确病理判断 | 替换为保守表达 |
| **治疗承诺** | 不得出现"治愈""矫正""训练能解决"等暗示治疗效果的表述 | 替换为"帮助""支持""给更多机会" |
| **责备表达** | 不得出现暗示家长做错了的表述 | 替换为鼓励性表达 |
| **过度确定性** | 不得出现"一定""肯定""必须"等绝对化判断 | 替换为"可以试试""通常""很多家庭发现" |
| **字段完整性** | 三个 step 均不得为空 | 触发重试或降级 |

### 3.5 降级版本

当模型超时、结构不合格或边界检查多次不通过时，返回以下降级结果：

```
InstantHelpResult(degraded) {
  step_one: {
    title: "先稳住自己",
    body: "深呼吸，提醒自己这个阶段的孩子出现这类反应是常见的。你的在场本身就是支持。",
    example_script: null
  },
  step_two: {
    title: "简短回应",
    body: "用简单、平静的话回应孩子当前的状态，不需要马上解决问题。",
    example_script: "我看到你了，我在这里。"
  },
  step_three: {
    title: "给双方空间",
    body: "如果当下没有缓解，可以先退一步，等情绪过去后再回来。这不是放弃，是给双方恢复的时间。",
    example_script: null
  },
  scenario_summary: "当前场景需要的是稳定和耐心",
  suggest_record: true,
  suggest_add_focus: false,
  suggest_consult_prep: false,
  boundary_note: "以上为通用支持建议。如果类似情况反复出现且让你持续担心，建议预约一次专业咨询。",
  metadata: { ..., boundary_check_passed: true }
}
```

## 四、微计划生成输出结构（PlanGenerationResult）

微计划生成是系统中结构最复杂的 AI 输出。一次生成需要产出一个完整的 7 天计划，包含 Plan 级别的元信息和 7 个 DayTask 的详细内容。

### 4.1 输出 Schema

```
PlanGenerationResult {
  // —— 计划元信息 ——
  title: String                        // 计划标题
  primary_goal: String                 // 本周主目标
  focus_theme: Enum                    // 焦点主题
  priority_scenes: Array<String>       // 优先场景列表（2-3 个）
  
  // —— 七日任务 ——
  day_tasks: Array<DayTaskContent>[7]  // 固定 7 个

  // —— 快速打点候选 ——
  observation_candidates: Array<ObservationCandidateContent>  // 5-8 个

  // —— 周末复盘引导 ——
  weekend_review_prompt: String        // Day 6-7 的复盘引导文本

  // —— 保守路径预置 ——
  conservative_note: String            // 如果本周困难，这段文本预置到周反馈

  // —— 元数据 ——
  metadata: OutputMetadata
}

DayTaskContent {
  day_number: Integer(1-7)
  main_exercise_title: String          // 主练习标题
  main_exercise_description: String    // 主练习说明
  natural_embed_title: String          // 自然嵌入标题
  natural_embed_description: String    // 自然嵌入说明
  demo_script: String                  // 示范话术
  observation_point: String            // 观察点
}

ObservationCandidateContent {
  id: String                           // 候选项标识
  text: String                         // 显示文本
  theme: Enum                          // 关联主题
  default_selected: Boolean            // 是否默认选中
}
```

### 4.2 字段约束

| 字段 | 约束 | 说明 |
|---|---|---|
| **title** | 最长 30 字符 | 计划卡片标题 |
| **primary_goal** | 最长 100 字符 | 一句话主目标 |
| **priority_scenes** | 2-3 个，每个最长 15 字符 | 场景标签 |
| **day_tasks** | 必须恰好 7 个 | 不能多也不能少 |
| **main_exercise_title** | 最长 25 字符 | |
| **main_exercise_description** | 最长 300 字符 | |
| **natural_embed_title** | 最长 25 字符 | |
| **natural_embed_description** | 最长 300 字符 | |
| **demo_script** | 最长 150 字符 | 必须是家长可以直接说出口的话 |
| **observation_point** | 最长 150 字符 | |
| **observation_candidates** | 5-8 个 | |
| **weekend_review_prompt** | 最长 200 字符 | |
| **conservative_note** | 最长 200 字符 | |

### 4.3 与数据结构的映射

PlanGenerationResult 不会被直接存储为一个完整对象。编排层完成结构化校验后，应将其拆分写入 Plan 和 DayTask 两个领域对象。

| PlanGenerationResult 字段 | 写入目标 | 写入字段 |
|---|---|---|
| title, primary_goal, focus_theme, priority_scenes | Plan | 同名字段 |
| observation_candidates | Plan.observation_candidates | 嵌套值对象 |
| weekend_review_prompt | Plan（扩展字段） | 周末复盘引导 |
| conservative_note | Plan（扩展字段） | 保守路径预置 |
| day_tasks[n] | DayTask | 按 day_number 逐条写入 |

### 4.4 与前台组件区的映射

| 前台组件区 | 消费的原始输出字段 | 经过数据结构后的消费路径 |
|---|---|---|
| P-2 WeekOverviewCard | title, primary_goal, priority_scenes | Plan.title, Plan.primary_goal, Plan.priority_scenes |
| P-4 DailyTaskPanel | day_tasks[n] 全部字段 | DayTask.* |
| R-2 QuickCheckPanel | observation_candidates | Plan.observation_candidates |
| 首页 H-2 FocusCard | title, focus_theme | Plan.title, Plan.focus_theme |
| 首页 H-3 TodayTaskCard | day_tasks[current_day] 的标题字段 | DayTask.main_exercise_title 等 |

### 4.5 非诊断化边界检查点

| 检查项 | 检查范围 | 不通过时处理 |
|---|---|---|
| **诊断性标签** | title, primary_goal, all day_task descriptions | 替换为支持性表达 |
| **训练化表达** | demo_script, main_exercise_description | 不使用"训练""矫正"，替换为"练习""游戏""互动" |
| **过度量化目标** | primary_goal, observation_point | 不出现"每天必须 N 次"类绝对量化 |
| **Day 1-7 连贯性** | day_tasks 整体 | 7 天之间难度应渐进，不得跳跃或重复 |
| **候选项有效性** | observation_candidates | 文本不得过长、不得包含诊断性表达 |

### 4.6 降级版本

微计划生成失败时，不能返回完全空白。降级策略如下：

| 失败阶段 | 降级方案 | 说明 |
|---|---|---|
| 模型超时 | 返回 session(status=processing)，后台继续重试 | 前台显示"计划正在生成中"等待卡 |
| 结构不合格（第一次） | 触发一次自动重试 | 更换 Prompt 模板尝试 |
| 结构不合格（重试后） | 返回基于阶段的通用模板计划 | 从预置模板库中按 stage + focus_theme 匹配 |
| 边界检查不通过 | 逐字段替换为安全表达，不丢弃整个计划 | 尽量保留结构完整性 |

## 五、周反馈生成输出结构（WeeklyFeedbackResult）

周反馈是系统中"AI 回看一周表现并给出前瞻建议"的核心产物。它在周期结束时（或家长手动触发时）由 AI 基于本周记录、计划执行情况和儿童档案生成。

### 5.1 输出 Schema

```
WeeklyFeedbackResult {
  // —— 积极变化 ——
  positive_changes: Array<FeedbackItemContent>    // 1-3 个

  // —— 仍需机会 ——
  opportunities: Array<FeedbackItemContent>       // 1-3 个

  // —— 整体摘要 ——
  summary_text: String

  // —— 下周决策选项 ——
  decision_options: Array<DecisionOptionContent>   // 固定 3 个

  // —— 保守路径说明 ——
  conservative_path_note: String

  // —— 数据引用 ——
  referenced_record_ids: Array<UUID>   // AI 引用了哪些记录
  referenced_plan_id: UUID             // AI 引用的计划

  // —— 元数据 ——
  metadata: OutputMetadata
}

FeedbackItemContent {
  title: String                  // 变化项标题
  description: String            // 变化项描述
  supporting_evidence: String    // 支撑证据摘要（从记录中提取）
}

DecisionOptionContent {
  id: String
  text: String                   // 选项显示文本
  value: Enum(continue, lower_difficulty, change_focus)
  rationale: String              // 选择该选项的理由说明
}
```

### 5.2 字段约束

| 字段 | 约束 | 说明 |
|---|---|---|
| **positive_changes** | 1-3 个，不得为空 | 即使本周表现平淡，也至少找到 1 个积极点 |
| **positive_changes[n].title** | 最长 25 字符 | |
| **positive_changes[n].description** | 最长 200 字符 | |
| **positive_changes[n].supporting_evidence** | 最长 100 字符 | 必须引用实际记录内容 |
| **opportunities** | 1-3 个，不得为空 | |
| **opportunities[n].title** | 最长 25 字符 | |
| **opportunities[n].description** | 最长 200 字符 | |
| **summary_text** | 最长 300 字符 | |
| **decision_options** | 恰好 3 个 | 对应继续、降低难度、换焦点 |
| **decision_options[n].text** | 最长 30 字符 | |
| **decision_options[n].rationale** | 最长 100 字符 | |
| **conservative_path_note** | 最长 200 字符 | |

### 5.3 与数据结构的映射

| WeeklyFeedbackResult 字段 | 写入目标 | 写入字段 |
|---|---|---|
| positive_changes | WeeklyFeedback.positive_changes | 转换为 FeedbackItem 值对象 |
| opportunities | WeeklyFeedback.opportunities | 转换为 FeedbackItem 值对象 |
| summary_text | WeeklyFeedback.summary_text | 直接写入 |
| decision_options | WeeklyFeedback.decision_options | 转换为 DecisionOption 值对象 |
| conservative_path_note | WeeklyFeedback.conservative_path_note | 直接写入 |
| referenced_record_ids | FeedbackItem.supporting_records | 拆分到各 FeedbackItem |

### 5.4 与前台组件区的映射

| 前台组件区 | 消费字段 | 渲染方式 |
|---|---|---|
| F-2 PositiveChangeCard | positive_changes[n].title, description, supporting_evidence | SummaryCard 列表 |
| F-3 OpportunityCard | opportunities[n].title, description | SummaryCard 列表 |
| F-4 NextWeekDecisionPanel | decision_options | SelectableTagGroup（单选） |
| F-5 ConservativePathNote | conservative_path_note | 虚线边框 SummaryCard |

### 5.5 非诊断化边界检查点

| 检查项 | 检查范围 | 不通过时处理 |
|---|---|---|
| **诊断性标签** | 所有文本字段 | 替换为支持性表达 |
| **消极归因** | opportunities[n].description | 不得暗示"孩子做不到"或"家长没做好" |
| **过度乐观** | positive_changes[n].description | 不得过度解读单次进步为"问题已解决" |
| **积极变化非空** | positive_changes | 至少 1 个，即使需要从很小的进步中提取 |
| **决策选项平衡** | decision_options | 三个选项不得有明显的情感偏向（如把"降低难度"描述为"退步"） |
| **证据可追溯** | supporting_evidence | 必须能对应到 referenced_record_ids 中的某条记录 |

### 5.6 降级版本

| 失败阶段 | 降级方案 | 说明 |
|---|---|---|
| 模型超时 | 返回 WeeklyFeedback(status=generating) | 前台显示"反馈正在生成"等待卡 |
| 结构不合格 | 返回记录摘要 + 通用决策选项 | 跳过 AI 总结，直接展示本周记录条数和完成率 |
| 记录过少（< 2 条） | 生成时提示"本周记录较少，反馈参考价值有限" | 在 summary_text 中说明 |
| 边界检查不通过 | 逐字段替换为安全表达 | 保留结构完整性 |

## 六、三类输出的统一处理流程

尽管三类输出的内容和结构不同，但编排层对它们的处理流程是统一的。以下流程适用于所有 AI 输出：

### 6.1 标准处理流程

```
1. 接收请求
   ↓
2. 拼装上下文（ContextSnapshot）
   ↓
3. 选择 Prompt 模板（根据 session_type + child.stage + child.risk_level）
   ↓
4. 调用模型（含超时控制）
   ↓
5. 解析结构化输出（JSON 解析）
   ├── 解析失败 → 重试（最多 1 次）→ 仍失败 → 降级
   ↓
6. 字段约束校验（长度、数量、必填）
   ├── 校验失败 → 重试或逐字段修正
   ↓
7. 非诊断化边界检查（逐字段）
   ├── 检查不通过 → 逐字段替换为安全表达
   ↓
8. 写入 AISession.result
   ↓
9. 拆分写入业务对象（Plan/DayTask/WeeklyFeedback）
   ↓
10. 返回前台（或通过轮询/推送通知前台结果已就绪）
```

### 6.2 超时与重试策略

| 输出类型 | 首次超时阈值 | 重试次数 | 重试间隔 | 最终降级阈值 |
|---|---|---|---|---|
| **即时求助** | 8 秒 | 1 次 | 2 秒 | 12 秒 |
| **微计划生成** | 30 秒 | 1 次 | 5 秒 | 45 秒 |
| **周反馈生成** | 20 秒 | 1 次 | 5 秒 | 35 秒 |

即时求助的超时阈值最短，因为它服务的是高压时刻，家长等不起。微计划生成允许更长时间，因为它通常是后台异步触发的。

### 6.3 Prompt 模板选择矩阵

系统应根据 session_type、child.stage 和 child.risk_level 选择不同的 Prompt 模板。以下是模板选择的维度组合：

| session_type | stage 维度 | risk_level 维度 | 模板数量 |
|---|---|---|---|
| **instant_help** | 3 阶段 | 3 级别 | 最多 9 个 |
| **plan_generation** | 3 阶段 | 3 级别 | 最多 9 个 |
| **weekly_feedback** | 3 阶段 | 3 级别 | 最多 9 个 |

> 实际实现时，不必一开始就准备 27 个模板。建议先按 session_type 各做 1 个通用模板，在模板内部通过条件分支处理 stage 和 risk_level 的差异。等到内容团队确认阶段差异足够大时，再拆分为独立模板。

### 6.4 边界检查规则分层

边界检查分为两层：**硬规则**可 100% 代码化实现，是发布前的阻塞性检查；**软规则**需要额外 LLM 审查调用或人工抽检，是质量提升手段而非阻塞条件。

**硬规则（可直接代码化）：**

| 类别 | 实现方式 | 示例 | 不通过时处理 |
|---|---|---|---|
| **诊断标签黑名单** | 正则/关键词匹配 | "自闭""多动""发育迟缓""语言障碍""感统失调" | 删除词汇并替换为"如果持续担心，建议咨询专业人士" |
| **治疗承诺黑名单** | 正则/关键词匹配 | "治愈""矫正""根治""训练好" | 替换为"帮助""支持""给更多机会" |
| **绝对判断黑名单** | 正则/关键词匹配 | "一定""肯定""必须""不能不" | 替换为"可以试试""通常""很多家庭发现" |
| **过度量化黑名单** | 正则匹配（"每天必须\d+次"等） | "每天必须3次""必须坚持7天" | 替换为"尝试在自然时机中融入" |
| **字段完整性** | Schema 校验 | 三步不为空、day_tasks 恰好 7 个 | 触发重试 |
| **字符长度** | 长度检查 | 各字段最大字符数 | 截断并标记 |

**软规则（需语义审查，不作为发布阻塞条件）：**

| 类别 | 审查方式 | 示例 | 处理 |
|---|---|---|---|
| **隐式责备** | 定期人工抽检 + 可选 LLM 二次审查 | "你应该早点注意到""如果你之前就..." | 标记并纳入 Prompt 模板优化 |
| **Day 1-7 难度连贯性** | 人工抽检 | 7 天任务是否渐进 | 纳入 Prompt 模板约束 |
| **过度乐观** | 定期人工抽检 | 单次进步被解读为"问题已解决" | 纳入 Prompt 模板优化 |
| **消极归因** | 定期人工抽检 | "孩子做不到""孩子不配合" | 纳入 Prompt 模板优化 |

## 七、输出结构与 AISession 对象的关联

为了与《数据结构草案 V1》中定义的 AISession 对象完全对齐，以下明确三类输出结构如何映射到 AISession.result 字段。

AISession.result 是一个多态字段，其具体结构取决于 AISession.session_type：

| session_type | AISession.result 的实际类型 | 说明 |
|---|---|---|
| instant_help | InstantHelpResult | 直接存储完整结果 |
| plan_generation | PlanGenerationResult | 存储完整结果，同时拆分写入 Plan + DayTask |
| weekly_feedback | WeeklyFeedbackResult | 存储完整结果，同时拆分写入 WeeklyFeedback |

AISession.degraded_result 的结构与 AISession.result 相同，但内容为降级版本。前台在消费时，优先使用 result；如果 result 为空且 status 为 degraded，则使用 degraded_result。

## 八、质量监控指标

为了持续改进 AI 输出质量，编排层应记录以下监控指标：

| 指标 | 计算方式 | 健康阈值 |
|---|---|---|
| **结构解析成功率** | 首次解析成功 / 总请求 | > 95% |
| **边界检查通过率** | 首次检查全通过 / 总请求 | > 90% |
| **降级率** | 最终返回降级结果 / 总请求 | < 5% |
| **平均延迟** | 按 session_type 分组统计 | 即时求助 < 6s，计划 < 20s，反馈 < 15s |
| **重试率** | 触发重试 / 总请求 | < 10% |
| **字段截断率** | 需要截断的字段数 / 总字段数 | < 3% |

当任一指标超出阈值时，应触发告警并进入人工审查流程。

## 九、结论

到这一版为止，三类 AI 输出（即时求助、微计划生成、周反馈）都已经有了明确的结构化 schema、字段约束、前台映射关系、非诊断化检查点和降级策略。这意味着 AI 编排层的实现不再需要猜测"前台需要什么格式"，而可以直接按照本稿定义的 schema 来解析、校验和写入。

| 结论项 | 结果 |
|---|---|
| **输出类型数** | 3 类（InstantHelpResult、PlanGenerationResult、WeeklyFeedbackResult） |
| **总字段数** | 即时求助 ~15 个、微计划 ~60 个（含 7 日展开）、周反馈 ~25 个 |
| **降级方案** | 每类输出均有完整降级版本 |
| **边界检查维度** | 5 个统一类别 + 各类型特定检查 |
| **处理流程** | 10 步标准流程，适用于所有类型 |
| **监控指标** | 6 个核心指标 |
| **与数据结构草案对齐** | AISession.result 多态映射已明确 |
| **与组件拆解对齐** | 所有前台组件区消费字段均有对应输出字段 |

| 推荐下一步 | 产出目标 |
|---|---|
| **Prompt 模板 V1** | 基于本稿的 schema 和约束编写第一版 Prompt 模板 |
| **通用组件接口定义** | 为 9 个通用组件补充伪类型签名 |
| **端到端联调草案** | 把数据结构 + AI 输出 + 组件区串成完整的联调清单 |
