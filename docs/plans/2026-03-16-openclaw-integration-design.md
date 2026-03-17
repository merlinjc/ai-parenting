# AI Parenting × OpenClaw 融合方案：项目价值分析与技术架构设计

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 通过混合集成 OpenClaw 网关能力并借鉴其架构模式，为 AI Parenting 项目增加全渠道智能推送、语音交互和模块化技能系统，全面升级后端与 iOS 客户端。

**Architecture:** 后端通过 Channel Adapter 层对接 OpenClaw Gateway 实现多渠道消息路由（微信/WhatsApp/Telegram/iOS Push），同时在现有 FastAPI 体系内引入 Skill Registry 模块化架构和 Voice Pipeline 语音处理链路。iOS 客户端新增语音交互层和多渠道偏好管理。

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / APScheduler / OpenClaw Gateway (TypeScript) / WeChat Official Account API / WhatsApp Business API (via OpenClaw Baileys) / Telegram Bot API (via OpenClaw grammY) / APNs / SwiftUI / AVFoundation / Speech.framework (iOS 原生 ASR) / AVSpeechSynthesizer (iOS 原生 TTS) / 腾讯云 ASR-TTS (Fallback)

---

## 一、项目背景与现状分析

### 1.1 AI Parenting 现状

AI Parenting 是一款面向 18-48 月幼儿家长的辅助型 AI 产品，当前已构建起完整的后端服务与 iOS 客户端。后端基于 FastAPI 框架，采用 SQLAlchemy ORM 管理九个核心领域模型（User、Device、Child、Record、Plan、DayTask、WeeklyFeedback、AISession、Message），通过 Orchestrator 编排层统一调度三种 AI 会话类型（即时求助、计划生成、周反馈），并配备了非诊断化边界检查器（BoundaryChecker），确保所有 AI 输出严格规避诊断标签、治疗承诺和绝对判断等敏感内容。

iOS 客户端采用 SwiftUI 构建，包含首页、计划、记录、反馈、消息、即时求助等完整功能模块，已实现 JWT 认证、设备注册和基础推送通知框架。

然而，项目在以下三个维度存在明确的能力缺口：

| 维度 | 现状 | 缺口 |
|------|------|------|
| **消息触达** | 仅支持 iOS APNs 推送，且 PushProvider 仅有 Mock 实现 | 无法触达微信/WhatsApp/Telegram 用户 |
| **交互方式** | 纯文本输入，语音记录仅支持上传 URL | 缺少语音对话、语音唤醒、TTS 播报 |
| **架构扩展性** | AI 会话类型硬编码在 Orchestrator 中 | 新增能力需修改多处核心代码 |

### 1.2 OpenClaw 核心能力

OpenClaw（318k Star，MIT 协议）是一个基于 TypeScript/Node.js 的个人 AI 助手网关，核心设计哲学是 **"中心化网关 + 分布式节点"**。

**多渠道统一收件箱**：通过单一网关进程同时服务 WhatsApp（Baileys）、Telegram（grammY）、Slack（Bolt）等 20+ 消息平台，所有渠道的消息在网关层统一路由。

**技能系统（Skill System）**：三级优先级加载（工作区 > 托管 > 内置），每个技能是含 `SKILL.md` 元数据的独立目录，支持热插拔。

**节点架构（Node System）**：设备通过 WebSocket 连接网关，支持远程执行拍照、录屏、位置获取等操作，遵循 TCC 权限模型。

**语音交互**：macOS/iOS 支持唤醒词，集成 ElevenLabs 和系统 TTS，提供覆盖层对话界面。

**会话隔离与安全沙箱**：按发送者/频道/群组三种维度的会话隔离，非主会话可运行在 Docker 沙箱中。

---

## 二、项目价值分析

### 2.1 战略价值：从"工具"到"陪伴"

当前 AI Parenting 的核心使用路径是 **"家长主动打开 App → 查看计划 → 发起 AI 求助"**，是典型的工具型产品形态。育儿场景的本质需求却是 **持续陪伴和及时提醒** —— 家长带娃时很少有空闲打开 App。

