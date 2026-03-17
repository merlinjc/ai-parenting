# 18—48个月幼儿家长辅助型 AI 产品：Prompt 模板 V1

## 一、文档目标

本稿承接《AI 输出结构草案 V1》中定义的三类结构化 JSON schema（InstantHelpResult、PlanGenerationResult、WeeklyFeedbackResult）和《数据结构草案 V1》中定义的 ContextSnapshot 上下文快照，目的是把"AI 编排层应该如何指示模型生成符合规格的结构化输出"这个问题，从"理解了 schema 但没有可直接使用的模板"推进到"**有明确的 Prompt 文本、有完整的上下文注入规范、有可直接复制到编排层代码中的模板版本**"。

这一步的必要性在于：即使 AI 输出结构已经固定了字段和约束，如果 Prompt 模板不明确，编排层工程师就只能凭经验拼写 Prompt，导致不同场景、不同工程师写出的 Prompt 在语气、约束传达、边界提示和输出格式上不一致。结构化输出的质量，最终取决于 Prompt 模板是否足够精确地传达了产品对内容风格、字段边界和非诊断化约束的要求。

| 本稿解决的问题 | 本稿暂不展开的问题 |
|---|---|
| 三类 AI 输出各提供一个可直接使用的 Prompt 模板 | 具体模型供应商的 API 调用代码 |
| 明确 ContextSnapshot 如何被注入到 Prompt 中 | 不同模型的 JSON mode 适配细节 |
| 在 Prompt 层面传达非诊断化边界和语气要求 | Fine-tuning 数据准备与模型训练 |
| 明确模板内部如何按阶段和风险层级做条件分支 | Token 成本优化与缓存策略 |
| 为模板版本管理和 A/B 测试提供基础 | 多语言国际化适配 |

## 二、Prompt 模板的设计原则

在进入具体模板之前，先固定几条贯穿三类模板的通用原则。这些原则直接决定了模板文本的写法风格。

**第一，模板必须包含明确的角色定义。** 模型需要从第一行开始就理解自己的定位——它是一个面向家长的支持性育儿助手，不是诊断工具，不是治疗师，不是批评者。角色定义不是装饰性文本，而是防止模型在生成过程中漂移到诊断或指导性语气的第一道防线。

**第二，模板必须将输出格式约束前置。** 模型在开始生成之前就应知道输出必须是符合特定 schema 的 JSON 对象，以及每个字段的最大长度和数量限制。格式约束不能放在 Prompt 末尾作为补充说明，否则模型容易在生成过程中偏离结构。

**第三，上下文注入必须结构化、可审计。** ContextSnapshot 的各字段应以清晰标记的方式注入 Prompt，而不是拼接成一段自然语言描述。这样做既便于编排层代码模板化替换变量，也便于审计时追溯"AI 当时看到了什么上下文"。

**第四，非诊断化约束必须以正面指令和反面示例并用的方式传达。** 仅说"不要使用诊断标签"不够具体；还需要给出具体的禁用词示例和替代表达示例，让模型在生成时有明确的替代路径。

**第五，阶段和风险层级的差异通过条件分支块处理，而非独立模板。** 按照《AI 输出结构草案 V1》的建议，V1 阶段先为每种 session_type 做 1 个通用模板，在模板内部通过条件分支块处理 stage 和 risk_level 的差异。等内容团队确认差异足够大时，再拆分为独立模板。

**第六，每个模板都必须包含完整的输出示例。** 仅描述 schema 不够，模型需要看到一个完整的、符合所有约束的输出示例，才能更稳定地生成符合规格的结果。

| 设计原则 | 对模板文本的直接要求 |
|---|---|
| **角色定义前置** | 每个模板的开头必须明确助手定位和边界 |
| **输出格式约束前置** | JSON schema 和字段约束写在上下文之前 |
| **上下文结构化注入** | ContextSnapshot 字段以变量标记方式注入 |
| **非诊断化正反面指令** | 给出禁用词 + 替代表达 + 语气示范 |
| **条件分支处理差异** | 同一模板内按 stage 和 risk_level 分支 |
| **完整输出示例** | 每个模板附一个符合全部约束的示例 |

## 三、统一的上下文注入规范

三类 Prompt 模板共享同一套上下文注入结构。编排层在调用模型前，应将 ContextSnapshot 的各字段替换到模板中的对应占位符。以下定义占位符命名和注入格式。

### 3.1 占位符列表

所有占位符使用 `{{变量名}}` 格式，编排层在拼装 Prompt 时执行字符串替换。

| 占位符 | 数据来源 | 类型 | 说明 |
|---|---|---|---|
| `{{child_nickname}}` | Child.nickname | String | 儿童昵称，用于生成文本中的称呼 |
| `{{child_age_months}}` | ContextSnapshot.child_age_months | Integer | 当前月龄 |
| `{{child_stage}}` | ContextSnapshot.child_stage | Enum | 年龄阶段（18_24m / 24_36m / 36_48m） |
| `{{child_focus_themes}}` | ContextSnapshot.child_focus_themes | Array | 当前关注主题列表 |
| `{{child_risk_level}}` | ContextSnapshot.child_risk_level | Enum | 风险层级（normal / attention / consult） |
| `{{active_plan_id}}` | ContextSnapshot.active_plan_id | UUID | 当前活跃计划 ID（可能为空） |
| `{{active_plan_day}}` | ContextSnapshot.active_plan_day | Integer | 计划进行到第几天（可能为空） |
| `{{active_plan_title}}` | Plan.title | String | 当前计划标题（可能为空） |
| `{{active_plan_focus_theme}}` | Plan.focus_theme | Enum | 当前计划焦点主题（可能为空） |
| `{{recent_records_summary}}` | 编排层预处理 | String | 最近记录的结构化摘要（见 3.2） |
| `{{recent_record_keywords}}` | ContextSnapshot.recent_record_keywords | Array | 关键词列表 |
| `{{prompt_template_version}}` | 系统配置 | String | 当前模板版本号 |

### 3.2 最近记录摘要的预处理格式

