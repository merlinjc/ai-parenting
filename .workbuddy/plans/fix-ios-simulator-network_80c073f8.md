---
name: fix-ios-simulator-network
overview: 修复 iOS 模拟器上的网络连接失败问题（DNS 解析被沙箱阻止），通过将 baseURL 中的 localhost 替换为 127.0.0.1 绕过 DNS 解析，并确保项目配置支持 HTTP 明文请求。
todos:
  - id: fix-baseurl
    content: 修改 AppConfig.swift 将 default 和 development 两处 baseURL 从 localhost 改为 127.0.0.1
    status: completed
---

## 用户需求

iOS 端在模拟器上运行时，请求后端 API 报网络错误 `NSURLErrorDomain Code=-1003 "A server with the specified hostname could not be found."`。后端服务已确认正常运行在 8000 端口。

## 产品概述

修复 iOS 模拟器环境下的网络连接问题，使 App 能正常访问本地后端 API。

## 核心问题

- iOS 模拟器的 Sandbox 环境限制了 DNS 解析服务（`com.apple.dnssd.service`），导致 `localhost` 主机名无法被解析
- 将 `baseURL` 从 `http://localhost:8000` 改为 `http://127.0.0.1:8000`，绕过 DNS 解析，直接使用 IP 地址
- `AppConfig.swift` 中 `default` 和 `development` 两处配置均需修改

## 技术栈

- iOS Swift Package（Swift 5.9，iOS 17+）
- 网络层：URLSession（`APIClient` 从 `AppConfig.baseURL` 读取基础 URL）

## 实现方案

将 `AppConfig.swift` 中两处 `http://localhost:8000` 替换为 `http://127.0.0.1:8000`。`127.0.0.1` 是回环地址的 IP 形式，不需要经过 DNS 解析，可以绕过模拟器 Sandbox 对 `com.apple.dnssd.service` 的限制。

### 技术决策

- **选择 `127.0.0.1` 而非 `localhost`**：iOS 模拟器 Sandbox 阻止了 DNS 解析服务，`localhost` 需要 DNS 解析才能转为 `127.0.0.1`，而直接使用 IP 地址无需 DNS 解析
- **不引入额外的 ATS 配置**：项目是 Swift Package（library），没有独立的 Info.plist；iOS 17 模拟器对回环地址的 HTTP 明文请求默认放行，无需额外的 NSAppTransportSecurity 配置
- **修改范围最小化**：仅修改一个文件中两处字符串常量，不涉及架构变更

## 实现要点

- 确认全仓库仅 `AppConfig.swift` 一个文件包含 `localhost` 引用（已验证）
- `default` 和 `development`（`#if DEBUG`）两处配置都需要修改
- 修改后无需改动 `APIClient`、`Endpoint` 等网络层代码，URL 构建逻辑不受影响

## 目录结构

```
ios/Sources/AIParenting/Core/Config/
└── AppConfig.swift  # [MODIFY] 将两处 baseURL 中的 "localhost" 替换为 "127.0.0.1"
```