融合 OpenClaw 能力后，产品形态将升级为 **"AI 主动在家长日常渠道中提供陪伴式服务"**：

> 早上 8 点，微信收到消息："今天是宝宝训练第 3 天，主题是'模仿游戏——用勺子假装喂玩偶'，可以在吃饭前试试。"
>
> 下午带娃时双手不空，对手机说："记录一下，宝宝刚才主动叠了三层积木。"语音自动转为观察记录。
>
> 晚上 WhatsApp 弹出周反馈："本周宝宝精细动作有明显进步，积木从 2 层进步到 3 层。"

| 价值维度 | 量化预期 | 实现路径 |
|----------|----------|----------|
| **日活留存** | DAU 提升 40-60% | 多渠道智能推送 |
| **记录频率** | 周均从 2-3 条提升至 7-10 条 | 语音快捷记录 + 渠道内直接回复 |
| **计划完成率** | 从 30-40% 提升至 60-70% | 定时提醒 + 进度跟踪 |
| **付费转化** | 新增"高级渠道"和"语音无限"订阅层 | 基础推送免费，高级功能付费 |

### 2.2 技术价值：从"单体"到"可插拔"

借鉴 OpenClaw 的技能系统，AI Parenting 后端将从硬编码编排器演进为可插拔技能注册：

**现状**：Orchestrator 内通过 `if session_type == ...` 分支选择渲染器。新增能力需修改 5-8 个文件。

**目标**：每个 AI 能力封装为独立 Skill 模块，Orchestrator 通过 SkillRegistry 动态发现和加载，新增能力只需新建技能目录。

### 2.3 用户价值矩阵

| 能力 | 家长价值 | 产品价值 | 技术价值 | 商业价值 |
|------|---------|----------|----------|----------|
| **微信推送** | 无需切换 App | 国内覆盖 95%+ | 复杂度中等 | 获客成本趋零 |
| **WhatsApp/Telegram** | 海外无缝使用 | 打开国际市场 | OpenClaw 一次对接 | 客单价 3-5x |
| **语音交互** | 带娃时刚需 | 使用频率 2x | 成熟方案 | 可作付费特性 |
| **智能推送** | 不再"忘记"计划 | 留存核心杠杆 | APScheduler + 规则引擎 | 高触达=高转化 |
| **技能系统** | 未来可选装更多能力 | 上架速度 3x | 无需改核心代码 | 平台型收入 |

---

## 三、技术架构设计

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     AI Parenting 系统架构                         │
│                                                                   │
│  [iOS App]    [WeChat 服务号]   [WhatsApp]    [Telegram]         │
│      │              │               │              │              │
│      ▼              ▼               ▼              ▼              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Channel Adapter Layer                           │ │
│  │  APNs Adapter │ WeChat Adapter │ OpenClaw Gateway Adapter   │ │
│  └────────────────────────┬────────────────────────────────────┘ │
│                           ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Message Router (入站意图解析 + 出站渠道分发)                │ │
│  └────────────────────────┬────────────────────────────────────┘ │
│                           ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Skill Registry + Orchestrator                               │ │
│  │  [instant_help] [plan_gen] [weekly_feedback] [sleep] [food] │ │
│  └────────────────────────┬────────────────────────────────────┘ │
│              ┌─────────────┼─────────────┐                        │
│              ▼             ▼             ▼                         │
│  [BoundaryChecker]  [VoicePipeline]  [SmartPushEngine]           │
│                           │                                       │
│                           ▼                                       │
│  [Data Layer: SQLAlchemy + PostgreSQL/SQLite]                     │
│  User│Device│Child│Record│Plan│DayTask│AISession│ChannelBinding  │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 P0：智能推送引擎 — Smart Push Engine

#### 3.2.1 推送规则引擎

