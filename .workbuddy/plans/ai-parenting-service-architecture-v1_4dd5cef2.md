---
name: ai-parenting-service-architecture-v1
overview: 在既有观察模型、微计划模板与示范周计划基础上，补充一份面向 iOS 客户端、业务后端、AI 编排与推送链路的整体服务架构文档，为后续页面信息架构提供稳定的系统边界。
todos:
  - id: align-service-scope
    content: 使用 [skill:brainstorming] 收敛 iOS、后端、AI、推送边界
    status: completed
  - id: scaffold-architecture-doc
    content: 使用 [skill:doc-coauthoring] 搭建 ai_parenting_service_architecture_v1.md 章节骨架
    status: completed
    dependencies:
      - align-service-scope
  - id: draft-service-layers
    content: 完成分层架构、模块职责与四条核心链路章节
    status: completed
    dependencies:
      - scaffold-architecture-doc
  - id: add-safety-and-evolution
    content: 补齐安全边界、状态回流与后续演进策略
    status: completed
    dependencies:
      - draft-service-layers
  - id: sync-overview-architecture
    content: 使用 [skill:writing-clearly-and-concisely] 更新 overview.md
    status: completed
    dependencies:
      - add-safety-and-evolution
---

## User Requirements

- 在进入页面信息架构之前，先补齐一份整体服务架构文档，明确系统不是单纯内容方案，而是由移动端入口、服务端能力、AI 调用链路和消息触达链路共同组成。
- 用户主入口为 iOS 应用，基础使用都在该端完成；服务端负责登录注册、保存用户与家庭互动信息、承接 AI 能力调用、完成消息推送与状态回流。
- 新文档需承接既有《产品设计草案》《观察模型》《观察项清单》《7 天微计划模板》《7 天微计划示范样稿》，与当前“观察—微计划—周反馈—即时求助”链路保持一致。
- 本轮仍以文档固化为主，不进入页面原型、接口细节穷举或代码实现；表达继续保持专业、克制、非诊断化。

## Product Overview

本轮产出应是一份可直接衔接后续页面信息架构的《整体服务架构草案 V1》。文档重点说明各层能力边界、核心模块职责、主要数据流和关键闭环，让“家长端使用什么、服务端负责什么、AI 在哪里接入、推送如何触达”变得清楚稳定。

整体呈现应继续采用结构化章节、职责表和流程表，阅读上清晰、复用性强，便于后续继续承接页面结构、数据结构和生成逻辑。

## Core Features

- 明确整体分层：客户端、业务后端、AI 编排层、外部服务的职责边界。
- 固化核心模块：账户体系、儿童与家庭档案、观察记录、微计划、AI 交互、消息推送。
- 梳理关键闭环：登录与设备绑定、记录沉淀、AI 输出回写、提醒触达与回流。
- 对齐安全边界：非诊断化表达、服务端统一调用 AI、数据保存范围与风险升级链路。
- 说明承接关系：服务架构如何支撑后续页面信息架构与产品输出链路。

## Tech Stack Selection

当前产出形态已验证为一组持续演进的 Markdown 文档，现有主文档包括：

- `/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/ai_parenting_product_design.md`
- `/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/ai_parenting_7day_microplan_v1.md`
- `/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/ai_parenting_7day_microplan_examples_v1.md`
- `/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/overview.md`

本次继续沿用“独立主文档 + overview 同步”的文档模式。

建议的目标技术组合如下，用于固化服务架构方向而非立即进入实现：

- 客户端：iOS 原生应用，建议 SwiftUI 作为主要界面层，基础交互、消息承接、本地轻缓存均在端上完成
- 服务端：建议 Python + FastAPI 作为统一 API 服务，先采用模块化单体
- 数据层：PostgreSQL 存储账户、儿童档案、观察记录、计划状态、会话摘要
- 异步层：Redis + 任务队列处理推送调度、AI 重试、周反馈生成
- 外部依赖：AI 服务商 OpenAPI、Apple Push Notification service

## Implementation Approach

### High-level Strategy

采用“先固化边界、再固化链路、最后固化演进路径”的方式撰写服务架构文档。文档先明确 iOS 端、业务后端、AI 编排层和推送链路的分工，再把登录、记录、计划、AI、推送几条关键闭环串起来，最终给出适合当前阶段的服务形态。

### Key Technical Decisions