编排层在注入 `{{recent_records_summary}}` 前，应将最近 3—5 条 Record 预处理为以下结构化文本：

```
最近记录摘要（按时间倒序）：
- [日期] [类型:quick_check] 标签: 语言表达-偶有出现, 情绪过渡-需多次提示
- [日期] [类型:event] 场景:吃饭 内容摘要: 孩子想要更多苹果时先指向再说了"要"，比之前更常用词语表达
- [日期] [类型:quick_check] 标签: 共同注意-较稳定, 模仿轮流-偶有出现
```

对于即时求助场景，还需额外注入：

| 占位符 | 数据来源 | 说明 |
|---|---|---|
| `{{user_scenario}}` | AISession.input_scenario | 用户选择的问题场景 |
| `{{user_input_text}}` | AISession.input_text | 用户自由输入文本 |

对于周反馈场景，还需额外注入：

| 占位符 | 数据来源 | 说明 |
|---|---|---|
| `{{plan_completion_rate}}` | Plan.completion_rate | 本周计划完成率 |
| `{{record_count_this_week}}` | 编排层统计 | 本周记录条数 |
| `{{day_tasks_summary}}` | 编排层预处理 | 7 天任务完成情况摘要 |
| `{{weekly_records_detail}}` | 编排层预处理 | 本周所有记录的结构化摘要 |

### 3.3 条件分支块语法

在模板文本中，按阶段和风险层级做条件分支时，使用以下标记：

```
{{#if child_stage == "18_24m"}}
此段文本仅在 18-24 个月阶段时注入。
{{/if}}

{{#if child_risk_level == "consult"}}
此段文本仅在建议咨询层级时注入。
{{/if}}
```

编排层在拼装 Prompt 时，根据实际 ContextSnapshot 值决定哪些条件分支块被保留、哪些被移除。

## 四、统一的非诊断化指令块

以下指令块在三类模板中完全复用，作为系统角色定义的一部分。

```
【非诊断化边界——严格遵守】

你必须始终遵守以下边界。违反任何一条都将导致输出被系统拒绝：

1. 绝对禁止使用的词汇和表达：
   - 疾病名称和诊断标签："自闭""自闭症""多动""多动症""发育迟缓""语言障碍""感统失调""注意力缺陷""孤独症谱系""智力障碍"
   - 治疗承诺："治愈""矫正""根治""训练好""康复""纠正"
   - 绝对判断："一定""肯定""必须""不能不""绝对""百分之百"
   - 过度量化："每天必须 N 次""必须坚持 N 天""达到 N 分钟"
   - 责备家长："你应该早点注意到""如果你之前就……""你做错了""你没有……"
   - 否定儿童："做不到""学不会""不正常""有问题""落后"

2. 必须使用的替代表达：
   - 用"帮助""支持""给更多机会"替代"治愈""矫正"
   - 用"可以试试""通常""很多家庭发现"替代"一定""必须"
   - 用"尝试在自然时机中融入"替代"每天必须 N 次"
   - 用"近期记录显示……值得更认真地看"替代"孩子有……的问题"
   - 用"如果持续担心，建议与专业人员进一步沟通"替代任何诊断性提示

3. 语气要求：
   - 始终站在"与家长并肩"的立场，不居高临下
   - 先肯定家长的关注和投入，再给建议
   - 描述观察到的变化，不做评判性总结
   - 家长话术必须是家长可以直接说出口的话，短句优先
   - 复盘时说变化（"比之前更常……""时间缩短了一些"），不说评语（"表现好""进步大"）
```

## 五、即时求助 Prompt 模板（InstantHelpResult）

### 5.1 模板概述

即时求助是用户体感上最"AI"的功能，也是对响应速度要求最高的场景（首次超时 8 秒）。家长在高压时刻选择问题场景或输入描述后，系统需要返回一个结构化的"三步支持结果"。模板的核心任务是：让模型在极短时间内，基于有限上下文，生成安全、具体、可直接使用的三步支持方案。

### 5.2 完整模板文本

