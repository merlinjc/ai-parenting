# 🧒 AI Parenting — AI 辅助育儿助手

> 面向 18–48 月龄幼儿家长的 AI 辅助育儿产品，提供即时咨询、个性化养育计划、多渠道消息推送、语音交互与技能扩展。

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com)
[![SwiftUI](https://img.shields.io/badge/SwiftUI-iOS%2017-orange)](https://developer.apple.com/swiftui/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[English](README_EN.md) · [设计文档](docs/)

---

## ✨ 功能亮点

| 模块 | 说明 |
|------|------|
| 🤖 **AI 咨询引擎** | 6 步编排管线（渲染 → 调用 → 解析 → 边界检查 → 降级 → 保存），支持即时咨询、养育计划生成、周反馈报告、咨询准备 |
| 📬 **多渠道推送** | APNs / 微信模板消息 / OpenClaw Gateway（WhatsApp + Telegram），优先级路由 + 自动降级 + 健康监控 |
| 🧠 **智能推送引擎** | 规则引擎 + 静默时段 + 频率限制 + 幂等去重，支持定时触发与事件驱动 |
| 🎤 **语音交互** | STT → 意图分类 → 技能路由 → TTS，支持 iOS 原生语音识别（SFSpeechRecognizer） |
| 🧩 **技能系统** | SkillRegistry + SkillAdapter 桥接模式，4 个内置技能（即时帮助 / 计划生成 / 周反馈 / 睡眠分析） |
| 📊 **管理后台** | React + TDesign，推送规则管理 + 渠道健康监控 + 数据可视化 |
| 🔐 **安全加固** | JWT 认证 + 所有权校验 + IP 限流 + CORS 白名单 + Webhook 签名验证 |
| 📱 **iOS 客户端** | SwiftUI 原生开发，13 个功能模块，支持深链导航 + Dark Mode + 触觉反馈 |

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        iOS Client (SwiftUI)                     │
│  Home │ Plan │ Record │ AI Chat │ Voice │ Channel │ Skills     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / REST
┌──────────────────────────▼──────────────────────────────────────┐
│                     FastAPI Backend (Python)                     │
│                                                                  │
│  ┌─────────┐  ┌──────────────┐  ┌───────────────┐              │
│  │ Routers │→│   Services    │→│  Orchestrator  │              │
│  │ (19 个)  │  │   (15 个)     │  │  (AI Pipeline) │              │
│  └─────────┘  └──────────────┘  └───────┬───────┘              │
│                                          │                       │
│  ┌──────────────┐  ┌─────────────┐  ┌───▼──────────┐           │
│  │ Channel Layer │  │ Voice       │  │ Skill System │           │
│  │ APNs/WeChat/  │  │ Pipeline    │  │ Registry +   │           │
│  │ OpenClaw      │  │ STT→TTS    │  │ 4 Adapters   │           │
│  └──────┬───────┘  └─────────────┘  └──────────────┘           │
│         │                                                        │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Smart Push   │  │ Memory       │  │ Boundary     │          │
│  │ Engine       │  │ Service      │  │ Checker      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────┐           │
│  │            SQLAlchemy ORM (12 Models)             │           │
│  │     SQLite (dev) │ PostgreSQL (production)        │           │
│  └──────────────────────────────────────────────────┘           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ OpenClaw     │  │ Admin        │  │   AI Model   │
│ Gateway      │  │ Dashboard    │  │ (混元/Mock)   │
│ (Node.js WS) │  │ (React+TD)  │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 📁 项目结构

```
ai-parenting/
├── src/ai_parenting/
│   ├── backend/
│   │   ├── app.py                 # FastAPI 应用工厂 + 中间件 + 路由注册
│   │   ├── auth.py                # JWT 认证
│   │   ├── config.py              # 环境配置 (Pydantic BaseSettings)
│   │   ├── deps.py                # 依赖注入工厂
│   │   ├── models.py              # 12 个 ORM 模型
│   │   ├── schemas.py             # Pydantic v2 API 数据模型
│   │   ├── scheduler.py           # APScheduler 定时任务
│   │   ├── channels/              # 📬 渠道适配层
│   │   │   ├── base.py            # ChannelAdapter 抽象基类
│   │   │   ├── router.py          # ChannelRouter (优先级路由)
│   │   │   ├── health_monitor.py  # 渠道健康监控
│   │   │   ├── apns_adapter.py    # Apple 推送服务
│   │   │   ├── wechat_adapter.py  # 微信消息推送
│   │   │   └── openclaw_adapter.py# OpenClaw Gateway 适配器
│   │   ├── routers/               # 🌐 19 个 API 路由模块
│   │   │   ├── auth.py            # 注册/登录/Token 刷新
│   │   │   ├── users.py           # 用户管理
│   │   │   ├── children.py        # 儿童档案
│   │   │   ├── records.py         # 养育记录
│   │   │   ├── plans.py           # 养育计划
│   │   │   ├── ai_sessions.py     # AI 会话
│   │   │   ├── home.py            # 首页聚合
│   │   │   ├── messages.py        # 消息中心
│   │   │   ├── devices.py         # 设备管理
│   │   │   ├── files.py           # 文件上传
│   │   │   ├── weekly_feedbacks.py# 周反馈报告
│   │   │   ├── consult_prep.py    # 咨询准备
│   │   │   ├── channels.py        # 渠道绑定/偏好
│   │   │   ├── voice.py           # 语音交互
│   │   │   ├── skills.py          # 技能列表
│   │   │   ├── memory.py          # 记忆管理
│   │   │   ├── admin.py           # 管理 API
│   │   │   ├── admin_panel.py     # 管理面板 SSR
│   │   │   └── webhooks.py        # 微信/OpenClaw 回调
│   │   ├── services/              # 💼 15 个业务服务
│   │   │   ├── smart_push_engine.py    # 智能推送引擎
│   │   │   ├── channel_binding_service.py # 渠道绑定
│   │   │   ├── inbound_handler.py      # 入站消息处理
│   │   │   ├── memory_service.py       # 层级记忆系统
│   │   │   ├── voice_service.py        # 语音管线编排
│   │   │   └── ...                     # 其他业务服务
│   │   └── voice/                 # 🎤 语音管线
│   │       ├── pipeline.py        # VoicePipeline (阶段链)
│   │       ├── intent_classifier.py # 混合意图分类器
│   │       ├── stt_provider.py    # 语音转文字
│   │       └── tts_provider.py    # 文字转语音
│   ├── skills/                    # 🧩 技能系统
│   │   ├── base.py                # Skill 抽象基类
│   │   ├── registry.py            # SkillRegistry (自动发现 + 意图路由)
│   │   └── adapters/              # 4 个技能适配器
│   │       ├── instant_help_adapter.py
│   │       ├── plan_generation_adapter.py
│   │       ├── weekly_feedback_adapter.py
│   │       └── sleep_analysis_skill.py  # 原生技能
│   ├── orchestrator.py            # AI 编排管线 (6 步)
│   ├── renderer*.py               # Prompt 渲染器
│   └── boundary_checker.py        # 安全边界检查
├── ios/Sources/AIParenting/       # 📱 iOS 客户端
│   ├── App/                       # 应用入口 + 全局状态
│   ├── Core/                      # 网络层 + 认证
│   ├── Features/                  # 13 个功能模块
│   │   ├── Home/                  # 首页 (任务卡片 + 通知横滑)
│   │   ├── Plan/                  # 养育计划
│   │   ├── Record/                # 养育记录 + 语音录入
│   │   ├── AI/                    # AI 咨询 + 即时帮助
│   │   ├── Voice/                 # 语音交互浮层
│   │   ├── Channel/               # 渠道管理 + 微信绑定
│   │   ├── Skills/                # 技能列表
│   │   ├── Message/               # 消息中心
│   │   ├── Profile/               # 个人中心
│   │   ├── Child/                 # 儿童管理
│   │   ├── Feedback/              # 周反馈
│   │   ├── Onboarding/            # 新手引导
│   │   └── Auth/                  # 登录注册
│   └── Models/                    # 数据模型
├── admin-dashboard/               # 📊 管理后台
│   └── src/
│       ├── pages/
│       │   ├── PushRulesPage.tsx   # 推送规则管理
│       │   └── ChannelMonitorPage.tsx # 渠道健康监控
│       ├── components/            # 可复用组件
│       └── layouts/               # 布局组件
├── gateway/                       # 🌐 OpenClaw Gateway (Node.js)
├── tests/                         # ✅ 27 个测试文件
├── docs/                          # 📖 设计文档
├── docker-compose.yml             # Docker 编排 (3 服务)
├── Dockerfile                     # 后端容器镜像
└── pyproject.toml                 # Python 项目配置
```

---

## 🔧 环境配置

### 环境变量

```bash
# ── 基础配置 ──
SECRET_KEY=your-jwt-secret-key          # JWT 签名密钥
DATABASE_URL=sqlite+aiosqlite:///./dev.db  # 数据库连接 (开发用 SQLite，生产用 PostgreSQL)
AI_PROVIDER=mock                        # AI 模型 (mock | hunyuan)

# ── 混元 AI (可选) ──
HUNYUAN_SECRET_ID=your-secret-id
HUNYUAN_SECRET_KEY=your-secret-key

# ── APNs 推送 (可选) ──
APNS_KEY_ID=your-key-id
APNS_TEAM_ID=your-team-id
APNS_KEY_PATH=path/to/AuthKey.p8
APNS_BUNDLE_ID=com.yourapp.aiparenting
APNS_USE_SANDBOX=true

# ── 微信推送 (可选) ──
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
WECHAT_TOKEN=your-wechat-verify-token
WECHAT_AES_KEY=your-wechat-aes-key

# ── OpenClaw Gateway (可选) ──
OPENCLAW_WS_URL=ws://localhost:8765
OPENCLAW_API_KEY=your-openclaw-key

# ── PostgreSQL (生产环境) ──
POSTGRES_USER=aiparenting
POSTGRES_PASSWORD=your-password
POSTGRES_DB=aiparenting
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aiparenting

# ── 推送引擎 ──
PUSH_ENGINE_MODE=smart                  # smart | legacy
```

---

## 🚀 快速开始

### 方式一：本地开发

```bash
# 1. 克隆项目
git clone https://github.com/your-org/ai-parenting.git
cd ai-parenting

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -e ".[dev,push]"

# 4. 启动后端 (自动使用 SQLite + Mock AI)
uvicorn src.ai_parenting.backend.app:create_app --factory --reload --port 8000

# 5. 访问 API 文档
open http://localhost:8000/docs
```

### 方式二：Docker 部署

```bash
# 启动全部服务 (后端 + OpenClaw Gateway + PostgreSQL)
docker compose --profile production up -d

# 仅启动后端 + Gateway (开发环境，使用 SQLite)
docker compose up -d backend gateway

# 查看日志
docker compose logs -f backend
```

### 管理后台

```bash
cd admin-dashboard
npm install
npm run dev
# 访问 http://localhost:5173
```

### iOS 客户端

```bash
cd ios/DevApp
xcodegen generate   # 生成 Xcode 工程
open DevApp.xcodeproj
# Xcode → Run (⌘R)
```

---

## 🌐 API 概览

后端提供 **19 个路由模块**，基础路径 `/api/v1`：

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| `auth` | `/api/v1/auth` | 注册、登录、Token 刷新 |
| `users` | `/api/v1/users` | 用户信息管理 |
| `children` | `/api/v1/children` | 儿童档案 CRUD |
| `records` | `/api/v1/records` | 养育记录（喂养/睡眠/运动等） |
| `plans` | `/api/v1/plans` | AI 养育计划生成与管理 |
| `ai_sessions` | `/api/v1/ai-sessions` | AI 会话管理 |
| `home` | `/api/v1/home` | 首页数据聚合 |
| `messages` | `/api/v1/messages` | 推送消息中心 |
| `devices` | `/api/v1/devices` | 设备注册 + APNs Token |
| `files` | `/api/v1/files` | 文件/图片上传 |
| `weekly_feedbacks` | `/api/v1/weekly-feedbacks` | 周反馈报告 |
| `consult_prep` | `/api/v1/consult-prep` | 就医咨询准备 |
| `channels` | `/api/v1/channels` | 渠道绑定与偏好设置 |
| `voice` | `/api/v1/voice` | 语音对话与转写 |
| `skills` | `/api/v1/skills` | 技能列表与详情 |
| `memory` | `/api/v1/memory` | 层级记忆读写 |
| `admin` | `/api/v1/admin` | 管理 API（用户/推送/统计） |
| `admin_panel` | `/admin` | 管理面板（SSR 页面） |
| `webhooks` | `/webhooks` | 微信 / OpenClaw 回调入口 |

> 完整 API 文档在后端启动后访问：`http://localhost:8000/docs`

---

## 🧪 测试

```bash
# 运行全部测试
pytest

# 带覆盖率
pytest --cov=src/ai_parenting --cov-report=term-missing

# 运行特定模块测试
pytest tests/test_voice_api.py       # 语音 API
pytest tests/test_skills.py          # 技能系统
pytest tests/test_channels_api.py    # 渠道 API
pytest tests/test_webhooks_api.py    # Webhook
pytest tests/test_inbound_e2e.py     # 入站消息端到端
pytest tests/test_memory_api.py      # 记忆系统
```

**测试覆盖范围**：27 个测试文件，覆盖 API 路由、业务服务、AI 编排、安全边界、Webhook、语音、技能、记忆等模块。

---

## 📊 ORM 数据模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `User` | `users` | 用户账户 |
| `Device` | `devices` | 设备信息 + APNs Token |
| `Child` | `children` | 儿童档案 |
| `Record` | `records` | 养育记录（多类型） |
| `Plan` | `plans` | AI 养育计划 |
| `DayTask` | `day_tasks` | 每日任务项 |
| `WeeklyFeedback` | `weekly_feedbacks` | 周反馈报告 |
| `AISession` | `ai_sessions` | AI 会话 |
| `Message` | `messages` | 推送消息 |
| `ChannelBinding` | `channel_bindings` | 渠道绑定关系 |
| `PushLog` | `push_logs` | 推送日志（幂等） |
| `UserChannelPreference` | `user_channel_preferences` | 用户渠道偏好 |

---

## 🔒 安全特性

- **JWT 认证**：所有 API 端点均需认证（除注册/登录/Webhook）
- **所有权校验**：用户只能访问自己的数据
- **IP 限流**：通用 120 次/分钟，AI 接口 10 次/分钟，登录 5 次/分钟
- **CORS 白名单**：可配置允许的域名
- **Webhook 签名验证**：微信消息签名 + OpenClaw HMAC
- **密码安全**：bcrypt 哈希 + 加盐
- **SQL 注入防护**：全部使用 SQLAlchemy ORM 参数化查询

---

## 🛠️ 技术栈

### 后端
- **语言**：Python 3.11+
- **框架**：FastAPI + Uvicorn
- **ORM**：SQLAlchemy 2.0 (async)
- **数据库**：SQLite (开发) / PostgreSQL 16 (生产)
- **迁移**：Alembic
- **调度器**：APScheduler
- **推送**：aioapns / httpx (微信) / websockets (OpenClaw)
- **认证**：python-jose (JWT) + passlib (bcrypt)

### iOS 客户端
- **语言**：Swift 5.9+
- **UI**：SwiftUI (iOS 17+)
- **语音**：Speech.framework + AVFoundation
- **推送**：APNs + UserNotifications

### 管理后台
- **框架**：React 18.3 + TypeScript 5.6
- **构建**：Vite 5.4
- **UI 组件**：TDesign React
- **样式**：Tailwind CSS
- **图表**：Recharts

### 基础设施
- **容器化**：Docker + Docker Compose
- **网关**：Node.js WebSocket Gateway (OpenClaw)
- **数据库**：PostgreSQL 16 (生产)

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [产品需求文档](docs/prd.md) | 完整产品需求规格 |
| [技术架构设计](docs/technical-architecture.md) | 系统架构详细设计 |
| [API 接口规格](docs/api-spec.md) | RESTful API 完整定义 |
| [数据模型设计](docs/data-model.md) | 数据库表结构设计 |
| [推送系统设计](docs/push-system-design.md) | 多渠道推送架构设计 |
| [语音系统设计](docs/voice-system-design.md) | 语音管线架构设计 |
| [技能系统设计](docs/skill-system-design.md) | 技能扩展框架设计 |
| [OpenClaw 集成设计](docs/plans/2026-03-16-openclaw-integration-design.md) | OpenClaw Gateway 集成方案 |

---

## 📄 开源协议

本项目采用 [MIT 协议](LICENSE) 开源。