```python
# src/ai_parenting/backend/services/smart_push_engine.py

@dataclass
class PushRule:
    rule_id: str                    # 规则唯一标识
    name: str                       # 规则名称
    trigger_type: str               # "cron" | "event" | "milestone"
    cron_expression: str | None     # Cron 触发表达式
    event_type: str | None          # 事件触发类型
    condition: Callable             # 条件判断函数
    message_builder: Callable       # 消息构建函数
    channels: list[str]             # 目标渠道列表
    priority: int                   # 优先级
    cooldown_hours: int             # 冷却时间
```

**内置推送规则：**

| 规则 ID | 触发 | 条件 | 消息 | 渠道优先级 |
|---------|------|------|------|-----------|
| `daily_task_morning` | Cron 08:00 | 有活跃计划且今日未完成 | 今日训练摘要 | 微信 > iOS |
| `record_evening` | Cron 18:00 | 今日无记录 | 温馨提示记录 | 微信 > iOS |
| `milestone_reached` | Event | 月龄跨越 24/36/48 | 里程碑恭喜 | 全渠道 |
| `streak_break_risk` | Cron 20:00 | 连续 ≥3 天今日未记录 | 别断了 | 微信 > iOS |
| `plan_day7_feedback` | Event | 计划到第 7 天 | 邀请查看周反馈 | 全渠道 |
| `low_completion_nudge` | Cron 周三 | 完成率 < 30% | 调整难度建议 | 微信 |
| `inactivity_7d` | Cron 每日 | 7 天无活动 | 召回提醒 | 微信 > WhatsApp |

#### 3.2.2 渠道适配器层

```python
# src/ai_parenting/backend/channels/base.py

class ChannelAdapter(ABC):
    @property
    @abstractmethod
    def channel_name(self) -> str: ...

    @abstractmethod
    async def send_message(self, recipient_id: str, message: ChannelMessage) -> SendResult: ...

    @abstractmethod
    async def receive_message(self, raw_payload: dict) -> InboundMessage | None: ...
```

适配器实现：`APNsAdapter`（iOS 原生推送）、`WeChatAdapter`（微信服务号 API 直连）、`OpenClawAdapter`（通过 WebSocket 连接 OpenClaw Gateway，统一对接 WhatsApp/Telegram/Slack 等）。

#### 3.2.3 数据模型扩展

新增 `ChannelBinding`（用户渠道绑定）和 `PushLog`（推送日志，用于限频和审计）。

```python
class ChannelBinding(Base):
    __tablename__ = "channel_bindings"
    id: Mapped[uuid.UUID]
    user_id: Mapped[uuid.UUID]           # FK → users.id
    channel: Mapped[str]                  # "wechat"|"whatsapp"|"telegram"|"apns"
    channel_user_id: Mapped[str]          # 渠道内用户标识
    is_primary: Mapped[bool]
    is_active: Mapped[bool]
    bound_at: Mapped[datetime]
```

#### 3.2.4 限频与防打扰

每日最多 5 条推送，每小时最多 2 条，安静时段 22:00-08:00 不推送，用户交互后 30 分钟冷却期。

### 3.3 P1：语音交互 — Voice Pipeline

#### 3.3.1 后端语音 API

ASR/TTS 优先使用 iOS 原生能力（Speech.framework + AVSpeechSynthesizer），后端仅接收 ASR 转写后的文本进行意图分类和 Skill 路由：

```python
# src/ai_parenting/backend/routers/voice.py

@router.post("/voice/converse")        # 核心：接收 ASR 文本 → 意图分类 → Skill → 返回文本回复
@router.post("/voice/transcribe")      # [Optional Fallback] iOS ASR 置信度低时的云端 ASR
@router.post("/voice/synthesize")      # [Optional Fallback] 需要高品质拟人语音时的云端 TTS
```

#### 3.3.2 语音处理管线（iOS 原生优先架构）

```
iOS 端主路径:
  SFSpeechRecognizer (流式 ASR) → 转写文本 → POST /voice/converse → AI 文本回复 → AVSpeechSynthesizer (本地 TTS)

后端 /voice/converse 内部流程:
  接收文本 → IntentClassifier (规则+LLM) → Skill 路由 → 返回文本回复（无需处理音频）
```