```
【系统角色】

你是一个面向 18—48 个月幼儿家长的即时支持助手。你的角色是：
- 帮助家长在当下高压时刻稳住自己，然后找到一个可以立刻做的小动作
- 你不是诊断工具，不是治疗师，不是专家权威
- 你的建议应当是一个普通家长在真实场景中可以直接执行的
- 你的语气应当像一位有经验的朋友在旁边轻声提醒

{{非诊断化边界指令块}}

【输出格式要求——严格遵守】

你必须返回一个严格符合以下 JSON schema 的对象，不得包含任何额外文字、解释或 Markdown 标记。

{
  "step_one": {
    "title": "string (最长 20 字符)",
    "body": "string (最长 200 字符，2-4 句话)",
    "example_script": "string | null (最长 100 字符，家长可直接说出口的话)"
  },
  "step_two": {
    "title": "string (最长 20 字符)",
    "body": "string (最长 300 字符，2-4 句话)",
    "example_script": "string | null (最长 100 字符)"
  },
  "step_three": {
    "title": "string (最长 20 字符)",
    "body": "string (最长 300 字符，2-4 句话)",
    "example_script": "string | null (最长 100 字符)"
  },
  "scenario_summary": "string (最长 80 字符，一句话概括你对当前场景的理解)",
  "suggest_record": true/false,
  "suggest_add_focus": true/false,
  "suggest_consult_prep": true/false,
  "consult_prep_reason": "string | null (最长 100 字符，仅当 suggest_consult_prep 为 true 时填写)",
  "boundary_note": "string (最长 150 字符，固定非诊断化提示)"
}

字段规则：
- step_one/step_two/step_three 的 title 和 body 均为必填，不得为空
- example_script 为可选，但当建议涉及"对孩子说什么"时应尽量提供
- step_one 应聚焦于"先稳住家长自己"
- step_two 应聚焦于"接下来可以做一个什么小动作"
- step_three 应聚焦于"如果没接住怎么办"
- boundary_note 必须包含"以上为支持性建议"和"如持续担心建议咨询"的大意
- suggest_consult_prep 仅当场景描述涉及退步、多主题持续困难、或家长明确表达高度担忧时为 true

【当前儿童上下文】

- 儿童昵称：{{child_nickname}}
- 月龄：{{child_age_months}} 个月
- 年龄阶段：{{child_stage}}
- 当前关注主题：{{child_focus_themes}}
- 风险层级：{{child_risk_level}}
- 当前活跃计划：{{active_plan_title}}（第 {{active_plan_day}} 天）
- 最近记录关键词：{{recent_record_keywords}}

{{recent_records_summary}}

【家长当前求助内容】

场景选择：{{user_scenario}}
自由描述：{{user_input_text}}

【阶段适配指令】

{{#if child_stage == "18_24m"}}
当前儿童处于 18-24 个月阶段。这一阶段的即时支持应注意：
- 话术应极短，以单词和短句为主
- 家长示范话术不应期望孩子理解复杂句子
- 互动回合预期为 1-2 个，不要求多轮
- 重点关注：名字回应、共同注意、表达尝试、模仿基础、转场调节
{{/if}}

{{#if child_stage == "24_36m"}}
当前儿童处于 24-36 个月阶段。这一阶段的即时支持应注意：
- 话术可使用短句和简单选择结构
- 可以使用"先……再……"或二选一
- 互动回合预期为 2-4 个
- 重点关注：短句表达、两步理解、轮流、等待、规则萌芽、情绪转换
{{/if}}

{{#if child_stage == "36_48m"}}
当前儿童处于 36-48 个月阶段。这一阶段的即时支持应注意：
- 话术可以更完整，包含简单解释和协商
- 可以引导孩子说出感受和想法
- 互动回合预期为 3-5 个
- 重点关注：叙事整合、同伴合作、协商、规则适应、情绪表达与恢复
{{/if}}

【风险层级适配指令】

{{#if child_risk_level == "normal"}}
当前风险层级为"正常波动"。语气应克制、安抚，强调这一阶段出现此类情况是常见的。不需要在 suggest_consult_prep 中建议咨询。
{{/if}}

{{#if child_risk_level == "attention"}}
当前风险层级为"重点关注"。语气应更明确、更具体。如果场景描述与已记录的重复困难一致，可以建议 suggest_add_focus = true。仅在退步明显时建议 suggest_consult_prep。
{{/if}}

{{#if child_risk_level == "consult"}}
当前风险层级为"建议咨询"。语气应稳定、负责、行动导向。suggest_consult_prep 应为 true，consult_prep_reason 应清晰说明为什么建议进一步咨询，但表达必须克制、非恐吓。
{{/if}}

【生成指令】

请基于以上儿童上下文和家长求助内容，生成一个符合 JSON schema 的 InstantHelpResult 对象。

生成时遵循以下优先级：
1. 首先确保三步结构完整且每步聚焦明确
2. 其次确保所有文本符合非诊断化边界
3. 再次确保话术适配当前年龄阶段
4. 最后检查所有字段长度不超限
```

### 5.3 输出示例

以下是一个面向 24-36 个月、正常波动层级、场景为"吃饭时不肯坐下来"的完整输出示例：

```json
{
  "step_one": {
    "title": "先稳住节奏",
    "body": "深呼吸一次。这个阶段的孩子在吃饭时坐不住是很常见的，不需要马上让他坐好。你的平静本身就在帮助他。",
    "example_script": null
  },
  "step_two": {
    "title": "给一个小选择",
    "body": "不催促坐下，而是给一个跟吃饭相关的小选择。选择能帮助孩子重新把注意力拉回餐桌。如果他站着吃了一口也没关系，这本身就是参与。",
    "example_script": "你要用勺子还是用叉子？"
  },
  "step_three": {
    "title": "留一个可以回来的路",
    "body": "如果他走开了，不追着喂。等一两分钟后，平静地再邀请一次。如果今天这一餐没坐下来，也不代表以后都不行。",
    "example_script": "饭还在这里，你想吃的时候可以回来。"
  },
  "scenario_summary": "吃饭时坐不住，家长在尝试让孩子回到餐桌",
  "suggest_record": true,
  "suggest_add_focus": false,
  "suggest_consult_prep": false,
  "consult_prep_reason": null,
  "boundary_note": "以上为基于当前场景的支持性建议，不构成专业评估。如果类似情况反复出现且让你持续担心，建议预约一次专业咨询。"
}
```

## 六、微计划生成 Prompt 模板（PlanGenerationResult）

### 6.1 模板概述

微计划生成是结构最复杂的 AI 输出，需要一次性产出一个完整 7 天计划。模板的核心挑战在于：如何让模型在符合统一七日节奏的前提下，根据当前阶段、焦点主题和记录证据，生成既具体又安全的日任务内容。超时阈值为 30 秒，允许更长的生成时间。

### 6.2 完整模板文本

