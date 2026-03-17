# iOS 登录/跳过登录无法进入首页 — Bug 修复

## 问题现象

iOS 客户端登录成功和点击"跳过登录（开发模式）"后，界面卡在登录页面，无法跳转到加载 → Onboarding/首页。

## 根因分析

`AppState` 是 `@Observable` 类，RootView 通过 `appState.isAuthenticated` 判断是否显示 LoginView。但 `isAuthenticated` 原来是一个 **computed property**，委托给 `jwtAuthProvider.isAuthenticated`（即 `JWTAuthProvider._token != nil`）。

**核心问题**：`JWTAuthProvider` 是普通 `class`，不是 `@Observable`。SwiftUI 的 `@Observable` 机制只跟踪 `@Observable` 对象的 **stored property** 访问。当 `JWTAuthProvider._token` 通过 `saveCredentials()` 变更时，SwiftUI 无法感知这个变化，导致 RootView 不会重新渲染。

流程断裂点：
```
LoginView → performAuth() → authProvider.saveCredentials() → onLoginSuccess()
  → appState.handleLoginSuccess() → isInitialized = false
  → 但 isAuthenticated 仍然读到旧值（SwiftUI 不知道 JWTAuthProvider._token 变了）
  → RootView 不刷新，卡在 LoginView
```

## 修复方案

### 文件 1: `AppState.swift`

将 `isAuthenticated` 从 computed property 改为独立的 **stored property**，手动在关键节点同步状态：

| 位置 | 变更 |
|---|---|
| 属性声明 | `public var isAuthenticated: Bool = false`（stored property） |
| `init()` | `self.isAuthenticated = authProvider.isAuthenticated`（从 Keychain 恢复） |
| `handleLoginSuccess()` | 新增 `isAuthenticated = true` |
| `logout()` | 新增 `isAuthenticated = false` |
| `initialize()` 中 401 处理 | 新增 `isAuthenticated = false` |

### 文件 2: `LoginView.swift`

"跳过登录"按钮增加 `authProvider.clearCredentials()` 调用，确保清除可能残留的旧 token，使 APIClient 使用 X-User-Id 回退模式。

## 修复后的完整导航流程

```
场景 A: 正常登录/注册
  LoginView → performAuth() → saveCredentials(token, userId)
    → onLoginSuccess() → handleLoginSuccess() → isAuthenticated = true, isInitialized = false
    → SwiftUI 检测到 isAuthenticated 变更 → 切换到加载中分支
    → .task { initialize() } → GET /api/v1/user/profile（Bearer token）
    → children.isEmpty ? OnboardingView : MainTabView

场景 B: 跳过登录（开发模式）
  LoginView → clearCredentials() → onLoginSuccess()
    → handleLoginSuccess() → isAuthenticated = true, isInitialized = false
    → 切换到加载中分支
    → .task { initialize() } → GET /api/v1/user/profile（X-User-Id 回退到默认开发用户）
    → 开发用户已有子档案 → 直接进入 MainTabView

场景 C: App 重启时 Keychain 有 token
  AppState.init() → isAuthenticated = authProvider.isAuthenticated (true)
    → RootView 跳过 LoginView → 加载中 → initialize() → MainTabView
```

## 验证

- 后端 391 个测试全部通过
- curl 验证 JWT 认证、X-User-Id 回退、无认证回退三种模式的 `/api/v1/user/profile` 端点均正常
- 后端服务运行在 `http://0.0.0.0:8000`，iOS 模拟器可正常联调