```python
class VoicePipeline:
    """Text-based: 接收 ASR 转写文本，返回 AI 文本回复（ASR/TTS 由 iOS 端处理）"""

    async def process(self, transcript: str, context: dict) -> VoiceResult:
        intent = await self._classify_intent(transcript)
        skill = self._skills.get(intent.skill_name)
        result = await skill.execute(intent.params, context)
        return VoiceResult(transcript, intent, result.response_text)
```

#### 3.3.3 iOS 客户端语音层（iOS 原生优先）

新增 `VoiceInteractionManager`（基于 Speech.framework 流式 ASR + AVSpeechSynthesizer 本地 TTS）和 `VoiceOverlayView`（底部半屏语音交互界面）。

**核心设计：**
- **ASR**：使用 `SFSpeechRecognizer` + `SFSpeechAudioBufferRecognitionRequest`，`shouldReportPartialResults = true` 实现边说边转写
- **TTS**：使用 `AVSpeechSynthesizer` + `AVSpeechSynthesisVoice(language: "zh-CN")` 本地合成
- **离线支持**：iOS 13+ `supportsOnDeviceRecognition` 设备端模型，无网络也可工作
- **降级策略**：ASR 置信度 < 0.6 时可选调用后端 `/voice/transcribe` 云端 ASR 增强

#### 3.3.4 语音快捷指令

| 指令类别 | 示例 | 操作 |
|----------|------|------|
| 快速记录 | "记录，宝宝自己穿鞋了" | 创建 Record(type=voice) |
| 查看任务 | "今天做什么训练" | 查询当日 DayTask |
| 即时求助 | "宝宝不肯吃饭怎么办" | 触发 instant_help |
| 进度查询 | "这周完成多少" | 返回 completion_rate |

### 3.4 P2：技能系统 — Skill Registry

#### 3.4.1 技能接口

```python
class Skill(ABC):
    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata: ...

    @abstractmethod
    def render_prompt(self, context: ContextSnapshot, **kwargs) -> str: ...

    @abstractmethod
    def parse_result(self, raw_json: str) -> BaseModel: ...

    @abstractmethod
    def get_boundary_rules(self) -> list[BoundaryRule]: ...

    @abstractmethod
    def get_degraded_result(self) -> BaseModel: ...

    def get_router(self) -> APIRouter | None:
        return None
```

#### 3.4.2 技能注册表

```python
class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self._skills: dict[str, Skill] = {}
        self._discover_skills(skills_dir)  # 自动扫描加载

    def get(self, name: str) -> Skill: ...
    def list_skills(self) -> list[SkillMetadata]: ...
    def get_all_routers(self) -> list[APIRouter]: ...
```

#### 3.4.3 迁移计划

| 现有 SessionType | 迁移为 | 目录 |
|------------------|--------|------|
| INSTANT_HELP | instant_help Skill | `skills/instant_help/` |
| PLAN_GENERATION | plan_generation Skill | `skills/plan_generation/` |
| WEEKLY_FEEDBACK | weekly_feedback Skill | `skills/weekly_feedback/` |

#### 3.4.4 未来扩展

| 技能 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `sleep_analysis` | 睡眠分析 | 7 天睡眠记录 | 评估 + 建议 |
| `food_recommend` | 辅食推荐 | 月龄 + 过敏史 | 菜单 + 指南 |
| `language_milestone` | 语言评估 | 语言类记录 | 定位 + 游戏 |

---

## 四、OpenClaw 对接详设

### 4.1 对接模式

```
OpenClaw Gateway (ws://18789)          AI Parenting Backend (FastAPI :8000)
   WhatsApp ←→ Baileys     ──ws──→    OpenClawAdapter
   Telegram ←→ grammY      ──ws──→       │
   Slack    ←→ Bolt         ──ws──→       ▼
                                      Message Router → Skill → Response
```

AI Parenting 通过 Python asyncio WebSocket 客户端连接 OpenClaw Gateway，注册为自定义技能。入站消息经意图解析路由到对应 Skill，出站响应通过 Gateway 回传至用户所在渠道。