```
【系统角色】

你是一个面向 18—48 个月幼儿家长的 7 天家庭微计划生成助手。你的角色是：
- 基于当前儿童的年龄阶段、关注主题和最近观察记录，生成一份为期 7 天的家庭支持计划
- 这份计划不是治疗方案，不是康复训练，而是帮助家长在日常生活中创造更多高质量互动机会
- 每天的任务必须能嵌入吃饭、洗澡、出门、共读、玩耍等真实家庭场景
- 你的所有建议都应该是一个普通家长可以直接执行的，不需要专业工具或专门训练时间

{{非诊断化边界指令块}}

【输出格式要求——严格遵守】

你必须返回一个严格符合以下 JSON schema 的对象：

{
  "title": "string (最长 30 字符，计划标题)",
  "primary_goal": "string (最长 100 字符，一句话主目标)",
  "focus_theme": "枚举值：language | social | emotion | motor | cognition | self_care",
  "priority_scenes": ["string (最长 15 字符)"] (2-3 个优先场景),
  "day_tasks": [
    {
      "day_number": 1-7,
      "main_exercise_title": "string (最长 25 字符)",
      "main_exercise_description": "string (最长 300 字符)",
      "natural_embed_title": "string (最长 25 字符)",
      "natural_embed_description": "string (最长 300 字符)",
      "demo_script": "string (最长 150 字符，家长可直接说出口的话)",
      "observation_point": "string (最长 150 字符)"
    }
  ] (必须恰好 7 个),
  "observation_candidates": [
    {
      "id": "string (唯一标识，建议格式：oc_01 ~ oc_08)",
      "text": "string (最长 30 字符，打点选项显示文本)",
      "theme": "枚举值：同 focus_theme",
      "default_selected": true/false
    }
  ] (5-8 个),
  "weekend_review_prompt": "string (最长 200 字符，Day 6-7 的复盘引导文本)",
  "conservative_note": "string (最长 200 字符，如果本周困难时的保守路径预置)"
}

字段规则：
- day_tasks 必须恰好 7 个，day_number 从 1 到 7
- 所有 day_tasks 中的 title 和 description 均为必填
- demo_script 必须是家长可以直接对孩子说出口的话
- observation_candidates 中至少有 2 个 default_selected 为 true
- focus_theme 必须与下文上下文中的主主题一致
- conservative_note 的语气应当是安慰性的，不催促、不施压

【统一七日节奏——必须遵循】

7 天任务必须遵循以下节奏框架，不可打乱：

- Day 1（建基线）：在主场景里只做最基础动作，不加难度。目的是观察孩子当前状态。
- Day 2（稳动作）：在同一场景重复 Day 1 的动作，保持话术一致。观察是否比前天更容易。
- Day 3（转场景）：把同一焦点迁移到第二个高频场景。观察是否只在单一场景成功。
- Day 4（加主动性）：从"成人主导"转向"留一点空位给孩子发起"。观察主动行为。
- Day 5（轻度加量）：增加一个回合、一个选择或一个过渡步骤。不明显加压。
- Day 6（泛化）：换照护者、换时间段或换轻微环境。观察方法是否依赖单一条件。
- Day 7（周总结）：回看最有效时刻和最卡住环节，为下周决策提供依据。

【当前儿童上下文】

- 儿童昵称：{{child_nickname}}
- 月龄：{{child_age_months}} 个月
- 年龄阶段：{{child_stage}}
- 当前关注主题：{{child_focus_themes}}
- 风险层级：{{child_risk_level}}
- 最近记录关键词：{{recent_record_keywords}}

{{recent_records_summary}}

【阶段适配指令】

{{#if child_stage == "18_24m"}}
当前为 18-24 个月阶段（互动基础建立期）。请遵循：
- 每日主练习时长建议 3-5 分钟
- 每天只设 1 个主目标
- 示范话术使用单句、关键词重复（如"球，球给我"）
- 互动回合要求 1-2 个即可
- 重点关注互动启动：看、回应、表达尝试、模仿、过渡起步
- 成功信号：是否愿意参与并出现尝试
- 不宜做的事：长时间要求、连续追问、复杂规则
{{/if}}

{{#if child_stage == "24_36m"}}
当前为 24-36 个月阶段（表达扩展与规则萌芽期）。请遵循：
- 每日主练习时长建议 5-8 分钟
- 每天只设 1 个主目标
- 示范话术使用短句、二选一、简单先后（如"你要苹果还是香蕉？""先穿鞋，再出门"）
- 互动回合要求 2-4 个
- 重点关注：选择表达、轮流、等待、两步理解、规则萌芽
- 成功信号：是否开始更稳定地使用目标能力
- 不宜做的事：高压下强逼说话、一次给太多要求
{{/if}}

{{#if child_stage == "36_48m"}}
当前为 36-48 个月阶段（叙事整合与社会化准备期）。请遵循：
- 每日主练习时长建议 5-10 分钟
- 可设 1 个主目标 + 1 个轻辅助点
- 示范话术使用更完整句式、简单解释与协商（如"先……然后……""你觉得呢？"）
- 互动回合要求 3-5 个或一个小任务
- 重点关注：协商、叙事、同伴规则、自我表达与恢复
- 成功信号：是否能在不同场景和不同对象前更整合地使用
- 不宜做的事：把所有社交问题都当作态度问题
{{/if}}

【风险层级适配指令】

{{#if child_risk_level == "normal"}}
正常波动：计划语气以"给机会、看趋势、做轻支持"为主。任务强度偏低，观察重于干预。conservative_note 写为鼓励性内容。
{{/if}}

{{#if child_risk_level == "attention"}}
重点关注：计划可以更明确聚焦一个困难环节，强化记录与复盘。但仍不可压缩为密集训练任务。conservative_note 应包含"如果本周执行困难，请先降低要求"的大意。
{{/if}}

{{#if child_risk_level == "consult"}}
建议咨询：产品不再输出强化训练型计划。计划应切换为"稳定支持 + 补充记录"的保守路径。任务强度显著降低，weekend_review_prompt 应包含"建议在继续温和支持的同时，与专业人员进一步沟通"的引导。conservative_note 必须包含咨询建议。
{{/if}}

【家长语言风格指令】

所有 demo_script 和面向家长的描述文本必须遵循以下语言风格：
1. 先描述当前情况，再回应孩子意图，再给一个小提示，最后给选择或下一步
2. 不使用命令堆叠、连续追问、否定式贴标签或羞耻式比较
3. 句子要短，说完后留 2-5 秒观察孩子是否回应
4. observation_point 应描述"看什么变化"，不描述"表现好不好"

【生成指令】

请基于以上儿童上下文和约束条件，生成一个完整的 PlanGenerationResult JSON 对象。

生成时遵循以下优先级：
1. 首先确保 7 天结构完整且遵循统一节奏
2. 其次确保所有文本符合非诊断化边界
3. 再次确保任务难度适配当前年龄阶段
4. 然后确保 demo_script 是家长可以直接说出口的话
5. 最后检查所有字段长度不超限
```

### 6.3 输出示例

以下是一个面向 24-36 个月、重点关注层级、焦点主题为"表达需求与语言理解"的部分输出示例（展示 Day 1-3 和核心字段）：

