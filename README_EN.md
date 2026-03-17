# 🧒 AI Parenting — AI-Powered Parenting Assistant

> An AI-assisted parenting product for caregivers of 18–48 month toddlers, offering instant consultation, personalized parenting plans, multi-channel messaging, voice interaction, and extensible skill system.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com)
[![SwiftUI](https://img.shields.io/badge/SwiftUI-iOS%2017-orange)](https://developer.apple.com/swiftui/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[中文文档](README.md) · [Design Docs](docs/)

---

## ✨ Key Features

| Module | Description |
|--------|-------------|
| 🤖 **AI Consultation Engine** | 6-step orchestration pipeline (render → call → parse → boundary check → degrade → save); supports instant help, plan generation, weekly feedback, and consult prep |
| 📬 **Multi-Channel Push** | APNs / WeChat Templates / OpenClaw Gateway (WhatsApp + Telegram); priority routing + auto fallback + health monitoring |
| 🧠 **Smart Push Engine** | Rule engine + quiet hours + frequency limiter + idempotent dedup; supports cron triggers and event-driven pushes |
| 🎤 **Voice Interaction** | STT → Intent Classification → Skill Routing → TTS; native iOS speech recognition (SFSpeechRecognizer) |
| 🧩 **Skill System** | SkillRegistry + SkillAdapter bridge pattern; 4 built-in skills (instant help / plan generation / weekly feedback / sleep analysis) |
| 📊 **Admin Dashboard** | React + TDesign; push rule management + channel health monitoring + data visualization |
| 🔐 **Security Hardening** | JWT auth + ownership validation + IP rate limiting + CORS whitelist + webhook signature verification |
| 📱 **iOS Client** | Native SwiftUI; 13 feature modules with deep linking + Dark Mode + haptic feedback |

---

## 🏗️ Architecture

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
│  │  (19)   │  │    (15)      │  │  (AI Pipeline) │              │
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
│ Gateway      │  │ Dashboard    │  │(HunYuan/Mock)│
│ (Node.js WS) │  │ (React+TD)  │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 📁 Project Structure

```
ai-parenting/
├── src/ai_parenting/
│   ├── backend/
│   │   ├── app.py                 # FastAPI app factory + middleware + route registration
│   │   ├── auth.py                # JWT authentication
│   │   ├── config.py              # Environment config (Pydantic BaseSettings)
│   │   ├── deps.py                # Dependency injection factories
│   │   ├── models.py              # 12 ORM models
│   │   ├── schemas.py             # Pydantic v2 API schemas
│   │   ├── scheduler.py           # APScheduler integration
│   │   ├── channels/              # 📬 Channel Adapter Layer
│   │   │   ├── base.py            # ChannelAdapter ABC
│   │   │   ├── router.py          # ChannelRouter (priority routing)
│   │   │   ├── health_monitor.py  # Channel health monitoring
│   │   │   ├── apns_adapter.py    # Apple Push Notification Service
│   │   │   ├── wechat_adapter.py  # WeChat message push
│   │   │   └── openclaw_adapter.py# OpenClaw Gateway adapter
│   │   ├── routers/               # 🌐 19 API route modules
│   │   │   ├── auth.py            # Register / Login / Token refresh
│   │   │   ├── users.py           # User management
│   │   │   ├── children.py        # Child profiles
│   │   │   ├── records.py         # Parenting records
│   │   │   ├── plans.py           # Parenting plans
│   │   │   ├── ai_sessions.py     # AI sessions
│   │   │   ├── home.py            # Home aggregation
│   │   │   ├── messages.py        # Message center
│   │   │   ├── devices.py         # Device management
│   │   │   ├── files.py           # File uploads
│   │   │   ├── weekly_feedbacks.py# Weekly feedback reports
│   │   │   ├── consult_prep.py    # Consultation prep
│   │   │   ├── channels.py        # Channel binding & preferences
│   │   │   ├── voice.py           # Voice interaction
│   │   │   ├── skills.py          # Skill listing
│   │   │   ├── memory.py          # Memory management
│   │   │   ├── admin.py           # Admin API
│   │   │   ├── admin_panel.py     # Admin panel SSR
│   │   │   └── webhooks.py        # WeChat / OpenClaw callbacks
│   │   ├── services/              # 💼 15 business services
│   │   │   ├── smart_push_engine.py    # Smart push engine
│   │   │   ├── channel_binding_service.py # Channel binding
│   │   │   ├── inbound_handler.py      # Inbound message handler
│   │   │   ├── memory_service.py       # Hierarchical memory system
│   │   │   ├── voice_service.py        # Voice pipeline orchestration
│   │   │   └── ...                     # Other business services
│   │   └── voice/                 # 🎤 Voice Pipeline
│   │       ├── pipeline.py        # VoicePipeline (stage chain)
│   │       ├── intent_classifier.py # Hybrid intent classifier
│   │       ├── stt_provider.py    # Speech-to-text
│   │       └── tts_provider.py    # Text-to-speech
│   ├── skills/                    # 🧩 Skill System
│   │   ├── base.py                # Skill ABC
│   │   ├── registry.py            # SkillRegistry (auto-discover + intent routing)
│   │   └── adapters/              # 4 skill adapters
│   │       ├── instant_help_adapter.py
│   │       ├── plan_generation_adapter.py
│   │       ├── weekly_feedback_adapter.py
│   │       └── sleep_analysis_skill.py  # Native skill
│   ├── orchestrator.py            # AI orchestration pipeline (6 steps)
│   ├── renderer*.py               # Prompt renderers
│   └── boundary_checker.py        # Safety boundary checker
├── ios/Sources/AIParenting/       # 📱 iOS Client
│   ├── App/                       # App entry + global state
│   ├── Core/                      # Network layer + auth
│   ├── Features/                  # 13 feature modules
│   │   ├── Home/                  # Home (task cards + notification slider)
│   │   ├── Plan/                  # Parenting plans
│   │   ├── Record/                # Records + voice input
│   │   ├── AI/                    # AI consultation + instant help
│   │   ├── Voice/                 # Voice interaction overlay
│   │   ├── Channel/               # Channel management + WeChat binding
│   │   ├── Skills/                # Skill list
│   │   ├── Message/               # Message center
│   │   ├── Profile/               # User profile
│   │   ├── Child/                 # Child management
│   │   ├── Feedback/              # Weekly feedback
│   │   ├── Onboarding/            # Onboarding flow
│   │   └── Auth/                  # Login & registration
│   └── Models/                    # Data models
├── admin-dashboard/               # 📊 Admin Dashboard
│   └── src/
│       ├── pages/
│       │   ├── PushRulesPage.tsx   # Push rule management
│       │   └── ChannelMonitorPage.tsx # Channel health monitoring
│       ├── components/            # Reusable components
│       └── layouts/               # Layout components
├── gateway/                       # 🌐 OpenClaw Gateway (Node.js)
├── tests/                         # ✅ 27 test files
├── docs/                          # 📖 Design documents
├── docker-compose.yml             # Docker orchestration (3 services)
├── Dockerfile                     # Backend container image
└── pyproject.toml                 # Python project config
```

---

## 🔧 Configuration

### Environment Variables

```bash
# ── Basic ──
SECRET_KEY=your-jwt-secret-key
DATABASE_URL=sqlite+aiosqlite:///./dev.db  # SQLite for dev, PostgreSQL for prod
AI_PROVIDER=mock                           # mock | hunyuan

# ── HunYuan AI (optional) ──
HUNYUAN_SECRET_ID=your-secret-id
HUNYUAN_SECRET_KEY=your-secret-key

# ── APNs Push (optional) ──
APNS_KEY_ID=your-key-id
APNS_TEAM_ID=your-team-id
APNS_KEY_PATH=path/to/AuthKey.p8
APNS_BUNDLE_ID=com.yourapp.aiparenting
APNS_USE_SANDBOX=true

# ── WeChat Push (optional) ──
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
WECHAT_TOKEN=your-wechat-verify-token
WECHAT_AES_KEY=your-wechat-aes-key

# ── OpenClaw Gateway (optional) ──
OPENCLAW_WS_URL=ws://localhost:8765
OPENCLAW_API_KEY=your-openclaw-key

# ── PostgreSQL (production) ──
POSTGRES_USER=aiparenting
POSTGRES_PASSWORD=your-password
POSTGRES_DB=aiparenting
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aiparenting

# ── Push Engine ──
PUSH_ENGINE_MODE=smart                     # smart | legacy
```

---

## 🚀 Quick Start

### Option 1: Local Development

```bash
# 1. Clone the repository
git clone https://github.com/your-org/ai-parenting.git
cd ai-parenting

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e ".[dev,push]"

# 4. Start backend (auto SQLite + Mock AI)
uvicorn src.ai_parenting.backend.app:create_app --factory --reload --port 8000

# 5. Open API docs
open http://localhost:8000/docs
```

### Option 2: Docker Deployment

```bash
# Start all services (Backend + OpenClaw Gateway + PostgreSQL)
docker compose --profile production up -d

# Start backend + gateway only (dev mode, uses SQLite)
docker compose up -d backend gateway

# View logs
docker compose logs -f backend
```

### Admin Dashboard

```bash
cd admin-dashboard
npm install
npm run dev
# Visit http://localhost:5173
```

### iOS Client

```bash
cd ios/DevApp
xcodegen generate   # Generate Xcode project
open DevApp.xcodeproj
# Xcode → Run (⌘R)
```

---

## 🌐 API Overview

The backend provides **19 route modules** under the base path `/api/v1`:

| Module | Path Prefix | Description |
|--------|-------------|-------------|
| `auth` | `/api/v1/auth` | Registration, login, token refresh |
| `users` | `/api/v1/users` | User profile management |
| `children` | `/api/v1/children` | Child profile CRUD |
| `records` | `/api/v1/records` | Parenting records (feeding/sleep/activity) |
| `plans` | `/api/v1/plans` | AI parenting plan generation & management |
| `ai_sessions` | `/api/v1/ai-sessions` | AI session management |
| `home` | `/api/v1/home` | Home page data aggregation |
| `messages` | `/api/v1/messages` | Push notification center |
| `devices` | `/api/v1/devices` | Device registration + APNs token |
| `files` | `/api/v1/files` | File/image uploads |
| `weekly_feedbacks` | `/api/v1/weekly-feedbacks` | Weekly feedback reports |
| `consult_prep` | `/api/v1/consult-prep` | Medical consultation prep |
| `channels` | `/api/v1/channels` | Channel binding & preference settings |
| `voice` | `/api/v1/voice` | Voice conversation & transcription |
| `skills` | `/api/v1/skills` | Skill listing & details |
| `memory` | `/api/v1/memory` | Hierarchical memory read/write |
| `admin` | `/api/v1/admin` | Admin API (users/push/stats) |
| `admin_panel` | `/admin` | Admin panel (SSR pages) |
| `webhooks` | `/webhooks` | WeChat / OpenClaw callback endpoints |

> Full API documentation available at: `http://localhost:8000/docs`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src/ai_parenting --cov-report=term-missing

# Run specific module tests
pytest tests/test_voice_api.py       # Voice API
pytest tests/test_skills.py          # Skill system
pytest tests/test_channels_api.py    # Channel API
pytest tests/test_webhooks_api.py    # Webhooks
pytest tests/test_inbound_e2e.py     # Inbound message E2E
pytest tests/test_memory_api.py      # Memory system
```

**Test coverage**: 27 test files covering API routes, business services, AI orchestration, safety boundaries, webhooks, voice, skills, memory, and more.

---

## 📊 ORM Data Models

| Model | Table | Description |
|-------|-------|-------------|
| `User` | `users` | User accounts |
| `Device` | `devices` | Device info + APNs token |
| `Child` | `children` | Child profiles |
| `Record` | `records` | Parenting records (multi-type) |
| `Plan` | `plans` | AI parenting plans |
| `DayTask` | `day_tasks` | Daily task items |
| `WeeklyFeedback` | `weekly_feedbacks` | Weekly feedback reports |
| `AISession` | `ai_sessions` | AI sessions |
| `Message` | `messages` | Push messages |
| `ChannelBinding` | `channel_bindings` | Channel binding relations |
| `PushLog` | `push_logs` | Push logs (idempotent) |
| `UserChannelPreference` | `user_channel_preferences` | User channel preferences |

---

## 🔒 Security Features

- **JWT Authentication**: All endpoints require auth (except register/login/webhooks)
- **Ownership Validation**: Users can only access their own data
- **IP Rate Limiting**: General 120/min, AI endpoints 10/min, login 5/min
- **CORS Whitelist**: Configurable allowed origins
- **Webhook Signature Verification**: WeChat message signature + OpenClaw HMAC
- **Password Security**: bcrypt hashing + salting
- **SQL Injection Prevention**: All queries via SQLAlchemy ORM parameterized queries

---

## 🛠️ Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI + Uvicorn
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: SQLite (dev) / PostgreSQL 16 (production)
- **Migration**: Alembic
- **Scheduler**: APScheduler
- **Push**: aioapns / httpx (WeChat) / websockets (OpenClaw)
- **Auth**: python-jose (JWT) + passlib (bcrypt)

### iOS Client
- **Language**: Swift 5.9+
- **UI**: SwiftUI (iOS 17+)
- **Voice**: Speech.framework + AVFoundation
- **Push**: APNs + UserNotifications

### Admin Dashboard
- **Framework**: React 18.3 + TypeScript 5.6
- **Build**: Vite 5.4
- **UI Components**: TDesign React
- **Styling**: Tailwind CSS
- **Charts**: Recharts

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Gateway**: Node.js WebSocket Gateway (OpenClaw)
- **Database**: PostgreSQL 16 (production)

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Product Requirements](docs/prd.md) | Complete product requirement specification |
| [Technical Architecture](docs/technical-architecture.md) | Detailed system architecture design |
| [API Specification](docs/api-spec.md) | Full RESTful API definitions |
| [Data Model Design](docs/data-model.md) | Database schema design |
| [Push System Design](docs/push-system-design.md) | Multi-channel push architecture |
| [Voice System Design](docs/voice-system-design.md) | Voice pipeline architecture |
| [Skill System Design](docs/skill-system-design.md) | Skill extension framework |
| [OpenClaw Integration](docs/plans/2026-03-16-openclaw-integration-design.md) | OpenClaw Gateway integration plan |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
