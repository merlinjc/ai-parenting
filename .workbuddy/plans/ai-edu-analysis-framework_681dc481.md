---
name: ai-edu-analysis-framework
overview: 围绕该项目与猿辅导、作业帮的差异化定位，先完成一轮更深入的思路梳理与论证框架设计，再决定后续是否展开成正式分析稿或汇报稿。重点是把比较维度、核心论点、证据链与未来趋势判断先捋顺。
todos:
  - id: research-evidence
    content: 用 [skill:deep-research] 复核已有结论与行业证据
    status: completed
  - id: thesis-matrix
    content: 用 [skill:brainstorming] 收敛主论点和比较矩阵
    status: completed
    dependencies:
      - research-evidence
  - id: outline-structure
    content: 用 [skill:doc-coauthoring] 搭建提纲骨架与章节顺序
    status: completed
    dependencies:
      - thesis-matrix
  - id: audience-tone
    content: 用 [skill:professional-communication] 校准受众与论证口径
    status: completed
    dependencies:
      - outline-structure
  - id: key-lines
    content: 用 [skill:writing-clearly-and-concisely] 提炼标题句与关键判断
    status: completed
    dependencies:
      - audience-tone
---

## User Requirements

基于当前 AI 育儿助手项目的立意，继续深化它与猿辅导、作业帮这类教育产品的差异分析，并进一步梳理“未来 AI 与教育结合会往哪里走”的讨论框架。当前目标不是直接成文，而是先把思路、论点、比较维度和趋势主线捋清楚。

## Product Overview

本次产出应以“结构化分析框架”为主，形成一个可讨论、可扩写、可继续打磨的提纲。内容上要先明确项目的核心立意，再建立与主流 K12 教育产品的对照关系，最后过渡到 AI 教育未来演进趋势。整体呈现应清晰、有层次，便于后续扩展成正式文章或汇报材料。

## Core Features

- 明确本项目的核心立意：非诊断化、陪伴式、面向家庭互动与儿童发展
- 建立与猿辅导、作业帮的核心比较框架，而非仅做功能罗列
- 收敛一个更有说服力的主论点：这不是细分年龄产品，而是不同的 AI 教育范式
- 梳理未来 AI 教育的发展趋势主线，突出从“知识传递”走向“家庭系统支持”和“全人发展支持”
- 先形成讨论提纲与论证顺序，暂不急于展开成完整长文

## Agent Extensions

### Skill

- **deep-research**
- Purpose: 复核项目立意、已有分析与外部行业信号，补齐高可信论据
- Expected outcome: 形成可支撑后续判断的事实底座，并控制趋势判断不过度外推

- **brainstorming**
- Purpose: 发散并收敛中心论点、比较维度、趋势叙事路径
- Expected outcome: 得到更稳的论证框架，避免只停留在功能对比层面

- **doc-coauthoring**
- Purpose: 以文稿共创方式搭建提纲骨架、章节顺序与问题树
- Expected outcome: 形成适合后续继续写作的结构化提纲，而不是松散笔记

- **professional-communication**
- Purpose: 从真实读者视角校准表达口径、受众层级与信息组织方式
- Expected outcome: 让后续内容既能打动非技术读者，也能经得住专业讨论

- **writing-clearly-and-concisely**
- Purpose: 压缩空话、强化句子力度、提炼结论表达
- Expected outcome: 让提纲标题、核心判断和过渡语更清楚、更有力