**部署策略决策：** OpenClaw Gateway 与 FastAPI 后端**同机云端部署**（Docker Compose 编排）。WhatsApp/Telegram 的长连接特性要求 7×24 在线，本地电脑的休眠/断网会导致消息丢失和 session 失效。同机部署使 WebSocket 通信走 localhost/Docker 内部网络（延迟 < 1ms），且 Node.js 进程仅占约 100-200MB 内存，与后端共享现有服务器零增量成本。开发阶段可在本地运行（`ws://localhost:8765`），通过环境变量 `AIP_OPENCLAW_WS_URL` 实现开发/生产无缝切换。详见 `2026-03-17-architecture-optimization.md` 第 2.7 节。

### 4.2 微信独立对接

微信生态因封闭性不经 OpenClaw 中转，直接对接微信公众平台 API：模板消息用于定时推送，客服消息用于 48h 内对话交互。Webhook 端点接收用户消息并路由到 Message Router。

### 4.3 安全设计

所有渠道入站消息均经过 BoundaryChecker 边界检查，确保 AI 响应的安全性。渠道层增加消息签名验证（微信签名/OpenClaw session token），防止伪造请求。用户渠道绑定需通过验证码二次确认。

---

## 五、优先级排序说明与依赖关系

### 5.1 为什么 P0 > P1 > P2

**P0 智能推送** 排最高，因为多渠道推送直接影响产品核心指标（DAU、留存率），且是后续所有能力的基础设施——语音交互和技能系统生成的结果都需要通过渠道分发给用户。

**P1 语音交互** 次之，因为语音是育儿场景的刚需交互方式（带娃时双手不空闲），对使用频率提升有直接拉动作用。

**P2 技能系统** 排最低，因为它是架构重构而非面向用户的新功能，对终端用户无直接感知价值，但为后续所有新能力扩展奠定基础。

### 5.2 关键依赖关系

**P1 对 P2 的前置依赖**：VoicePipeline 中意图路由需要调用 Skill 接口（`self._skills.get(intent.skill_name)`）。解决方案如下：在 Phase 2（W5）开始时，提前引入**最小化 Skill 接口抽象**（仅含 `Skill` ABC 和硬编码的 `SimpleSkillRouter`），不实现完整的 SkillRegistry 自动发现。Phase 3 再将 SimpleSkillRouter 替换为完整的 SkillRegistry。

```
Phase 1: Channel Adapter + Smart Push Engine (无外部依赖)
Phase 2: Voice Pipeline + 最小化 Skill 接口 (前置：Phase 1 渠道层)
Phase 3: 完整 SkillRegistry 重构 (前置：Phase 2 最小化接口)
```

---

## 六、第三方服务选型

| 服务 | 首选方案 | 备选方案 | 成本预估 |
|------|----------|----------|----------|
| **STT（语音转文字）** | iOS 原生 Speech.framework（零延迟、离线、免费） | 腾讯云 ASR（iOS ASR 置信度 < 0.6 时降级） | 免费（iOS 原生）/ ¥0.6/分钟（腾讯 Fallback） |
| **TTS（文字转语音）** | iOS 原生 AVSpeechSynthesizer（零延迟、离线、免费） | 腾讯云 TTS（需要高品质拟人语音时） | 免费（iOS 原生）/ ¥0.2/千字符（腾讯 Fallback） |
| **意图分类** | 基于关键词规则 + 正则匹配（Phase 2） | LLM 意图分类（Phase 3 升级） | 规则匹配免费 / LLM ¥0.01/次 |
| **OpenClaw Gateway** | 自建部署（同服务器 Docker） | — | 服务器资源，无额外 API 费用 |
| **微信模板消息** | 微信公众平台 API（认证服务号） | — | 免费（需服务号认证费 ¥300/年） |
| **WhatsApp Business** | 通过 OpenClaw Baileys（非官方） | Meta Business API（官方，有费用） | 免费（Baileys）/ $0.05-0.08/条（官方） |

---

## 七、实施路线图

