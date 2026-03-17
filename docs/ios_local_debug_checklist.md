# iOS 客户端 × 本地后端联调准备清单

> 最后更新：2026-03-17
>
> 本文档覆盖 iOS 模拟器/真机与本地 FastAPI 后端的联调环境搭建，包括网络配置、环境依赖、接口调试工具及常见问题排查。

---

## 一、环境依赖

### 1.1 Xcode 版本要求

| 项目 | 要求 | 说明 |
|------|------|------|
| **Xcode 版本** | ≥ 15.0 | `Package.swift` 声明 `swift-tools-version: 5.9`，平台要求 `.iOS(.v17)` |
| **iOS Deployment Target** | ≥ 17.0 | 使用了 `@Observable` / `Observation` 框架（iOS 17+） |
| **推荐模拟器** | iPhone 15 / 16 系列 (iOS 17+) | 也可用真机（需额外配置，见第三节） |

### 1.2 Python 后端依赖

```bash
# 进入项目根目录
cd /path/to/ai-parenting

# 创建并激活虚拟环境
python3.12 -m venv .venv
source .venv/bin/activate

# 安装依赖（含开发 + 推送依赖）
pip install -e ".[dev,push]"
```

> ⚠️ 项目要求 `requires-python = ">=3.11"`，推荐使用 **Python 3.12**（Dockerfile 基于 `python:3.12-slim`）。

### 1.3 后端服务端口

| 服务 | 默认端口 | 说明 |
|------|----------|------|
| **FastAPI 后端** | `8000` | iOS `AppConfig.development` 指向 `http://127.0.0.1:8000` |
| **OpenClaw Gateway (WS)** | `8765` | 后端 `config.py` 默认 `ws://localhost:8765` |
| **OpenClaw Gateway (HTTP)** | `18789` | 管理端口（健康检查） |
| **PostgreSQL** | `5432` | 仅生产 profile，开发环境用 SQLite |

### 1.4 数据库（开发环境 — 零配置）

开发环境**默认使用 SQLite**，无需额外安装数据库：

```python
# config.py 默认值
database_url: str = "sqlite+aiosqlite:///./ai_parenting_dev.db"
```

应用首次启动时通过 `lifespan` 事件**自动建表 + 插入种子数据**，无需手动执行迁移。

> 如需 PostgreSQL，通过环境变量覆盖：
> ```bash
> export AIP_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/ai_parenting"
> ```

---

## 二、启动后端服务

### 2.1 最小启动（仅后端，推荐联调用）

```bash
cd /path/to/ai-parenting
source .venv/bin/activate

# 直接启动 FastAPI（使用默认 SQLite + mock AI provider）
python -m uvicorn ai_parenting.backend.app:app --host 0.0.0.0 --port 8000 --reload
```

关键参数说明：

| 参数 | 作用 | 必要性 |
|------|------|--------|
| `--host 0.0.0.0` | 监听所有网卡，真机可通过局域网 IP 访问 | **必须** |
| `--port 8000` | 与 iOS `AppConfig.development` 匹配 | **必须** |
| `--reload` | 代码修改后自动重载 | 推荐 |

### 2.2 验证后端健康状态

```bash
curl http://127.0.0.1:8000/health
# 期望返回: {"status":"ok","version":"0.3.0"}
```

### 2.3 使用 Docker Compose 启动（完整环境，含 Gateway）

```bash
# 创建 .env 文件
cat > .env << 'EOF'
AI_PROVIDER=mock
JWT_SECRET=dev-secret-change-in-production
OPENCLAW_API_KEY=dev-test-key
WHATSAPP_ENABLED=false
TELEGRAM_ENABLED=false
EOF

docker compose up backend gateway
```

---

## 三、网络配置

### 3.1 iOS 模拟器联调（最简配置 — 开箱即用）

模拟器直接使用 `127.0.0.1`，项目已完整配置，**无需额外修改**：

**AppConfig.swift — 开发环境自动选择：**