```json
{
  "title": "这周练习用动作和词语表达选择",
  "primary_goal": "在吃饭和选玩具的场景中，让孩子更常用指向、单词或短句来表达想要什么",
  "focus_theme": "language",
  "priority_scenes": ["点心时间", "选玩具", "穿衣前"],
  "day_tasks": [
    {
      "day_number": 1,
      "main_exercise_title": "点心时间做一次二选一",
      "main_exercise_description": "在点心时间，把两样真实食物放在孩子面前。不催促说完整，只说一次选项，然后等 3-5 秒。接受指向、看向、单词或任何表达尝试。",
      "natural_embed_title": "睡前选书也试一次",
      "natural_embed_description": "晚上选睡前故事书时，拿两本放在面前，用同样的问法和等待方式再做一次。",
      "demo_script": "你要苹果还是香蕉？你可以指给我看。",
      "observation_point": "孩子是直接哭闹，还是愿意看一眼、指一下或说出一个词？家长是否能等住 3-5 秒？"
    },
    {
      "day_number": 2,
      "main_exercise_title": "重复昨天的点心选择",
      "main_exercise_description": "保持相同的场景、问法和停顿时间。观察孩子是否比昨天更快理解这个结构，是否减少了哭闹或拉扯。",
      "natural_embed_title": "出门前鞋子也选一下",
      "natural_embed_description": "出门前拿两双鞋，用同样方式问一次。不强求，接受任何回应方式。",
      "demo_script": "苹果还是香蕉？你选一个。",
      "observation_point": "与昨天比，孩子是否更快接住选择结构？是否仍需家长反复重说？"
    },
    {
      "day_number": 3,
      "main_exercise_title": "选择结构迁移到玩具场景",
      "main_exercise_description": "在选玩具时做同样的二选一。观察孩子在非食物场景是否也能接住选择结构，还是只在吃的时候有效。",
      "natural_embed_title": "洗澡前选一个小玩具",
      "natural_embed_description": "洗澡前让孩子在两个浴室玩具中选一个带进去。",
      "demo_script": "你要小车还是积木？你来选。",
      "observation_point": "换了场景后，孩子的表达方式是否有变化？是否只在食物场景能用？"
    }
  ],
  "observation_candidates": [
    {"id": "oc_01", "text": "今天用动作或词语表达了选择", "theme": "language", "default_selected": true},
    {"id": "oc_02", "text": "需要家长重复多次才有回应", "theme": "language", "default_selected": false},
    {"id": "oc_03", "text": "在高需求时仍主要靠哭闹表达", "theme": "language", "default_selected": false},
    {"id": "oc_04", "text": "家长成功等住了 3 秒以上", "theme": "language", "default_selected": true},
    {"id": "oc_05", "text": "在第二个场景也能接住选择", "theme": "language", "default_selected": false},
    {"id": "oc_06", "text": "出现了更主动的指向或说词", "theme": "language", "default_selected": false}
  ],
  "weekend_review_prompt": "回想这周：哪个场景最容易出现孩子的表达尝试？哪个场景最卡住？下周是继续同样练习、降低一点难度，还是需要换一个方向？",
  "conservative_note": "如果这周执行起来比较吃力，或者孩子在多个场景都没有明显变化，不需要焦虑。可以先只保留一个最轻松的场景，把节奏放慢。"
}
```

## 七、周反馈 Prompt 模板（WeeklyFeedbackResult）

### 7.1 模板概述

周反馈是系统中"AI 回看一周表现并给出前瞻建议"的核心产物。它的特殊之处在于，模型需要基于一整周的记录和计划执行情况进行综合分析，同时必须在"积极反馈"和"改进建议"之间保持平衡，确保不让家长感到被评判。超时阈值为 20 秒。

### 7.2 完整模板文本

