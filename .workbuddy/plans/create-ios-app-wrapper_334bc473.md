---
name: create-ios-app-wrapper
overview: 为 Swift Package 创建一个 Xcode App 项目 wrapper（DevApp target），包含 @main 入口、App Sandbox entitlements（开启网络权限）和 Info.plist（ATS 例外），使 App 能在 iOS 模拟器上正常发起网络请求。
todos:
  - id: create-devapp-files
    content: 在 ios/DevApp/ 下创建 AppEntry.swift（@main 入口）、Info.plist（ATS 例外配置 127.0.0.1）、DevApp.entitlements（网络出站权限）
    status: completed
  - id: create-xcodegen-config
    content: 创建 project.yml（XcodeGen 配置），定义 iOS 17 App target、本地 AIParenting Package 依赖、签名和 entitlements 关联
    status: completed
    dependencies:
      - create-devapp-files
  - id: generate-xcodeproj
    content: 安装 xcodegen（如未安装）并运行 xcodegen generate 生成 DevApp.xcodeproj，验证项目可用 xcodebuild 编译通过
    status: completed
    dependencies:
      - create-xcodegen-config
---

## 用户需求

iOS 模拟器运行时报错 `connectx failed: [1: Operation not permitted]`，App Sandbox 阻止了所有网络出站连接，导致无法访问本地后端 API。

## 产品概述

为纯 Swift Package 项目创建一个最小化的 Xcode App 宿主工程，配置正确的 Sandbox 权限和 ATS 例外，使 App 能在 iOS 模拟器上正常发起网络请求。

## 核心问题

- 当前项目是纯 Swift Package（library target），没有独立的 Xcode App 工程
- 通过 Xcode "Open Package" 方式运行时，进程被 App Sandbox 限制，禁止网络出站连接（`connectx failed: Operation not permitted`）
- 需要一个带有正确 entitlements 和 Info.plist 的 App target 来承载网络权限
- 现有 `AIParentingApp` 故意不带 `@main`（注释明确说明"在 Xcode 项目中新建一个 App 入口文件"），这正是项目设计的使用方式

## 技术栈

- iOS Swift (Swift 5.9, iOS 17+)
- SwiftUI App 生命周期
- Xcode Project (pbxproj) + Swift Package 本地依赖
- URLSession 网络层（已有，无需修改）

## 实现方案

在 `ios/` 目录下创建一个最小化的 Xcode App 工程 `AIParentingApp.xcodeproj`，通过本地 Swift Package 依赖引用现有的 `AIParenting` library。App 工程仅包含三个关键文件：

1. **App 入口文件**（`@main`）：导入 `AIParenting` library，创建 `AIParentingApp` 实例
2. **Info.plist**：配置 `NSAppTransportSecurity` 允许 `127.0.0.1` 的 HTTP 明文请求
3. **Entitlements 文件**：配置 `com.apple.security.network.client = true` 允许网络出站连接

### 关键技术决策

- **创建独立 App 工程而非修改 Package.swift**：Swift Package Manager 不支持 `.executableTarget` 配置 entitlements 和 Info.plist，只有 Xcode App target 才能正确配置 Sandbox 权限。这也符合 `AIParentingApp.swift` 注释中的设计意图
- **本地 Package 依赖而非远程**：App 工程通过相对路径引用 `ios/` 下的 Package.swift，开发时代码修改实时生效
- **最小化 App 工程**：仅包含入口文件 + 配置文件，所有业务代码保持在 Swift Package 中不变
- **保留现有 `AIParentingApp` 不带 `@main`**：不修改 library 代码，App 入口由宿主工程的独立文件提供
- **ATS 仅允许 `127.0.0.1`**：不使用 `NSAllowsArbitraryLoads`（全局禁用 ATS 不安全），而是针对 `127.0.0.1` 单独配置例外，生产环境使用 HTTPS 不受影响

## 实现要点

- Xcode 项目文件（`.pbxproj`）格式复杂，手动编写容易出错。使用 `xcodegen` 或 `swift package generate-xcodeproj` 等工具辅助生成，或直接通过 Xcode 命令行创建
- App target 的 Bundle Identifier 设为 `com.aiparenting.dev`（开发用）
- Deployment Target 设为 iOS 17.0，与 Package.swift 的 `platforms` 保持一致
- 入口文件 `AppEntry.swift` 仅包含 `@main` 标注和对 `AIParentingApp` 的透传调用

## 目录结构

```
ios/
├── Package.swift                          # [UNCHANGED] 现有 Swift Package 定义
├── Sources/AIParenting/                   # [UNCHANGED] 所有业务代码保持不变
├── Tests/AIParentingTests/                # [UNCHANGED] 测试代码保持不变
└── DevApp/                                # [NEW] 最小化 Xcode App 宿主工程目录
    ├── AppEntry.swift                     # [NEW] App 入口，标注 @main，导入 AIParenting library 并实例化 AIParentingApp。仅 3-5 行代码
    ├── Info.plist                         # [NEW] App 配置文件。配置 NSAppTransportSecurity 允许 127.0.0.1 的 HTTP 明文请求（NSExceptionDomains）
    ├── DevApp.entitlements                # [NEW] Sandbox 权限配置。启用 com.apple.security.network.client（出站网络连接）
    └── project.yml                        # [NEW] XcodeGen 项目描述文件。定义 App target（iOS 17）、本地 Package 依赖、签名配置。用于生成 DevApp.xcodeproj
```

## 关键代码结构

```swift
// DevApp/AppEntry.swift — App 入口（仅此一个业务文件）
import AIParenting
import SwiftUI

@main
struct AppEntry: App {
    var body: some Scene {
        AIParentingApp().body
    }
}
```