```swift
// 开发环境配置
public static let development = AppConfig(
    baseURL: URL(string: "http://127.0.0.1:8000")!,
    requestTimeout: 30,
    aiRequestTimeout: 60,
    pollingInterval: 2,
    defaultPageSize: 20
)

// 默认配置：DEBUG → development，Release → production
public static let `default`: AppConfig = {
    #if DEBUG
    return .development
    #else
    return .production
    #endif
}()
```

### 3.2 ATS (App Transport Security) 已配置

`Info.plist` 已允许 `127.0.0.1` 的 HTTP 明文传输：

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSExceptionDomains</key>
    <dict>
        <key>127.0.0.1</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
            <key>NSIncludesSubdomains</key>
            <false/>
        </dict>
    </dict>
</dict>
```

> ✅ 模拟器联调无需 HTTPS 证书，当前配置已可直接使用。

### 3.3 真机联调（需额外配置）

如果使用 **iPhone 真机**而非模拟器，需要做以下调整：

#### Step 1 — 获取 Mac 本地 IP

```bash
# 获取 Mac 的局域网 IP（Wi-Fi）
ipconfig getifaddr en0
# 例如: 192.168.1.100
```

#### Step 2 — 修改 AppConfig.swift 中的开发 URL

```swift
// 真机联调：替换为 Mac 的局域网 IP
public static let development = AppConfig(
    baseURL: URL(string: "http://192.168.1.100:8000")!,  // ← 改这里
    requestTimeout: 30,
    aiRequestTimeout: 60,
    pollingInterval: 2,
    defaultPageSize: 20
)
```

#### Step 3 — 更新 Info.plist ATS 配置

在 `NSExceptionDomains` 中追加局域网 IP：

```xml
<key>192.168.1.100</key>
<dict>
    <key>NSExceptionAllowsInsecureHTTPLoads</key>
    <true/>
    <key>NSIncludesSubdomains</key>
    <false/>
</dict>
```

或者使用更宽松的开发配置（**仅限 DEBUG，切勿上线**）：

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsLocalNetworking</key>
    <true/>
</dict>
```

#### Step 4 — 确保同一 Wi-Fi 网络

- Mac 和 iPhone 连接**同一个 Wi-Fi 网络**
- macOS 防火墙需允许 `uvicorn` 进程的入站连接（系统设置 → 网络 → 防火墙）
- 后端启动时 `--host 0.0.0.0` 是**必须的**

### 3.4 公司网络特殊情况

| 问题 | 解决方案 |
|------|----------|
| Wi-Fi 有 AP 隔离（设备互不可见） | 切换到手机热点，或使用 USB 连接 + 网络共享 |
| VPN 干扰 | 联调时暂时断开 VPN，或在 VPN Split Tunnel 中排除局域网段 |
| 公司防火墙拦截 8000 端口 | 改用常见端口（如 3000、80），或使用模拟器绕过 |

---

## 四、接口调试工具

### 4.1 Swagger UI（内置）

后端自动生成 OpenAPI 文档，浏览器直接访问：

```
http://127.0.0.1:8000/docs         ← Swagger UI（交互式 API 文档）
http://127.0.0.1:8000/redoc        ← ReDoc（只读文档）
http://127.0.0.1:8000/openapi.json ← OpenAPI 3.0 规范（可导入 Postman）
```

### 4.2 Postman 配置

#### 导入 API 规范

1. Postman → Import → 粘贴 `http://127.0.0.1:8000/openapi.json`
2. 自动生成全部端点集合

#### 配置环境变量

在 Postman 中创建 `AI Parenting Dev` 环境：

| 变量 | 值 |
|------|------|
| `base_url` | `http://127.0.0.1:8000` |
| `token` | （登录后填入） |

#### 认证流程测试

```http
### 1. 注册
POST {{base_url}}/api/v1/auth/register
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "Test123!"
}

### 2. 登录获取 token
POST {{base_url}}/api/v1/auth/login
Content-Type: application/json

{
  "email": "test@example.com",
  "password": "Test123!"
}
# 响应中获取 access_token，填入环境变量 token

### 3. 后续请求添加 Header
Authorization: Bearer {{token}}
```

