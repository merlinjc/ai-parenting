import SwiftUI

/// 渠道管理页
///
/// 展示已绑定的渠道列表（可拖拽排序优先级）、绑定新渠道入口、各渠道状态指示器。
/// Phase 6 升级：渠道连接状态实时指示、最近消息预览、Gateway 在线检测。
/// 从 ProfileView 的"消息渠道"入口进入。
public struct ChannelManageView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var bindings: [ChannelBindingResponse] = []
    @State private var isLoading = true
    @State private var showWeChatBind = false
    @State private var error: String?
    @State private var gatewayOnline = false
    @State private var showUnbindAlert = false
    @State private var bindingToUnbind: ChannelBindingResponse?

    public init() {}

    public var body: some View {
        List {
            // 渠道连接状态概览
            if !bindings.isEmpty {
                Section {
                    channelStatusOverview
                }
            }

            // 已绑定渠道
            Section("已绑定渠道") {
                if bindings.isEmpty && !isLoading {
                    emptyBindingsView
                } else if isLoading {
                    HStack {
                        Spacer()
                        ProgressView()
                            .padding(.vertical, 16)
                        Spacer()
                    }
                } else {
                    ForEach(bindings) { binding in
                        channelRow(binding)
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    bindingToUnbind = binding
                                    showUnbindAlert = true
                                } label: {
                                    Label("解绑", systemImage: "minus.circle")
                                }
                            }
                    }
                    .onMove { from, to in
                        bindings.move(fromOffsets: from, toOffset: to)
                        Task { await updatePriority() }
                    }
                }
            }

            // 添加渠道
            Section("添加渠道") {
                // 微信
                if !bindings.contains(where: { $0.channel == "wechat" }) {
                    Button {
                        showWeChatBind = true
                    } label: {
                        addChannelLabel(
                            icon: "message.fill",
                            color: .green,
                            name: "绑定微信",
                            desc: "扫码关注服务号，接收推送消息"
                        )
                    }
                }

                // WhatsApp — 根据 Gateway 状态动态显示
                if !bindings.contains(where: { $0.channel == "openclaw_whatsapp" }) {
                    if gatewayOnline {
                        Button {
                            // TODO: WhatsApp 绑定流程（输入手机号 → Gateway 发送验证码）
                        } label: {
                            addChannelLabel(
                                icon: "phone.fill",
                                color: .green,
                                name: "WhatsApp",
                                desc: "通过 WhatsApp 接收消息和回复"
                            )
                        }
                    } else {
                        addChannelLabel(
                            icon: "phone.fill",
                            color: .gray.opacity(0.4),
                            name: "WhatsApp",
                            desc: "消息网关离线，暂不可用"
                        )
                        .foregroundStyle(.tertiary)
                    }
                }

                // Telegram — 同样根据 Gateway 状态
                if !bindings.contains(where: { $0.channel == "openclaw_telegram" }) {
                    if gatewayOnline {
                        Button {
                            // TODO: Telegram 绑定流程（跳转 Bot 链接）
                        } label: {
                            addChannelLabel(
                                icon: "paperplane.fill",
                                color: .blue,
                                name: "Telegram",
                                desc: "通过 Telegram Bot 接收消息和回复"
                            )
                        }
                    } else {
                        addChannelLabel(
                            icon: "paperplane.fill",
                            color: .gray.opacity(0.4),
                            name: "Telegram",
                            desc: "消息网关离线，暂不可用"
                        )
                        .foregroundStyle(.tertiary)
                    }
                }
            }

            // 推送偏好
            Section("推送偏好") {
                HStack {
                    Image(systemName: "hand.draw")
                        .foregroundStyle(.secondary)
                    Text("拖拽上方已绑定渠道可调整优先级")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                NavigationLink {
                    Text("静默时段设置（开发中）")
                } label: {
                    Label("静默时段", systemImage: "moon.fill")
                }
            }

            // 网关状态
            Section("系统状态") {
                HStack {
                    Image(systemName: gatewayOnline ? "wifi" : "wifi.slash")
                        .foregroundStyle(gatewayOnline ? .green : .red)
                    Text("OpenClaw 消息网关")
                    Spacer()
                    Text(gatewayOnline ? "在线" : "离线")
                        .font(.caption)
                        .foregroundStyle(gatewayOnline ? .green : .red)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(
                            Capsule()
                                .fill(gatewayOnline ? .green.opacity(0.1) : .red.opacity(0.1))
                        )
                }
            }
        }
        .navigationTitle("消息渠道")
        .toolbar {
            EditButton()
        }
        .refreshable {
            await loadBindings()
            await checkGatewayStatus()
        }
        .sheet(isPresented: $showWeChatBind) {
            WeChatBindView()
        }
        .alert("确认解绑", isPresented: $showUnbindAlert, presenting: bindingToUnbind) { binding in
            Button("解绑", role: .destructive) {
                Task { await unbindChannel(binding) }
            }
            Button("取消", role: .cancel) {}
        } message: { binding in
            let channelType = ChannelType(rawValue: binding.channel)
            Text("确认解绑 \(channelType?.displayName ?? binding.channel)？解绑后将无法通过该渠道接收消息。")
        }
        .task {
            await loadBindings()
            await checkGatewayStatus()
        }
    }

    // MARK: - Channel Status Overview

    private var channelStatusOverview: some View {
        let activeCount = bindings.filter(\.isActive).count
        let totalCount = bindings.count

        return HStack(spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text("\(activeCount)/\(totalCount)")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundStyle(.primary)
                Text("活跃渠道")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            // 渠道图标集
            HStack(spacing: -6) {
                ForEach(bindings.prefix(4)) { binding in
                    let channelType = ChannelType(rawValue: binding.channel)
                    Image(systemName: channelType?.iconName ?? "questionmark.circle")
                        .font(.caption)
                        .foregroundStyle(.white)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle().fill(binding.isActive ? .blue : .gray)
                        )
                }
            }
        }
        .padding(.vertical, 4)
    }

    // MARK: - Empty State

    private var emptyBindingsView: some View {
        HStack {
            Spacer()
            VStack(spacing: 8) {
                Image(systemName: "antenna.radiowaves.left.and.right.slash")
                    .font(.title2)
                    .foregroundStyle(.secondary)
                Text("暂未绑定任何渠道")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text("绑定渠道后可通过微信、WhatsApp 等接收 AI 育儿助手消息")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .multilineTextAlignment(.center)
            }
            Spacer()
        }
        .padding(.vertical, 16)
    }

    // MARK: - Channel Row

    private func channelRow(_ binding: ChannelBindingResponse) -> some View {
        let channelType = ChannelType(rawValue: binding.channel)
        return HStack(spacing: 12) {
            // 渠道图标 + 状态环
            ZStack(alignment: .bottomTrailing) {
                Image(systemName: channelType?.iconName ?? "questionmark.circle")
                    .font(.title3)
                    .foregroundStyle(binding.isActive ? .blue : .gray)
                    .frame(width: 36, height: 36)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(binding.isActive ? .blue.opacity(0.1) : .gray.opacity(0.1))
                    )

                // 在线/离线小圆点
                Circle()
                    .fill(binding.isActive ? .green : .gray.opacity(0.5))
                    .frame(width: 10, height: 10)
                    .overlay(
                        Circle().stroke(.white, lineWidth: 2)
                    )
                    .offset(x: 2, y: 2)
            }

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text(channelType?.displayName ?? binding.channel)
                        .fontWeight(.medium)
                    if binding.channel.hasPrefix("openclaw_") {
                        Text("via Gateway")
                            .font(.caption2)
                            .foregroundStyle(.blue)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 1)
                            .background(
                                Capsule().fill(.blue.opacity(0.1))
                            )
                    }
                }
                if let label = binding.displayLabel {
                    Text(label)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    Text(maskedChannelUserId(binding.channelUserId))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            // 绑定时间
            VStack(alignment: .trailing, spacing: 2) {
                Text(binding.isActive ? "已绑定" : "已暂停")
                    .font(.caption)
                    .foregroundStyle(binding.isActive ? .green : .secondary)
                Text(relativeTimeText(binding.createdAt))
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
        }
    }

    // MARK: - Add Channel Label

    private func addChannelLabel(icon: String, color: Color, name: String, desc: String) -> some View {
        Label {
            VStack(alignment: .leading, spacing: 2) {
                Text(name)
                    .fontWeight(.medium)
                Text(desc)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        } icon: {
            Image(systemName: icon)
                .foregroundStyle(color)
        }
    }

    // MARK: - Helpers

    private func maskedChannelUserId(_ id: String) -> String {
        guard id.count > 6 else { return id }
        let prefix = String(id.prefix(3))
        let suffix = String(id.suffix(3))
        return "\(prefix)***\(suffix)"
    }

    private func relativeTimeText(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    // MARK: - Actions

    @MainActor
    private func loadBindings() async {
        isLoading = true
        do {
            let response: ChannelBindingListResponse = try await apiClient.request(.listChannelBindings)
            bindings = response.bindings
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }

    @MainActor
    private func updatePriority() async {
        let priority = bindings.map(\.channel)
        let originalBindings = bindings
        let update = ChannelPreferenceUpdate(channelPriority: priority)
        do {
            let _: ChannelPreferenceResponse = try await apiClient.request(.updateChannelPreferences(update))
        } catch {
            // 保存失败：恢复原始顺序并提示用户
            bindings = originalBindings
            self.error = "优先级保存失败：\(error.localizedDescription)"
        }
    }

    @MainActor
    private func unbindChannel(_ binding: ChannelBindingResponse) async {
        do {
            try await apiClient.requestVoid(.unbindChannel(binding.id))
            bindings.removeAll { $0.id == binding.id }
        } catch {
            self.error = "解绑失败：\(error.localizedDescription)"
        }
    }

    @MainActor
    private func checkGatewayStatus() async {
        // 通过尝试获取技能列表间接判断后端是否在线
        // Gateway 状态可通过后端 /health 端点的 channels 字段获取
        do {
            let _: HealthResponse = try await apiClient.request(.health)
            gatewayOnline = true
        } catch {
            gatewayOnline = false
        }
    }
}

// MARK: - Health Response

/// 后端健康检查响应（用于检测 Gateway 状态）
/// 使用 Common.swift 中的公共 HealthResponse