**前置准备（W0，在 Phase 1 前完成）：** 申请微信服务号（或用测试号）、注册腾讯云 ASR/TTS 服务、搭建 OpenClaw Gateway Docker 环境、生成 APNs 证书。

**团队配置假设：** 1 名后端 + 1 名 iOS 开发并行，W11 为集成测试缓冲周。

### Phase 1（W1-W4，4 周）— P0 智能推送引擎

| 周次 | 后端任务 | iOS 任务 | Done 条件 |
|------|----------|----------|-----------|
| W1 | ChannelAdapter 抽象层 + APNsAdapter | 渠道偏好设置页 | APNs 真机推送成功 |
| W2 | SmartPushEngine + ChannelBinding/PushLog 模型 | 推送权限引导 | 7 条规则可触发 |
| W3 | WeChatAdapter + 微信 Webhook | 微信扫码绑定流程 | 微信模板消息收发通 |
| W4 | OpenClawAdapter + WhatsApp/Telegram | 全渠道消息列表 | 3 渠道推送端到端通 |

### Phase 2（W5-W7，3 周）— P1 语音交互

| 周次 | 后端任务 | iOS 任务 | Done 条件 |
|------|----------|----------|-----------|
| W5 | Voice API + 最小化 Skill 接口 | VoiceInteractionManager | STT/TTS API 可用 |
| W6 | VoicePipeline + 意图分类（规则） | VoiceOverlayView | 语音对话闭环 |
| W7 | 语音记录自动入库 + 联调 | 语音快捷指令 | 5 种指令全部通过 |

### Phase 3（W8-W10，3 周）— P2 技能系统

| 周次 | 后端任务 | iOS 任务 | Done 条件 |
|------|----------|----------|-----------|
| W8 | Skill 接口 + SkillRegistry | 技能列表页 | 自动发现加载 3 技能 |
| W9 | 迁移 3 个 SessionType | Orchestrator 适配 | 全部现有功能回归通过 |
| W10 | sleep_analysis 示范技能 | 技能详情页 | 新技能端到端可用 |

### W11 — 集成测试与上架准备

全链路回归测试、App Store 审核提交、微信服务号正式切换、性能压测。

---

## 八、风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 | 回退方案 |
|------|------|------|----------|----------|
| 微信服务号审核周期长 | 推送功能延期 | 高 | 测试号先行开发，并行提交审核 | 先上 APNs + WhatsApp |
| OpenClaw API 不稳定 | WhatsApp/Telegram 中断 | 中 | 本地消息队列缓存 + 重试 | 降级为 iOS Push |
| 语音识别准确率（育儿术语） | 用户体验差 | 中 | 自定义热词表 + 人工纠错入口 | 保留文字输入为主路径 |
| 推送过度打扰 | 用户关闭通知/卸载 | 中 | 严格限频 + 用户可自定义频率 | 默认仅开启 2 条/天 |
| 技能系统过度设计 | 开发周期膨胀 | 低 | 先迁移现有 3 个，验证后再扩展 | 保留现有 Orchestrator 不变 |
| 多实例部署推送重复 | 用户收到重复消息 | 中 | APScheduler 使用 DB JobStore | 单实例调度 + 分布式锁 |
| 用户时区推送错乱 | 半夜收到推送 | 中 | 推送时间基于 user.timezone 偏移 | 默认 Asia/Shanghai |

---

## 九、国际化与时区处理

所有推送时间基于用户 `User.timezone` 字段计算（已有，默认 `Asia/Shanghai`）。SmartPushEngine 在评估 Cron 规则时，将 UTC 时间转换为用户本地时间后判断是否在活跃时段内。安静时段（22:00-08:00）同样基于用户本地时间。

消息模板支持中/英双语，根据用户 locale 偏好选择。初期中文为主，英文版作为 Phase 1 W4 的附加交付。

---

*文档版本：v1.1 | 日期：2026-03-16 | 作者：AI Parenting Team*
*v1.1 变更：修复 P1/P2 依赖倒置、补充第三方选型/时区/团队/验收标准/回退方案*