### 4.3 Charles 抓包配置

#### 模拟器抓包（推荐）

1. 启动 Charles → Proxy → macOS Proxy（确保勾选）
2. 模拟器的 HTTP 流量会自动经过 Charles（共享 Mac 网络代理）
3. 在 Charles 中 Focus 过滤 `127.0.0.1:8000`

#### 真机抓包

1. Charles → Help → SSL Proxying → Install Certificate on a Mobile Device
2. iPhone 中 Wi-Fi → HTTP 代理 → 手动 → 服务器填 Mac IP，端口 `8888`
3. Safari 访问 `chls.pro/ssl` 安装 CA 证书
4. 设置 → 通用 → 关于 → 证书信任设置 → 开启 Charles 证书

> 💡 本项目开发环境全程 HTTP，Charles 无需额外配置 SSL Proxying。

### 4.4 快速 cURL 验证脚本

```bash
#!/bin/bash
# 文件名: debug_api.sh
# 用法: chmod +x debug_api.sh && ./debug_api.sh

BASE="http://127.0.0.1:8000"

echo "=== 1. 健康检查 ==="
curl -s "$BASE/health" | python3 -m json.tool

echo -e "\n=== 2. 注册 ==="
REGISTER=$(curl -s -X POST "$BASE/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"debug@test.com","password":"Debug123!"}')
echo "$REGISTER" | python3 -m json.tool

echo -e "\n=== 3. 登录 ==="
LOGIN=$(curl -s -X POST "$BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"debug@test.com","password":"Debug123!"}')
echo "$LOGIN" | python3 -m json.tool
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo -e "\n=== 4. 当前用户 ==="
curl -s "$BASE/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

echo -e "\n=== 5. OpenAPI 文档可达性 ==="
curl -s -o /dev/null -w "HTTP %{http_code}" "$BASE/openapi.json"
echo ""
```

---

## 五、必要的代码调整

### 5.1 API Base URL（通常无需修改）

| 场景 | Base URL | 配置位置 |
|------|----------|----------|
| **模拟器** | `http://127.0.0.1:8000` | `AppConfig.development`（已配置） |
| **真机** | `http://<Mac-IP>:8000` | 需修改 `AppConfig.development` |
| **生产** | `https://api.aiparenting.example.com` | `AppConfig.production`（上线前替换） |

DEBUG 构建自动使用 `development` 配置，**模拟器联调零代码修改**。

### 5.2 HTTPS 证书配置

| 环境 | 是否需要 HTTPS | 说明 |
|------|----------------|------|
| 模拟器联调 | ❌ 不需要 | ATS 已放行 `127.0.0.1` 的 HTTP |
| 真机联调 | ❌ 不需要 | 添加 `NSAllowsLocalNetworking` 即可 |
| 生产环境 | ✅ 必须 | 反向代理（Nginx/Caddy）提供 TLS |

### 5.3 环境变量配置（.env 文件）

开发环境**全部使用默认值即可**，无需配置 `.env` 文件：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AIP_DATABASE_URL` | `sqlite+aiosqlite:///./ai_parenting_dev.db` | SQLite 零配置 |
| `AIP_AI_PROVIDER` | `mock` | 使用模拟 AI 响应 |
| `AIP_JWT_SECRET_KEY` | `ai-parenting-dev-secret-key-change-in-prod` | 开发环境内置 |
| `AIP_PUSH_PROVIDER` | `channel_router` | 未配置凭据时自动降级为 Mock |

### 5.4 iOS 项目打开方式

```bash
# 方式 1: 通过 Xcode 项目打开（推荐）
open ios/DevApp/DevApp.xcodeproj

# 方式 2: 通过 SPM Package 打开（仅编辑库代码）
open ios/Package.swift
```

> 联调时使用方式 1（xcodeproj），它包含 Info.plist、Entitlements 等完整配置。

---

## 六、常见连接问题排查

### 6.1 快速排查速查表

