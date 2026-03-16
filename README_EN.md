# AI Parenting — Intelligent Parenting Assistant

> Not a diagnostic tool, not a therapist — a knowledgeable friend helping parents create more high-quality interactions with their children in everyday life.

**AI Parenting** is an AI-powered parenting product designed for **parents of toddlers aged 18–48 months (1.5–4 years)**, featuring a full-stack implementation with a Python backend service and a native iOS client.

[中文版](./README.md)

---

## Table of Contents

- [Core Features](#core-features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [iOS Client](#ios-client)
- [Testing](#testing)
- [Safety by Design](#safety-by-design)
- [License](#license)

---

## Core Features

### Three AI Capabilities

| Feature | Description | Timeout Strategy |
|---------|-------------|-----------------|
| **Instant Help** | Real-time 3-step guidance during high-pressure moments (calm yourself → take action → observe later) | 8s timeout, retry then fallback |
| **Micro-Plan Generation** | AI generates a 7-day family support plan with 2 daily tasks, sample scripts, and observation points | 30s timeout |
| **Weekly Feedback** | Post-plan weekly report with positive change recognition and improvement suggestions | 20s timeout |

### End-to-End Business Flow

- **Child Profile Management**: Automatic age-stage classification (18–24m / 24–36m / 36–48m) with six focus areas (language, social, emotional, motor, cognitive, self-care)
- **Observation Records**: Three recording modes — quick check, event log, and voice recording
- **Message Center**: System notifications for plan reminders, record prompts, weekly feedback alerts, and risk warnings
- **Scheduled Tasks**: Daily automatic plan progression, task reminders, and record prompts
- **Consult Preparation**: Helps parents prepare materials for medical consultations
- **Push Notifications**: APNs integration for iOS

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   iOS Client                         │
│          SwiftUI · MVVM · iOS 17+                   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTPS / JSON
┌──────────────────────▼──────────────────────────────┐
│                 FastAPI Backend                       │
│  ┌────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Router │→│  Service  │→│   AI Orchestrator    │  │
│  │12 mods │  │ 11 svcs  │  │ Render→LLM→Parse   │  │
│  └────────┘  └──────────┘  │ →Validate→Boundary  │  │
│                             └─────────┬──────────┘  │
│  ┌────────────────┐  ┌────────────────▼──────────┐  │
│  │  SQLAlchemy    │  │    LLM Provider Layer      │  │
│  │  Async ORM     │  │  MockProvider / Hunyuan   │  │
│  └───────┬────────┘  └───────────────────────────┘  │
└──────────┼──────────────────────────────────────────┘
           │
    ┌──────▼───────┐
    │  SQLite (dev) │
    │  PostgreSQL   │
    │   (prod)      │
    └──────────────┘
```

| Layer | Technology |
|-------|-----------|
| **Backend Framework** | FastAPI (Python 3.11+) |
| **ORM** | SQLAlchemy 2.0 (async mode) |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Validation** | Pydantic v2 |
| **Authentication** | JWT (python-jose) + bcrypt (passlib) |
| **Scheduler** | APScheduler (AsyncIO) |
| **LLM Integration** | Tencent Hunyuan (OpenAI-compatible API) |
| **iOS Client** | Swift 5.9 / SwiftUI / iOS 17+ |
| **iOS Architecture** | MVVM + @Observable |
| **Package Management** | Swift Package Manager / pip |
| **Testing** | pytest + pytest-asyncio |

---

## Project Structure

```
ai-parenting/
├── pyproject.toml                 # Python project config & dependencies
├── src/ai_parenting/
│   ├── orchestrator.py            # AI orchestrator (core)
│   ├── renderer*.py               # Prompt template renderers
│   ├── engine/
│   │   ├── boundary_checker.py    # Non-diagnostic safety boundary checks
│   │   └── template_engine.py     # Conditional template engine
│   ├── models/                    # Domain models & enums
│   ├── providers/                 # LLM provider adapter layer
│   │   ├── base.py                # Abstract interface
│   │   ├── mock_provider.py       # Mock (dev/test)
│   │   └── hunyuan_provider.py    # Tencent Hunyuan
│   ├── templates/                 # Prompt template constants
│   └── backend/
│       ├── app.py                 # FastAPI entry point
│       ├── config.py              # Configuration management
│       ├── models.py              # 9 ORM models
│       ├── schemas.py             # API schemas
│       ├── auth.py                # JWT authentication
│       ├── scheduler.py           # Scheduled task dispatcher
│       ├── routers/               # 12 API router modules
│       └── services/              # 11 business services
├── ios/
│   ├── Package.swift              # SPM configuration
│   └── Sources/AIParenting/
│       ├── App/                   # App entry & global state
│       ├── Core/                  # Networking, auth, push
│       ├── Features/              # Feature modules (MVVM)
│       ├── Models/                # Swift data models
│       ├── Shared/                # Shared UI components
│       └── Extensions/            # Utility extensions
└── tests/                         # Backend test suite
```

---

## Getting Started

### Prerequisites

- **Python** 3.11+
- **Xcode** 15+ / iOS 17+ (for the iOS client)
- **SQLite** (used automatically in development)

### Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/merlinjc/ai-parenting.git
cd ai-parenting

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Configure environment variables (optional; defaults to Mock LLM)
cp .env.example .env
# Edit .env to add your Tencent Hunyuan API key (if real AI is needed)

# 4. Start the server
uvicorn ai_parenting.backend.app:app --reload --host 0.0.0.0 --port 8000
```

On startup, the server automatically: creates tables → seeds data (default user + default child "Xiaobao") → starts the scheduler.

### Access the API

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## Configuration

All environment variables use the `AIP_` prefix and can be set via a `.env` file or system environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `AIP_DATABASE_URL` | `sqlite+aiosqlite:///./ai_parenting_dev.db` | Database connection string |
| `AIP_AI_PROVIDER` | `mock` | LLM provider (`mock` or `hunyuan`) |
| `AIP_HUNYUAN_API_KEY` | — | Tencent Hunyuan API key |
| `AIP_HUNYUAN_MODEL` | `hunyuan-lite` | Hunyuan model name |
| `AIP_JWT_SECRET_KEY` | Dev default | JWT signing key (must change in production) |
| `AIP_PUSH_PROVIDER` | `mock` | Push notification provider |

---

## API Reference

The backend provides 12 API router modules, all mounted under the `/api/v1` prefix:

| Module | Path | Description |
|--------|------|-------------|
| Auth | `/api/v1/auth` | Register, login, token refresh |
| Children | `/api/v1/children` | CRUD operations |
| Records | `/api/v1/records` | Observation record management |
| Plans | `/api/v1/plans` | Plan generation & management |
| AI Sessions | `/api/v1/ai-sessions` | Instant help sessions |
| Home | `/api/v1/home` | Aggregated dashboard data |
| Weekly Feedbacks | `/api/v1/weekly-feedbacks` | Feedback generation & decisions |
| Messages | `/api/v1/messages` | Message list & status |
| Users | `/api/v1/users` | User profile |
| Devices | `/api/v1/devices` | Push token registration |
| Files | `/api/v1/files` | File uploads |
| Consult Prep | `/api/v1/consult-prep` | Consultation preparation |

---

## iOS Client

The iOS client is built with **SwiftUI + MVVM** architecture, targeting iOS 17+.

### Running the App

```bash
cd ios
open Package.swift   # Opens in Xcode
```

### Feature Modules

- **Home**: Daily task overview, child status, quick-access entries
- **Plans**: 7-day micro-plan details, daily task management
- **Records**: Observation record list, quick check, voice recording
- **Messages**: System notification center
- **Instant Help**: Global floating button for on-demand AI guidance
- **Onboarding**: First-time user guidance flow
- **Authentication**: JWT token-based login

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=ai_parenting

# Run specific module tests
pytest tests/test_orchestrator.py -v
```

The test suite includes 18 test files covering API routes, data models, business services, the AI orchestrator, and the boundary checker.

---

## Safety by Design

### Non-Diagnostic Boundary Checking

The project's core safety feature — **BoundaryChecker** — enforces 8 hard rules on all AI outputs:

1. **Diagnostic Label Blocklist**: Blocks diagnostic labels such as "autism" or "ADHD"
2. **Treatment Promise Blocklist**: Prevents claims of treatment efficacy
3. **Absolute Judgment Blocklist**: Blocks definitive statements like "definitely" or "certainly"
4. **Over-Quantification Detection**: Regex detection of excessive percentages and metrics
5. **Parent-Blaming Detection**: Blocks language that blames parents
6. **Child-Negation Detection**: Blocks language that negates the child
7. **Field Completeness Check**: Ensures structured output fields are complete
8. **Character Length Check**: Keeps output length within reasonable bounds

### Fault-Tolerant Degradation

```
Prompt Render → LLM Call → JSON Parse → Pydantic Validate → Boundary Check → Return
                 ↓ timeout/error                                ↓ violation
               Retry once                              Use sanitized result
                 ↓ still fails
               Graceful fallback (pre-built static safe result)
```

### Authentication

Progressive migration with dual authentication modes:

- **JWT Bearer Token**: Primary auth mode, HS256 algorithm, 7-day expiry
- **X-User-Id Header**: Compatibility mode for legacy client support

---

## License

This is a private project. Unauthorized copying, modification, or distribution is prohibited.
