---
name: ai-parenting-page-prototype-design
overview: 为已确定的“发育观察 + AI轻干预教练”产品形成专业、逻辑清晰的页面原型设计方案，重点覆盖信息架构、核心页面结构、关键交互链路与专业表达规范。
design:
  architecture:
    framework: react
    component: shadcn
  styleKeywords:
    - 专业育儿服务
    - 移动端优先
    - 温和低焦虑
    - 清晰层级
    - 轻量卡片化
    - 可解释交互
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 28px
      weight: 600
    subheading:
      size: 18px
      weight: 600
    body:
      size: 15px
      weight: 400
  colorSystem:
    primary:
      - "#4F7BFF"
      - "#6E9CFF"
      - "#6BCB9A"
    background:
      - "#F6F8FC"
      - "#FFFFFF"
      - "#EEF4FF"
    text:
      - "#1F2A37"
      - "#4B5563"
      - "#FFFFFF"
    functional:
      - "#22C55E"
      - "#F59E0B"
      - "#EF4444"
      - "#4F46E5"
todos:
  - id: align-prototype-scope
    content: 使用 [skill:brainstorming] 固化五页原型范围与信息优先级
    status: pending
  - id: map-page-logic
    content: 梳理 ai_parenting_product_design.md 的页面职责与主流程
    status: pending
    dependencies:
      - align-prototype-scope
  - id: design-core-pages
    content: 使用 [skill:frontend-design] 设计首页、记录页、AI计划页原型
    status: pending
    dependencies:
      - map-page-logic
  - id: design-support-pages
    content: 使用 [skill:frontend-design] 设计即时求助与风险转介页原型
    status: pending
    dependencies:
      - design-core-pages
  - id: compile-prototype-doc
    content: 沉淀 ai_parenting_page_prototype.md 的信息架构与页面说明
    status: pending
    dependencies:
      - design-support-pages
  - id: polish-copy-and-summary
    content: 使用 [skill:writing-clearly-and-concisely] 统一文案并更新 overview.md
    status: pending
    dependencies:
      - compile-prototype-doc
---

## User Requirements

- 继续沿用“发育观察 + AI轻干预教练”路线，面向 18—48 个月幼儿的家长端产品。
- 在已完成的产品方案基础上，进一步细化页面原型，而不是改动产品定位。
- 页面设计需要同时满足两点：一是逻辑清晰，能把“观察、判断、干预、提醒、转介”串成完整闭环；二是专业可信，体现发展阶段、风险分层和家长指导的严谨性。

## Product Overview

产品以家长为主要使用者，围绕孩子阶段画像、本周重点、轻量记录、AI 微计划、即时话术支持和风险提醒展开。页面应帮助家长快速理解“现在该看什么、今天该做什么、出现异常怎么办”。

视觉上应避免儿童内容平台的娱乐化风格，采用温和、专业、低焦虑的表达，兼顾医疗服务的可信度与家庭陪伴的温度。

## Core Features

- 阶段主页：按月龄展示当前阶段重点、趋势摘要和本周任务。
- 观察记录：用低负担方式记录语言、动作、情绪、社交等真实片段。
- AI 干预计划：将观察结果转为 7 天家庭微计划与亲子活动建议。
- 即时求助：针对哭闹、拒绝、不开口等高频问题提供话术和处理节奏。
- 风险提醒：区分正常波动、重点关注和建议转介，明确下一步动作。

## Tech Stack Selection

- 当前阶段基于已存在的 Markdown 设计产物继续深化页面原型，不直接进入代码开发。
- 若后续需要可交互原型，优先采用移动端优先的 React 原型方式，便于承接页面结构、组件复用与后续实现。

## Implementation Approach

- 以现有文档 `/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/ai_parenting_product_design.md` 为唯一产品基线，把“五个核心模块”映射为 5 个主页面。
- 先完成信息架构，再做页面块级原型，最后统一文案规范、状态定义和跨页流转，避免页面漂亮但逻辑断裂。
- 关键决策：坚持家长端、低屏幕、线下执行优先；风险页独立呈现，避免与日常建议混杂；首页承担“判断中枢”，记录页承担“输入中枢”。

## Implementation Notes

- 沿用既有三阶段结构：18—24、24—36、36—48 个月，不新增脱离现有研究依据的能力线。
- 所有页面文案都要避免诊断化表达，统一为“观察建议、重点关注、建议咨询”三级。
- 原型优先展示低认知负担路径，避免一次页面中出现过多图表、术语或操作入口。