| 症状 | 排查命令 | 解决方案 |
|------|----------|----------|
| `Connection refused` | `lsof -i :8000` | 后端未启动 / 端口被占用 |
| `Could not connect to server` | `curl http://127.0.0.1:8000/health` | 确认后端进程存活 |
| 模拟器连不上 `127.0.0.1` | 检查 uvicorn 监听地址 | 必须用 `--host 0.0.0.0` |
| 真机连不上 Mac | `ping <Mac-IP>`（从手机） | 同网段 + 防火墙放行 |
| 请求返回 `401 Unauthorized` | 检查 `Authorization` header | JWT token 过期 → 重新登录 |
| 请求返回 `422 Unprocessable Entity` | 查看响应体 `detail` 字段 | 请求体字段缺失或类型错误 |
| 模拟器无网络 | Device → Erase All Content and Settings | 模拟器网络栈异常，重置即可 |
| `NSURLErrorDomain -1004` | 检查 ATS 配置 | Info.plist 缺少 HTTP 例外配置 |
| `NSURLErrorDomain -1001` | 检查超时配置 | 普通请求 30s，AI 请求 60s/90s |
| 响应日期解码失败 | 检查后端日期格式 | iOS 端 APIClient 支持 6 种日期格式 |

### 6.2 端口占用排查

```bash
# 查看 8000 端口占用
lsof -i :8000

# 杀掉占用进程
kill -9 $(lsof -t -i :8000)

# 查看所有监听端口
lsof -iTCP -sTCP:LISTEN -P | grep LISTEN
```

### 6.3 后端日志实时查看

后端已内置请求日志中间件（`app.py` 中的 `access_log_middleware`），会输出每个请求的方法、路径、状态码和耗时：

```
INFO: POST /api/v1/auth/login 200 45ms
INFO: GET  /api/v1/children 200 12ms
INFO: POST /api/v1/memory/initialize 201 234ms
```

在终端中查看 uvicorn 输出即可，无需额外配置。

### 6.4 iOS 端网络调试

Xcode 控制台中搜索关键日志前缀：

- `[Onboarding]` — 注册引导流程
- `[API]` — 网络请求（如果有打印）

可在 `APIClient.executeRequest` 中临时添加调试日志：

```swift
#if DEBUG
print("[API] \(endpoint.method) \(endpoint.path) → \(httpResponse.statusCode)")
#endif
```

### 6.5 SQLite 数据库检查

```bash
# 查看数据库文件
ls -la ai_parenting_dev.db

# 使用 sqlite3 查看表结构
sqlite3 ai_parenting_dev.db ".tables"

# 查看用户数据
sqlite3 ai_parenting_dev.db "SELECT id, email FROM users LIMIT 5;"

# 删除数据库重新初始化（重启后端自动重建）
rm ai_parenting_dev.db
```

---

## 七、完整联调验证流程

按以下顺序逐步验证，每步确认通过后再进入下一步：

```
□ Step 1: 后端启动
    $ python -m uvicorn ai_parenting.backend.app:app --host 0.0.0.0 --port 8000 --reload
    验证: curl http://127.0.0.1:8000/health → {"status":"ok","version":"0.3.0"}

□ Step 2: OpenAPI 文档可达
    浏览器打开 http://127.0.0.1:8000/docs
    验证: 看到 Swagger UI 且所有端点列出

□ Step 3: Postman 认证流程
    POST /api/v1/auth/register → 201
    POST /api/v1/auth/login    → 200 + access_token
    GET  /api/v1/users/me      → 200（Bearer token）

□ Step 4: Xcode 构建
    打开 ios/DevApp/DevApp.xcodeproj
    选择 iPhone 模拟器 (iOS 17+)
    Cmd+B 编译通过

□ Step 5: 模拟器运行
    Cmd+R 运行 App
    验证: 看到登录页面

□ Step 6: 端到端注册流程
    App 中注册新用户 → 登录 → 进入 Onboarding
    后端终端确认收到请求日志
    完成 Onboarding → 进入主页

□ Step 7: 核心接口验证
    创建育儿记录    → POST /api/v1/records       → 201
    查看首页数据    → GET  /api/v1/home/dashboard → 200
    即时求助        → POST /api/v1/ai/instant-help → 200
    记忆初始化      → POST /api/v1/memory/initialize → 201
```

