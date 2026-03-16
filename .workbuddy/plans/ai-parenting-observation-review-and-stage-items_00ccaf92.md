---
name: ai-parenting-observation-review-and-stage-items
overview: 复核现有观测模型结构稿，补足缺失的判定与记录细节，并在此基础上展开 18—48 个月三个年龄阶段的具体观察项框架。
todos:
  - id: review-model-gaps
    content: 使用 [skill:brainstorming] 复盘观测模型结构稿缺口
    status: completed
  - id: refine-model-rules
    content: 修订观测模型的字段边界、证据规则与误判控制
    status: completed
    dependencies:
      - review-model-gaps
  - id: build-age-framework
    content: 展开三年龄段观察项框架并预留干预映射槽位
    status: completed
    dependencies:
      - refine-model-rules
  - id: sync-summary
    content: 使用 [skill:writing-clearly-and-concisely] 更新 overview.md
    status: completed
    dependencies:
      - build-age-framework
---

## User Requirements

### User Requirements

- 先对现有《观测模型结构稿 V1》做一次完整 review，确认是否还缺少关键细节、边界说明和判断条件。
- review 完成后，不改变“发育观察 + AI 轻干预教练”的产品定位，继续推进下一步内容，而不是先进入页面原型。
- 输出内容需保持专业、克制、非诊断化表达，便于后续继续承接年龄分层观察项与干预映射。

### Product Overview

本轮工作聚焦文档深化，不新增产品方向。核心是把现有观测模型从“结构完整”推进到“可直接落地承接下一层设计”，重点补齐记录边界、误判控制、证据充分性、跨照护者口径与后续接口定义。

呈现形式应保持结构清晰、层级明确，以章节说明、规则表格和阶段框架为主，方便后续继续扩展年龄段观察项与干预模型。

### Core Features

- 观测模型复盘：检查主题树、记录单元、状态规则、风险分层是否仍有缺口。
- 关键细节补强：明确最小必填字段、可选补充字段、证据不足处理、单场景偏差与观察频率不足的控制条件。
- 阶段化衔接：在稳定模型基础上，为 18—24、24—36、36—48 个月观察项展开建立统一框架。
- 干预接口预留：补充每个主题后续需要输出的标准化映射槽位，便于继续生成微计划、话术与转介条件。
- 文档同步沉淀：把 review 结论、修订范围和下一步承接关系同步到会话概览。

## Agent Extensions

### Skill

- **brainstorming**
- Purpose: 用于收敛观测模型 review 的重点缺口、补充边界与下一步展开范围。
- Expected outcome: 得到稳定的补强清单，明确哪些内容需要修订、哪些内容进入下一阶段展开。

- **writing-clearly-and-concisely**
- Purpose: 用于统一修订后文档的表达方式、风险提示语气和章节结构。
- Expected outcome: 形成更简洁、专业、可执行的文档表述，并保证 overview.md 与主文档口径一致。