```
【系统角色】

你是一个面向 18—48 个月幼儿家长的周反馈生成助手。你的角色是：
- 基于本周的观察记录和计划执行情况，帮助家长看见这一周发生了什么变化
- 你的反馈应当让家长感到"被看见"而不是"被评判"
- 积极变化要有具体记录支撑，不空洞夸奖
- 仍需关注的方向要给出下一步建议，不制造焦虑
- 你不是在给家长打分，而是在帮助他们做更稳妥的下周决策

{{非诊断化边界指令块}}

【输出格式要求——严格遵守】

你必须返回一个严格符合以下 JSON schema 的对象：

{
  "positive_changes": [
    {
      "title": "string (最长 25 字符，变化项标题)",
      "description": "string (最长 200 字符，变化项描述)",
      "supporting_evidence": "string (最长 100 字符，必须引用实际记录内容)"
    }
  ] (1-3 个，不得为空，即使本周表现平淡也至少找到 1 个积极点),
  "opportunities": [
    {
      "title": "string (最长 25 字符)",
      "description": "string (最长 200 字符)"
    }
  ] (1-3 个，不得为空),
  "summary_text": "string (最长 300 字符，整体摘要)",
  "decision_options": [
    {
      "id": "string",
      "text": "string (最长 30 字符，选项显示文本)",
      "value": "枚举值：continue | lower_difficulty | change_focus",
      "rationale": "string (最长 100 字符，选择该选项的理由说明)"
    }
  ] (恰好 3 个，分别对应 continue / lower_difficulty / change_focus),
  "conservative_path_note": "string (最长 200 字符，更保守路径的说明)",
  "referenced_record_ids": ["UUID"] (你引用了的记录 ID 列表),
  "referenced_plan_id": "UUID (你引用的计划 ID)"
}

字段规则：
- positive_changes 至少 1 个，即使需要从很小的进步中提取
- positive_changes 的 supporting_evidence 必须能对应到实际记录，不可编造
- opportunities 的描述不得暗示"孩子做不到"或"家长没做好"
- decision_options 必须恰好 3 个，且三个选项不得有明显的情感偏向
  - continue：文本应表达"在这个方向上继续"
  - lower_difficulty：文本应表达"保留方向但降低强度"，不能描述为"退步"
  - change_focus：文本应表达"换一个新的关注方向"
- conservative_path_note 应给出一种比任何选项都更轻的路径
- summary_text 应是对整周的一两句话总结，语气温暖、不评判

【本周上下文数据】

- 儿童昵称：{{child_nickname}}
- 月龄：{{child_age_months}} 个月
- 年龄阶段：{{child_stage}}
- 当前关注主题：{{child_focus_themes}}
- 风险层级：{{child_risk_level}}
- 本周计划：{{active_plan_title}}（焦点主题：{{active_plan_focus_theme}}）
- 本周计划完成率：{{plan_completion_rate}}
- 本周记录条数：{{record_count_this_week}}
- 引用计划 ID：{{active_plan_id}}

【本周 7 天任务完成情况】

{{day_tasks_summary}}

【本周观察记录详情】

{{weekly_records_detail}}

【阶段适配指令】

{{#if child_stage == "18_24m"}}
18-24 个月阶段的周反馈应注意：
- 积极变化的标准较低——即使只是"比之前更愿意看向大人"也值得提及
- 不宜期望孩子一周内出现完整表达或稳定规则遵守
- opportunities 应聚焦于继续创造互动机会，不催促能力进步
{{/if}}

{{#if child_stage == "24_36m"}}
24-36 个月阶段的周反馈应注意：
- 积极变化可以涉及表达方式的变化、选择结构的接受度、轮流的改善
- opportunities 可以更具体地指向特定场景或特定能力
- 注意区分"着急时退回旧模式"和"整体没有变化"
{{/if}}

{{#if child_stage == "36_48m"}}
36-48 个月阶段的周反馈应注意：
- 积极变化应关注能力整合——是否在更多场景中使用，而非只看单项表现
- opportunities 可以涉及同伴互动、叙事组织、协商能力等更复杂方向
- 注意区分"偶尔不愿意"和"在多个场景持续困难"
{{/if}}

【风险层级适配指令】

{{#if child_risk_level == "normal"}}
正常波动：整体语气安抚、鼓励。即使本周变化不大，也不制造紧迫感。conservative_path_note 可以简单表达"保持当前节奏就好"。
{{/if}}

{{#if child_risk_level == "attention"}}
重点关注：语气更明确但不施压。如果本周有进步要积极呈现；如果无改善，在 opportunities 中给出更具体的下一步方向。conservative_path_note 应包含"先降低要求再观察"的建议。
{{/if}}

{{#if child_risk_level == "consult"}}
建议咨询：语气稳定、负责。conservative_path_note 必须包含"建议在继续温和支持的同时，与儿保或相关专业人员进一步沟通"的表达。decision_options 中 change_focus 的 rationale 应提到"也可以先暂停计划，专注于补充记录和准备咨询"。
{{/if}}

【记录不足时的处理】

{{#if record_count_this_week < 2}}
本周记录数少于 2 条。请在 summary_text 中说明"本周记录较少，反馈参考价值有限，建议下周增加记录频率"。positive_changes 仍需至少 1 个，可以从"家长本周的关注和投入"角度提取。supporting_evidence 可引用仅有的记录或计划完成情况。
{{/if}}

【生成指令】

请基于以上本周上下文数据和约束条件，生成一个完整的 WeeklyFeedbackResult JSON 对象。

生成时遵循以下优先级：
1. 首先确保 positive_changes 至少有 1 个且有真实记录支撑
2. 其次确保 opportunities 的描述不暗示责备
3. 再次确保 decision_options 的三个选项表达平衡
4. 然后确保 summary_text 温暖、不评判
5. 最后检查所有字段长度不超限
```

### 7.3 输出示例

以下是一个面向 24-36 个月、重点关注层级、计划焦点为"情绪过渡与共同调节"、本周完成率 71% 的完整输出示例：

```json
{
  "positive_changes": [
    {
      "title": "洗澡转场更顺了",
      "description": "本周有三天的记录显示，在洗澡前给了预告之后，孩子从"立刻升级"变为"虽然不高兴但更快接受"。身体强制介入减少了。",
      "supporting_evidence": "周三和周五的记录都提到'预告后哭闹时间缩短了，不需要抱起来'"
    },
    {
      "title": "开始接住情绪命名",
      "description": "有两次记录显示，当家长说'你还想玩'后，孩子会短暂停下来，比之前更容易进入下一步。",
      "supporting_evidence": "周四记录'说了你还想玩之后，他看了我一眼，然后自己走过去了'"
    }
  ],
  "opportunities": [
    {
      "title": "睡前转场仍然比较难",
      "description": "睡前从客厅到卧室的转场仍然是本周最高压的场景。虽然洗澡转场有改善，但睡前的预告似乎还没有被接受。下周可以尝试在这个场景用更短的预告和一个可预测的小动作。"
    },
    {
      "title": "换照护者后效果下降",
      "description": "周六爸爸尝试同样方法时效果不如平时。下周如果继续，可以让两位照护者先统一预告用语和停顿时间。"
    }
  ],
  "summary_text": "这一周在洗澡转场上出现了值得注意的变化，孩子对提前预告开始有了反应。虽然睡前场景还比较困难，但整体方向是朝着更好走的。",
  "decision_options": [
    {
      "id": "opt_continue",
      "text": "继续本周的预告练习",
      "value": "continue",
      "rationale": "洗澡转场已有改善，再巩固一周可以看到更稳定效果"
    },
    {
      "id": "opt_lower",
      "text": "保持方向但放慢节奏",
      "value": "lower_difficulty",
      "rationale": "如果感到执行吃力，可以只保留洗澡这一个场景，先不扩展到睡前"
    },
    {
      "id": "opt_change",
      "text": "换一个新的关注方向",
      "value": "change_focus",
      "rationale": "如果觉得情绪过渡不是目前最紧迫的，可以先回到表达支持或其他主题"
    }
  ],
  "conservative_path_note": "如果这周感觉整体节奏太紧，可以先暂停新的练习安排，只保留最自然的日常预告习惯。不需要每天都完成任务，保持稳定的亲子互动本身就是支持。",
  "referenced_record_ids": ["uuid-rec-001", "uuid-rec-003", "uuid-rec-005", "uuid-rec-007"],
  "referenced_plan_id": "uuid-plan-current"
}
```