---

## 八、快速参考卡片

```
┌─────────────────────────────────────────────────────────┐
│              iOS ↔ 本地后端联调速查                       │
├─────────────────────────────────────────────────────────┤
│  后端启动:                                               │
│    uvicorn ai_parenting.backend.app:app \                │
│      --host 0.0.0.0 --port 8000 --reload                │
│                                                         │
│  iOS 指向:                                               │
│    模拟器 → http://127.0.0.1:8000 (已配置)               │
│    真机   → http://<Mac-IP>:8000 (需改 AppConfig)        │
│                                                         │
│  数据库:  SQLite (零配置，自动建表)                        │
│  AI:     mock 模式 (无需 API Key)                        │
│  认证:    JWT (dev secret 已内置)                         │
│  ATS:    127.0.0.1 HTTP 已放行                           │
│                                                         │
│  调试入口:                                               │
│    Swagger UI  → http://127.0.0.1:8000/docs              │
│    OpenAPI     → http://127.0.0.1:8000/openapi.json      │
│    Health      → http://127.0.0.1:8000/health            │
│                                                         │
│  关键文件:                                               │
│    AppConfig   → ios/.../Core/Config/AppConfig.swift      │
│    ATS 配置    → ios/DevApp/Info.plist                    │
│    后端配置    → src/ai_parenting/backend/config.py       │
│    API 端点    → ios/.../Core/Network/Endpoint.swift      │
└─────────────────────────────────────────────────────────┘
```

---

## 附录 A: 项目关键文件路径

| 文件 | 路径 | 说明 |
|------|------|------|
| iOS 项目入口 | `ios/DevApp/DevApp.xcodeproj` | Xcode 项目文件 |
| App 配置 | `ios/Sources/AIParenting/Core/Config/AppConfig.swift` | Base URL / 超时 |
| ATS 配置 | `ios/DevApp/Info.plist` | HTTP 例外域名 |
| Entitlements | `ios/DevApp/DevApp.entitlements` | 网络权限 |
| API 客户端 | `ios/Sources/AIParenting/Core/Network/APIClient.swift` | 网络层 |
| 端点定义 | `ios/Sources/AIParenting/Core/Network/Endpoint.swift` | 全部 API 端点 |
| 后端入口 | `src/ai_parenting/backend/app.py` | FastAPI 应用 |
| 后端配置 | `src/ai_parenting/backend/config.py` | 环境变量映射 |
| Docker | `docker-compose.yml` | 完整环境编排 |
| Gateway | `gateway/index.js` | OpenClaw 网关 |

## 附录 B: 后端 API 端点总览

后端共注册 **50+ 个端点**，全部挂载在 `/api/v1` 前缀下。主要模块：

| 模块 | 前缀 | 关键端点 |
|------|------|----------|
| 认证 | `/auth` | register, login, refresh-token |
| 用户 | `/users` | me, profile |
| 儿童 | `/children` | CRUD, complete-onboarding, refresh-stage |
| 记录 | `/records` | CRUD, 按类型/日期筛选 |
| 计划 | `/plans` | 创建, 详情, 每日任务完成 |
| AI | `/ai` | instant-help |
| 语音 | `/voice` | converse, transcribe, synthesize |
| 技能 | `/skills` | 列表, sleep-analysis |
| 记忆 | `/memory` | initialize |
| 渠道 | `/channels` | bind, unbind, preferences |
| 消息 | `/messages` | 列表, 标记已读 |
| 首页 | `/home` | dashboard |
| 周反馈 | `/weekly-feedbacks` | 列表, 详情, 决策提交 |
| 设备 | `/devices` | register |
| 文件 | `/files` | upload |
| 管理 | `/admin` | push-rules, channel-stats |

完整交互式文档请访问：`http://127.0.0.1:8000/docs`
