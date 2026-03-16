---
name: ai-parenting-7day-microplan-v1
overview: 围绕已完成的三阶段观察模型与具体观察项清单，规划下一步《7 天微计划模板 V1》的文档设计，重点明确干预焦点、家庭场景、示范话术、复盘信号与升级门槛。
todos:
  - id: align-doc-basis
    content: 使用 [skill:brainstorming] 对齐模型、清单与微计划槽位
    status: pending
  - id: draft-weekly-template
    content: 新建 ai_parenting_micro_plan_template_v1.md 统一七日模板
    status: pending
    dependencies:
      - align-doc-basis
  - id: expand-eight-focuses
    content: 补齐八类干预焦点的三阶段适配与每日动作
    status: pending
    dependencies:
      - draft-weekly-template
  - id: wire-safety-boundaries
    content: 对齐复盘信号、升级门槛、不适用条件与求助入口
    status: pending
    dependencies:
      - expand-eight-focuses
  - id: sync-overview-doc
    content: 使用 [skill:writing-clearly-and-concisely] 更新 overview.md
    status: pending
    dependencies:
      - wire-safety-boundaries
---

## User Requirements

### User Requirements

- 在已完成《观测模型结构稿 V1.1》和《三阶段具体观察项清单 V1》之后，继续推进下一步，产出 **7 天微计划模板 V1**。
- 保持既有产品定位不变：面向家长端的发育观察与 AI 轻干预教练，不进入页面原型，不转向代码实现。
- 微计划需与既有六个主题、三个年龄阶段、三层记录单元、三级风险表达和八类干预焦点保持一致。
- 表达方式需继续保持专业、克制、非诊断化，强调低屏幕、强亲子、线下执行优先。

### Product Overview

本轮产出应是一份可直接承接后续产品设计的微计划文档，核心内容是把观察结果翻译成家长可执行的 7 天支持方案。文档应以章节和表格为主，清晰展示每类微计划的适用场景、每日动作、示范话术、复盘信号和升级边界。

整体呈现应结构稳定、复用性强，便于后续继续衔接即时话术、周反馈和页面信息架构。

### Core Features

- 统一 7 天微计划模板：固定每个计划都要包含的核心槽位与每日节奏。
- 三阶段适配规则：区分 18—24、24—36、36—48 个月的任务强度与表达方式。
- 八类干预焦点展开：把等待回应、选择表达、动作模仿等焦点转成可执行周计划。
- 观察与行动对齐：让微计划可回接观察项、记录方式和主题趋势。
- 安全边界说明：明确复盘信号、升级门槛、不适用条件与咨询提示口径。

## Agent Extensions

- **brainstorming**
- Purpose: 收敛 7 天微计划的统一骨架、八类焦点结构和三阶段差异边界。
- Expected outcome: 形成稳定、不过度复杂、可直接落文档的模板框架。

- **writing-clearly-and-concisely**
- Purpose: 统一微计划文档与会话概览的表达风格，保持克制、清晰、可执行。
- Expected outcome: 生成专业、简洁、非诊断化且便于产品继续承接的文档内容。