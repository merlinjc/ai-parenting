# AI Parenting — AI 育儿助手

> 不做诊断工具、不做治疗师，像一位有经验的朋友，帮助家长在日常生活中创造更多高质量亲子互动机会。

**AI Parenting** 是一款面向 **18–48 个月（1.5–4 岁）幼儿家长**的 AI 辅助型育儿产品，包含 Python 后端服务与 iOS 原生客户端的全栈实现。

[English Version](./README_EN.md)

---

## 目录

- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [环境变量配置](#环境变量配置)
- [API 文档](#api-文档)
- [iOS 客户端](#ios-客户端)
- [测试](#测试)
- [安全设计](#安全设计)
- [许可证](#许可证)

---

## 核心功能

### 三大 AI 能力

| 功能 | 说明 | 超时策略 |
|------|------|----------|
| **即时求助** | 家长在高压时刻获得即时三步指导（稳住自己 → 立刻行动 → 后续观察） | 8 秒超时，重试后降级 |
| **微计划生成** | AI 生成 7 天家庭支持计划，每天 2 项任务，含示范话术和观察要点 | 30 秒超时 |
| **周反馈** | 计划完成后生成周度反馈报告，含正向变化识别和改进建议 | 20 秒超时 |

### 完整业务闭环

- **儿童档案管理**：按年龄自动划分三阶段（18–24月 / 24–36月 / 36–48月），支持六大关注主题（语言、社交、情绪、运动、认知、自理）
- **观察记录**：支持快速打点、事件记录、语音记录三种模式
- **消息中心**：计划提醒、记录提示、周反馈就绪、风险预警等系统通知
- **定时任务**：每日自动推进计划进度、发送任务提醒和记录提示
- **就医准备**：为家长准备就医所需材料
- **推送通知**：APNs 推送集成

---

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                   iOS 客户端                         │
│          SwiftUI · MVVM · iOS 17+                   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / JSON
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI 后端                         │
│  ┌────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ 路由层  │→│  服务层   │→│   AI 编排调度器      │  │
│  │12 模块  │  │ 11 服务  │  │ Prompt渲染→LLM调用  │  │
│  └────────┘  └──────────┘  │ →JSON解析→边界检查   │  │
│                             └─────────┬──────────┘  │
│  ┌────────────────┐  ┌────────────────▼──────────┐  │
│  │  SQLAlchemy    │  │    LLM Provider 适配层     │  │
│  │  异步 ORM      │  │  MockProvider / Hunyuan   │  │
│  └───────┬────────┘  └───────────────────────────┘  │
└──────────┼──────────────────────────────────────────┘
           │
    ┌──────▼───────┐
    │  SQLite (开发) │
    │  PostgreSQL   │
    │   (生产)      │
    └──────────────┘
```

| 层次 | 技术选型 |
|------|---------|
| **后端框架** | FastAPI (Python 3.11+) |
| **ORM** | SQLAlchemy 2.0 异步模式 |
| **数据库** | SQLite（开发）/ PostgreSQL（生产） |
| **数据校验** | Pydantic v2 |
| **认证** | JWT (python-jose) + bcrypt (passlib) |
| **定时任务** | APScheduler (AsyncIO) |
| **LLM 集成** | 腾讯混元大模型（OpenAI 兼容接口） |
| **iOS 客户端** | Swift 5.9 / SwiftUI / iOS 17+ |
| **iOS 架构** | MVVM + @Observable |
| **包管理** | Swift Package Manager / pip |
| **测试** | pytest + pytest-asyncio |

---

## 项目结构

```
ai-parenting/
├── pyproject.toml                 # Python 项目配置与依赖
├── src/ai_parenting/
│   ├── orchestrator.py            # AI 编排调度器（核心）
│   ├── renderer*.py               # Prompt 模板渲染器
│   ├── engine/
│   │   ├── boundary_checker.py    # 非诊断化安全边界检查
│   │   └── template_engine.py     # 条件模板引擎
│   ├── models/                    # 领域模型与枚举
│   ├── providers/                 # LLM 供应商适配层
│   │   ├── base.py                # 抽象接口
│   │   ├── mock_provider.py       # Mock（开发/测试）
│   │   └── hunyuan_provider.py    # 腾讯混元
│   ├── templates/                 # Prompt 模板常量
│   └── backend/
│       ├── app.py                 # FastAPI 入口
│       ├── config.py              # 配置管理
│       ├── models.py              # 9 个 ORM 模型
│       ├── schemas.py             # API Schema
│       ├── auth.py                # JWT 认证
│       ├── scheduler.py           # 定时任务调度
│       ├── routers/               # 12 个 API 路由模块
│       └── services/              # 11 个业务服务
├── ios/
│   ├── Package.swift              # SPM 配置
│   └── Sources/AIParenting/
│       ├── App/                   # 应用入口与全局状态
│       ├── Core/                  # 网络、认证、推送
│       ├── Features/              # 功能模块（MVVM）
│       ├── Models/                # Swift 数据模型
│       ├── Shared/                # 通用 UI 组件
│       └── Extensions/            # 扩展工具
└── tests/                         # 后端测试套件
```

---

## 快速开始

### 环境要求

- **Python** 3.11+
- **Xcode** 15+ / iOS 17+（运行 iOS 客户端）
- **SQLite**（开发环境自动使用）

### 后端启动

```bash
# 1. 克隆项目
git clone https://github.com/merlinjc/ai-parenting.git
cd ai-parenting

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 配置环境变量（可选，默认使用 Mock LLM）
cp .env.example .env
# 编辑 .env 填入腾讯混元 API Key（如需真实 AI 能力）

# 4. 启动服务
uvicorn ai_parenting.backend.app:app --reload --host 0.0.0.0 --port 8000
```

启动后自动完成：建表 → 插入种子数据（默认用户 + 默认儿童"小宝"） → 启动定时任务调度器。

### 访问 API

- Swagger UI: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

---

## 环境变量配置

所有环境变量使用 `AIP_` 前缀，通过 `.env` 文件或系统环境变量配置。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AIP_DATABASE_URL` | `sqlite+aiosqlite:///./ai_parenting_dev.db` | 数据库连接字符串 |
| `AIP_AI_PROVIDER` | `mock` | LLM 供应商（`mock` 或 `hunyuan`） |
| `AIP_HUNYUAN_API_KEY` | — | 腾讯混元 API 密钥 |
| `AIP_HUNYUAN_MODEL` | `hunyuan-lite` | 混元模型名称 |
| `AIP_JWT_SECRET_KEY` | 开发默认值 | JWT 签名密钥（生产环境务必修改） |
| `AIP_PUSH_PROVIDER` | `mock` | 推送供应商 |

---

## API 文档

后端提供 12 个 API 路由模块，全部挂载在 `/api/v1` 前缀下：

| 模块 | 路径 | 功能 |
|------|------|------|
| 认证 | `/api/v1/auth` | 注册、登录、Token 刷新 |
| 儿童档案 | `/api/v1/children` | CRUD 操作 |
| 观察记录 | `/api/v1/records` | 记录管理 |
| 微计划 | `/api/v1/plans` | 计划生成与管理 |
| AI 会话 | `/api/v1/ai-sessions` | 即时求助会话 |
| 首页 | `/api/v1/home` | 聚合数据 |
| 周反馈 | `/api/v1/weekly-feedbacks` | 反馈生成与决策 |
| 消息 | `/api/v1/messages` | 消息列表与状态 |
| 用户 | `/api/v1/users` | 用户档案 |
| 设备 | `/api/v1/devices` | 推送令牌注册 |
| 文件 | `/api/v1/files` | 文件上传 |
| 就医准备 | `/api/v1/consult-prep` | 就医材料准备 |

---

## iOS 客户端

iOS 客户端基于 **SwiftUI + MVVM** 架构，支持 iOS 17+。

### 运行方式

```bash
cd ios
open Package.swift   # 使用 Xcode 打开
```

### 主要功能模块

- **首页**：今日任务概览、儿童状态、快速入口
- **计划**：7 天微计划详情、日任务管理
- **记录**：观察记录列表、快速打点、语音记录
- **消息**：系统通知中心
- **即时求助**：全局浮动按钮，随时获取 AI 指导
- **引导流程**：新用户首次使用引导
- **登录认证**：JWT Token 认证

---

## 测试

```bash
# 运行全部测试
pytest tests/ -v

# 带覆盖率报告
pytest tests/ -v --cov=ai_parenting

# 运行特定模块测试
pytest tests/test_orchestrator.py -v
```

测试套件包含 18 个测试文件，覆盖 API 路由、数据模型、业务服务、AI 编排器、边界检查器等核心模块。

---

## 安全设计

### 非诊断化边界检查

项目的核心安全特性 — **BoundaryChecker** 对所有 AI 输出执行 8 项硬规则检查：

1. **诊断标签黑名单**：禁止输出"自闭"、"多动"等诊断性标签
2. **治疗承诺黑名单**：禁止做出治疗效果承诺
3. **绝对判断黑名单**：禁止使用"一定"、"肯定"等绝对判断
4. **过度量化检测**：正则检测百分比等过度量化表述
5. **责备家长检测**：禁止责备家长的表达
6. **否定儿童检测**：禁止否定儿童的表达
7. **字段完整性检查**：确保结构化输出字段完整
8. **字符长度检查**：控制输出长度在合理范围内

### 容错降级机制

```
Prompt 渲染 → LLM 调用 → JSON 解析 → Pydantic 校验 → 边界检查 → 返回
                ↓ 超时/失败                                  ↓ 不通过
              重试 1 次                                 使用清洁后结果
                ↓ 仍失败
              降级兜底（预构建静态安全结果）
```

### 认证机制

支持渐进式迁移的双认证模式：

- **JWT Bearer Token**：正式认证模式，HS256 算法，7 天有效期
- **X-User-Id Header**：兼容模式，向后兼容旧版客户端

---

## 许可证

本项目为私有项目。未经授权，不得复制、修改或分发。