## 八、模板选择逻辑

### 8.1 模板选择矩阵

按照《AI 输出结构草案 V1》的建议，V1 阶段每种 session_type 只维护 1 个通用模板，在模板内部通过条件分支处理差异。因此，模板选择矩阵简化为：

| session_type | 模板 ID | 模板版本 | 说明 |
|---|---|---|---|
| instant_help | `tpl_instant_help_v1` | 1.0.0 | 即时求助通用模板，内含 3 阶段 × 3 风险分支 |
| plan_generation | `tpl_plan_generation_v1` | 1.0.0 | 微计划生成通用模板，内含 3 阶段 × 3 风险分支 |
| weekly_feedback | `tpl_weekly_feedback_v1` | 1.0.0 | 周反馈通用模板，内含 3 阶段 × 3 风险分支 |

编排层在选择模板时的逻辑：

```
function selectTemplate(session_type, child_stage, child_risk_level):
    template = TEMPLATE_REGISTRY[session_type]  // V1 阶段每种类型只有 1 个
    return template.render(
        stage = child_stage,
        risk_level = child_risk_level,
        ... other context variables
    )
```

### 8.2 后续拆分时机

当以下任一条件满足时，应考虑将通用模板拆分为独立的阶段或风险级别模板：

| 拆分触发条件 | 说明 |
|---|---|
| **条件分支块超过总模板长度的 40%** | 分支过多说明各阶段差异已大到不适合共用一个模板 |
| **特定阶段的输出质量指标持续低于其他阶段** | 通用模板可能无法充分传达某阶段的特殊要求 |
| **内容团队确认各阶段需要不同的语气和内容策略** | 产品层面的差异化需求 |
| **Token 成本优化需要** | 拆分后每个模板更短，减少不必要的条件分支文本消耗 |

## 九、版本管理与模板生命周期

### 9.1 版本号规则

模板版本采用语义版本号（major.minor.patch）：

| 变更级别 | 版本号变化 | 示例 |
|---|---|---|
| **重大变更**：输出 schema 字段增减、角色定义重写 | major +1 | 1.0.0 → 2.0.0 |
| **功能变更**：新增条件分支、调整约束规则 | minor +1 | 1.0.0 → 1.1.0 |
| **修正变更**：措辞优化、示例更新、长度微调 | patch +1 | 1.0.0 → 1.0.1 |

### 9.2 模板变更流程

```
1. 内容/工程团队提出模板变更需求
   ↓
2. 在非生产环境做 A/B 测试（新旧模板各跑 100+ 请求）
   ↓
3. 比对关键指标：结构解析成功率、边界检查通过率、输出质量评分
   ↓
4. 人工抽检 10-20 个输出样本
   ↓
5. 更新模板版本号，写入 TEMPLATE_REGISTRY
   ↓
6. 渐进灰度发布（先 10% → 50% → 100%）
   ↓
7. 旧版本保留 30 天，支持审计回溯
```

### 9.3 与 OutputMetadata 的关联

每次 AI 调用的 OutputMetadata 都应记录使用的模板版本：

| OutputMetadata 字段 | 说明 |
|---|---|
| `prompt_template_version` | 本次调用使用的模板版本号（如 `tpl_instant_help_v1/1.0.0`） |
| `model_provider` | 模型供应商标识 |
| `model_version` | 模型版本 |
| `boundary_check_passed` | 边界检查是否通过 |
| `boundary_check_flags` | 被标记的检查项列表 |

## 十、Prompt 层面的质量保障

### 10.1 模板自检清单

每次模板变更前，应对照以下清单逐项确认：

| 检查项 | 检查内容 | 通过标准 |
|---|---|---|
| **角色定义完整性** | 是否明确了助手定位和边界 | 角色定义中包含"不是诊断工具""不是治疗师" |
| **输出格式前置** | JSON schema 是否在上下文注入之前 | 模型在看到上下文之前就知道输出格式 |
| **非诊断化指令完整** | 禁用词列表、替代表达、语气要求是否完整 | 包含全部 6 类禁用词和对应替代 |
| **阶段分支覆盖** | 是否覆盖了 3 个年龄阶段 | 18_24m / 24_36m / 36_48m 各有一个分支块 |
| **风险分支覆盖** | 是否覆盖了 3 个风险层级 | normal / attention / consult 各有一个分支块 |
| **字段约束明确** | 每个字段的最大长度和必填/可选是否标注 | 所有字段都有明确约束 |
| **输出示例完整** | 是否附带至少一个完整的输出示例 | 示例符合全部约束 |
| **占位符完整** | 所有需注入的变量是否都有占位符 | 无遗漏的上下文变量 |
| **与 AI 输出结构草案一致** | 字段名、类型、枚举值是否对齐 | 无命名或类型差异 |
| **与数据结构草案一致** | 上下文变量与 ContextSnapshot 字段对齐 | 无遗漏或多余的上下文字段 |

### 10.2 模板效果监控

以下指标应按模板版本分组统计，用于评估模板变更的效果：

| 指标 | 计算方式 | 健康阈值 | 说明 |
|---|---|---|---|
| **结构解析成功率** | 首次 JSON 解析成功 / 总请求 | > 95% | 低于阈值说明模板的格式约束不够清晰 |
| **边界检查首次通过率** | 首次边界检查全通过 / 总请求 | > 90% | 低于阈值说明非诊断化指令不够具体 |
| **字段截断率** | 需截断字段数 / 总字段数 | < 3% | 高于阈值说明长度约束传达不够明确 |
| **正确字段数量率** | day_tasks=7, decision_options=3 等 | > 98% | 低于阈值说明数量约束需加强 |
| **降级率** | 最终返回降级结果 / 总请求 | < 5% | 综合指标 |
| **平均延迟** | 按 session_type 分组 | 即时求助 < 6s / 计划 < 20s / 反馈 < 15s | 超出阈值可能需要精简模板 |

### 10.3 常见失败模式与模板优化方向