## Architecture Design

- 页面关系：阶段主页进入记录、AI 计划、即时求助、趋势与风险；记录结果反向更新主页与周反馈。
- 信息流：家长输入观察片段 → 系统生成阶段判断与主题聚合 → AI 输出微计划与话术 → 风险模块做分层提醒与转介建议。
- 结构重点：全局保持统一底部导航与阶段上下文，任何页面都能返回“本周重点”。

## Directory Structure

## Directory Structure Summary

本次工作以现有设计文档为基础，补充一份页面原型规格文档，并同步更新会话概览。

`/Users/tanghan/Library/Application Support/WorkBuddy/User/globalStorage/tencent-cloud.coding-copilot/brain/8ac2d304540345c08966c7afc14a53f6/`

- `ai_parenting_product_design.md`  [MODIFY] 现有产品方案主文档。补充页面层级、页面职责映射、跨页流转说明，确保原型与既有产品逻辑一致。
- `ai_parenting_page_prototype.md`  [NEW] 页面原型规格文档。沉淀信息架构、5 个核心页面的区块设计、关键状态、交互路径、文案原则与风险提示规范。
- `overview.md`  [MODIFY] 会话概览文档。记录本轮页面原型设计范围、主要输出物和下一步交付方向。

## 设计定位

移动端家长应用原型，强调“专业可信 + 温和支持”。整体风格偏医疗服务与家庭教练的中间地带，不做卡通堆砌，不制造焦虑感。

## 设计风格

以简洁留白、柔和蓝绿、卡片分层和轻提示交互为主。核心信息优先级明确：先看阶段重点，再做记录，再看建议，最后处理风险。

## 页面规划

### 1. 阶段主页

- 顶部导航：孩子头像、月龄、当前阶段标签、通知入口。
- 阶段摘要卡：展示本周重点主题与一句阶段判断。
- 趋势概览区：用简洁条形或标签呈现近期变化。
- 今日行动区：记录入口、AI 计划、即时求助三个主按钮。
- 底部导航：主页、记录、计划、求助、我的。

### 2. 观察记录页

- 顶部导航：返回、日期切换、记录方式切换。
- 快速勾选区：语言、动作、情绪、社交四类观察项。
- 事件记录区：支持简短文字与语音转写摘要。
- 引导提示区：提示如何描述具体行为而非主观判断。
- 底部导航：保持全局一致，降低跳转成本。

### 3. AI 干预计划页

- 顶部导航：阶段标签、计划周期、编辑入口。
- 本周目标卡：只展示 1—2 个核心干预目标。
- 7 天微计划区：按日呈现活动、话术、时长和场景。
- 解释说明区：说明为何推荐这类活动。
- 底部导航：可快速返回记录或即时求助。

### 4. 即时求助页

- 顶部导航：问题分类、搜索、最近问题。
- 高频问题区：不开口、哭闹、过渡崩溃、见人躲避等。
- 三步应对卡：先说什么、接着做什么、无效时怎么调。
- 话术示例区：展示家长可直接复用的表达。
- 底部导航：支持一键回到当前计划。

### 5. 趋势与风险页

- 顶部导航：趋势、提醒、转介三个页签。
- 能力趋势区：按主题显示稳定、波动、需关注状态。
- 风险分层区：正常波动、重点关注、建议咨询三层。
- 下一步建议区：继续观察、补充记录、咨询专业人员。
- 底部导航：与全局一致，保证闭环浏览。

## 交互原则

- 首屏只呈现最重要的下一步动作。
- 重要提示先解释原因，再给行动建议。
- 风险表达克制，不使用诊断式结论。
- 关键按钮固定位置，形成稳定操作习惯。

## Agent Extensions

### Skill

- **brainstorming**
- Purpose: 先收敛页面范围、核心页面数量与信息优先级，避免原型扩散。
- Expected outcome: 得到稳定的页面边界、页面职责和跨页主流程。
- **frontend-design**
- Purpose: 产出具有专业感、层级清晰的移动端页面原型方案。
- Expected outcome: 形成可直接落地的页面结构、区块布局和视觉风格规范。
- **writing-clearly-and-concisely**
- Purpose: 统一页面文案、按钮文案、提醒语和风险提示语气。
- Expected outcome: 页面文字简洁、专业、可执行，减少歧义和焦虑感。