- **后端先采用模块化单体**：当前产品仍在定义期，先把账户、记录、计划、AI、通知这些领域模块放在同一后端内，更利于快速收敛；比直接拆微服务更低风险、更易维护。
- **AI 只走服务端代理**：客户端不直接调用模型服务。这样可以统一管理密钥、Prompt 模板、上下文拼装、结果结构化、供应商切换、失败重试与审计边界。
- **同步接口 + 异步任务分层**：登录、读取、记录保存走同步 API；AI 长耗时处理、周反馈生成、消息推送走异步任务，避免关键页面被外部模型延迟拖慢。
- **文档保持实现友好但不过度下沉**：本轮聚焦模块关系、数据流、边界与演进策略，不展开到接口字段表或页面原型，避免过早锁死细节。

### Performance and Reliability

- 账户、档案、记录、计划状态的常规读写以单用户、单儿童、单计划维度为主，主路径复杂度可控制在 O(1) 到 O(n) 窗口聚合范围内。
- 主要性能瓶颈在外部 AI 响应延迟，而非数据库本身；通过超时、重试、幂等键、异步化和失败降级控制体验波动。
- 周反馈、趋势聚合、推送调度应按时间窗批处理，避免每次记录后都全量重算。
- 推送链路需保留送达记录和点击回流，便于后续验证提醒效果并减少无效消息。

### Avoiding Technical Debt

- 复用现有文档命名和组织方式，不打散已有内容链路。
- 不引入新的产品主模式，继续围绕“发育观察 + AI 轻干预教练”展开。
- 不在文档中提前拆解过细服务或接口，保留后续按调用量和团队协作再拆分的空间。

## Implementation Notes

- 继续沿用现有文档风格：主标题、章节说明、表格化职责与边界、验证式表达。
- 关键术语保持与既有文档一致：观察、微计划、周反馈、即时求助、风险分层、转介。
- AI 相关章节只描述能力边界和调用路径，不写诊断化承诺，不把儿童作为独立高频交互对象。
- 安全边界需前置写明：鉴权、密钥只在服务端、输入校验、敏感数据最小化保存、日志避免泄露家庭隐私。
- 变更范围控制在新增独立服务架构文档和同步 overview，避免回头重写已稳定的产品与微计划文档。

## Architecture Design

### System Structure

建议在文档中固化以下四层结构：

- **iOS 应用层**
- 登录注册
- 儿童与家庭档案
- 观察记录与计划查看
- AI 交互入口
- 消息承接与回流

- **业务后端层**
- 账户与鉴权
- 档案管理
- 观察记录与趋势聚合
- 微计划与周反馈状态管理
- 消息任务调度

- **AI 编排层**
- Prompt 模板管理
- 上下文拼装
- 模型供应商适配
- 结果结构化
- 风险边界与失败降级

- **外部服务层**
- AI 服务商 OpenAPI
- APNs 推送通道

### Core Flows

文档应至少覆盖四条核心链路：

1. **账户链路**：注册登录、鉴权、设备绑定、会话续期  
2. **记录链路**：观察输入、结构化保存、状态更新、周反馈聚合  
3. **AI 链路**：上下文组装、模型调用、结果标准化、会话回写  
4. **消息链路**：事件触发、定时调度、推送送达、点击回流

### Recommended Module Boundaries

- 账户与身份模块
- 家庭与儿童档案模块
- 观察与记录模块
- 微计划与任务模块
- AI 会话与编排模块
- 通知与消息模块
- 审计与运营支持模块

## Directory Structure

### Directory Structure Summary

本次不是代码实现，而是继续补强文档体系。建议只新增一份服务架构主文档，并同步更新总览文档。

- `/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/ai_parenting_service_architecture_v1.md`  [NEW] 整体服务架构主文档。用于固化客户端、业务后端、AI 编排层、推送链路的分层关系，明确核心模块职责、关键数据流、边界控制和后续页面信息架构的承接点。实现上应延续现有文档写法，以章节和表格为主，不展开页面原型或接口实现细节。

- `/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/overview.md`  [MODIFY] 会话概览同步文档。用于记录本轮新增服务架构文档后的系统边界、模块划分、关键验证结论，以及它与既有观察模型、微计划模板、示范样稿和后续页面信息架构之间的关系。实现上应保持现有概览结构与简洁风格。

## Agent Extensions

### Skill

- **brainstorming**
- Purpose: 收敛 iOS 端、业务后端、AI 编排层与推送链路的职责边界
- Expected outcome: 形成稳定、不过度复杂的服务架构文档骨架与关键判断

- **doc-coauthoring**
- Purpose: 以结构化文档方式组织服务架构章节顺序、读者视角与承接关系
- Expected outcome: 输出适合后续继续扩写、评审和映射页面信息架构的文档结构

- **writing-clearly-and-concisely**
- Purpose: 统一服务架构文档与 overview 的表达风格，保持克制、清晰、可执行
- Expected outcome: 生成专业、简洁、便于后续产品与架构承接的文档文本