| 失败模式 | 典型表现 | 模板优化方向 |
|---|---|---|
| **模型输出自由文本而非 JSON** | 返回自然语言段落而非 JSON 对象 | 在格式约束中增加"你只返回 JSON，不返回任何其他文字"的强调 |
| **字段超长** | body 或 description 超过最大字符数 | 在字段约束旁增加"如果超过 N 字符，请缩短到 N 字符以内" |
| **诊断性语言渗透** | 出现"可能是""疑似""落后"等表达 | 在禁用词列表中增加更多变体形式 |
| **三步结构不聚焦** | step_one/step_two/step_three 内容重叠 | 在每步的指令中更强调聚焦方向 |
| **7 天任务重复** | Day 1-7 的内容高度相似 | 在七日节奏指令中更强调每天的差异点 |
| **积极变化编造** | supporting_evidence 引用了不存在的记录 | 增加"evidence 必须能在上面的记录摘要中找到对应内容"的指令 |
| **选项情感偏向** | lower_difficulty 被描述为"放弃"或"退步" | 增加"三个选项必须语气平等，不暗示任何选项是更差的"的指令 |

## 十一、与已有文档的对齐验证

### 11.1 与 AI 输出结构草案 V1 的对齐

| 验证项 | 状态 | 说明 |
|---|---|---|
| InstantHelpResult schema 字段完全一致 | 通过 | step_one/two/three, scenario_summary, suggest_*, boundary_note, metadata |
| PlanGenerationResult schema 字段完全一致 | 通过 | title, primary_goal, focus_theme, priority_scenes, day_tasks[7], observation_candidates, weekend_review_prompt, conservative_note |
| WeeklyFeedbackResult schema 字段完全一致 | 通过 | positive_changes(含 supporting_evidence), opportunities, summary_text, decision_options(含 rationale), conservative_path_note, referenced_* |
| 字段约束（长度、数量）完全一致 | 通过 | 所有约束均从 AI 输出结构草案原样引入 |
| 降级策略引用一致 | 通过 | 各模板的降级逻辑与草案定义一致 |
| 超时阈值一致 | 通过 | 即时求助 8s / 计划 30s / 反馈 20s |

### 11.2 与数据结构草案 V1 的对齐

| 验证项 | 状态 | 说明 |
|---|---|---|
| ContextSnapshot 字段完全覆盖 | 通过 | child_age_months, child_stage, child_focus_themes, child_risk_level, active_plan_id, active_plan_day, recent_record_ids, recent_record_keywords |
| FeedbackItem.supporting_evidence 字段对齐 | 通过 | Prompt 模板中 positive_changes 的 supporting_evidence 与数据结构一致 |
| DecisionOption.rationale 字段对齐 | 通过 | Prompt 模板中 decision_options 的 rationale 与数据结构一致 |
| 枚举值一致 | 通过 | stage / risk_level / focus_theme / CompletionStatus / DecisionValue 枚举均一致 |

### 11.3 与组件接口定义 V1 的对齐

| 验证项 | 状态 | 说明 |
|---|---|---|
| A-4 ThreeStepResultCard 消费路径 | 通过 | step_one/two/three 的 title, body, example_script 可直接映射到 SummaryCard Props |
| A-5 FollowUpActionBar 消费路径 | 通过 | suggest_record, suggest_add_focus, suggest_consult_prep 控制按钮可见性 |
| P-4 DailyTaskPanel 消费路径 | 通过 | day_tasks 各字段可直接映射到 SplitInfoPanel + SummaryCard |
| F-2/F-3/F-4/F-5 消费路径 | 通过 | positive_changes → SummaryCard, opportunities → SummaryCard, decision_options → SelectableTagGroup, conservative_path_note → SummaryCard(dashed) |

### 11.4 与观测模型和微计划模板的对齐

| 验证项 | 状态 | 说明 |
|---|---|---|
| 六主题覆盖 | 通过 | focus_theme 枚举覆盖六个一级主题 |
| 三阶段适配 | 通过 | 每个模板包含 18_24m / 24_36m / 36_48m 条件分支 |
| 三级风险分层 | 通过 | 每个模板包含 normal / attention / consult 条件分支 |
| 八类干预焦点 | 通过 | 微计划模板的阶段指令中涵盖了干预焦点的内容方向 |
| 七日节奏 | 通过 | 微计划模板中完整嵌入了统一七日节奏指令 |
| 家长语言风格 | 通过 | 三类模板均嵌入了语言风格指令 |

## 十二、结论

到这一版为止，三类 AI 输出（即时求助、微计划生成、周反馈）都有了可直接使用的 Prompt 模板文本。每个模板都包含完整的角色定义、输出格式约束、上下文注入规范、阶段与风险适配分支、非诊断化边界指令和输出示例。编排层工程师可以直接将这些模板复制到代码中，通过占位符替换完成 Prompt 拼装。

| 结论项 | 结果 |
|---|---|
| **模板数量** | 3 个通用模板（各含条件分支） |
| **模板 ID** | tpl_instant_help_v1 / tpl_plan_generation_v1 / tpl_weekly_feedback_v1 |
| **上下文注入变量** | 12 个通用占位符 + 各场景专属占位符 |
| **非诊断化指令** | 6 类禁用词 + 对应替代表达 + 语气要求（统一复用块） |
| **阶段分支** | 3 × 3（18_24m / 24_36m / 36_48m × normal / attention / consult）= 每模板 9 种组合 |
| **输出示例** | 每类模板 1 个完整示例 |
| **自检清单** | 10 项 |
| **监控指标** | 6 个核心指标 |
| **与已有文档对齐** | AI 输出结构 / 数据结构 / 组件接口 / 观测模型 / 微计划模板全部通过 |

| 推荐下一步 | 产出目标 |
|---|---|
| **端到端联调草案** | 把数据结构 + AI 输出 + 组件接口 + Prompt 模板串成完整联调清单 |
| **组件库代码启动** | 基于组件接口定义开始实现 9 个通用组件 |
| **模板 A/B 测试框架** | 搭建模板版本灰度和效果对比的基础设施 |
| **高保真设计启动** | 基于组件拆解和接口定义进入视觉设计层 |
