import SwiftUI

/// 用户个人中心页面
///
/// 展示用户基本信息、儿童管理入口、设置入口。
/// 对应低保真原型中首页右上角 "ME" 图标的目标页。
public struct ProfileView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(AppState.self) private var appState
    @Environment(\.dismiss) private var dismiss

    @State private var isEditing = false
    @State private var editDisplayName = ""
    @State private var editCaregiverRole = ""
    @State private var isSubmitting = false
    @State private var saveErrorMessage: String?

    public init() {}

    @State private var showLogoutConfirm = false

    public var body: some View {
        NavigationStack {
            List {
                // 用户信息区
                userInfoSection

                // 儿童管理
                childrenSection

                // 设置
                settingsSection

                // 关于
                aboutSection

                // 账号操作
                accountSection
            }
            .navigationTitle("我的")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("关闭") { dismiss() }
                }
            }
            .sheet(isPresented: $isEditing) {
                profileEditSheet
            }
            .alert("确认退出", isPresented: $showLogoutConfirm) {
                Button("取消", role: .cancel) {}
                Button("退出登录", role: .destructive) {
                    dismiss()
                    // 延迟执行让 sheet 关闭动画完成
                    Task { @MainActor in
                        try? await Task.sleep(nanoseconds: 300_000_000)
                        appState.logout()
                    }
                }
            } message: {
                Text("退出登录后需要重新输入账号密码")
            }
        }
    }

    // MARK: - User Info Section

    private var userInfoSection: some View {
        Section {
            HStack(spacing: 14) {
                // 头像占位
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [Color.appPrimary, Color.appSecondary],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 56, height: 56)

                    Text(avatarText)
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundStyle(.white)
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(appState.userProfile?.displayName ?? "未设置昵称")
                        .font(.title3)
                        .fontWeight(.semibold)

                    if let role = appState.userProfile?.caregiverRole {
                        Text(roleDisplayName(role))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                Button {
                    editDisplayName = appState.userProfile?.displayName ?? ""
                    let role = appState.userProfile?.caregiverRole ?? ""
                    let validRoles: Set<String> = ["mother", "father", "grandparent", "other"]
                    editCaregiverRole = validRoles.contains(role) ? role : ""
                    isEditing = true
                } label: {
                    Text("编辑")
                        .font(.subheadline)
                }
            }
            .padding(.vertical, 4)
        }
    }

    // MARK: - Children Section

    private var childrenSection: some View {
        Section("儿童档案") {
            ForEach(appState.children) { child in
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        HStack {
                            Text(child.nickname)
                                .fontWeight(.medium)
                            if child.id == appState.activeChildId {
                                Text("当前")
                                    .font(.caption2)
                                    .foregroundStyle(.white)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 1)
                                    .background(Color.appPrimary)
                                    .clipShape(Capsule())
                            }
                        }
                        Text("\(child.ageMonths)个月 · \(child.stage)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    if child.id != appState.activeChildId {
                        Button("切换") {
                            appState.setActiveChild(child)
                        }
                        .font(.caption)
                        .buttonStyle(.bordered)
                    }
                }
            }

            NavigationLink {
                ChildListView()
            } label: {
                Label("管理儿童档案", systemImage: "person.crop.circle.badge.plus")
            }
        }
    }

    // MARK: - Settings Section

    private var settingsSection: some View {
        Section("设置") {
            NavigationLink {
                ChannelManageView()
            } label: {
                Label("消息渠道", systemImage: "paperplane")
            }

            NavigationLink {
                SkillListView()
            } label: {
                Label("AI 能力", systemImage: "cpu")
            }

            HStack {
                Label("推送通知", systemImage: "bell.badge")
                Spacer()
                Text(appState.userProfile?.pushEnabled == true ? "已开启" : "已关闭")
                    .foregroundStyle(.secondary)
            }

            HStack {
                Label("时区", systemImage: "clock")
                Spacer()
                Text(appState.userProfile?.timezone ?? "Asia/Shanghai")
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - About Section

    private var aboutSection: some View {
        Section("关于") {
            HStack {
                Text("版本")
                Spacer()
                Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0.0")
                    .foregroundStyle(.secondary)
            }
            HStack {
                Text("构建号")
                Spacer()
                Text(Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1")
                    .foregroundStyle(.secondary)
            }
        }
    }

    // MARK: - Account Section

    private var accountSection: some View {
        Section {
            Button(role: .destructive) {
                showLogoutConfirm = true
            } label: {
                HStack {
                    Spacer()
                    Label("退出登录", systemImage: "rectangle.portrait.and.arrow.right")
                    Spacer()
                }
            }
        }
    }

    // MARK: - Profile Edit Sheet

    private var profileEditSheet: some View {
        NavigationStack {
            Form {
                Section("基本信息") {
                    TextField("显示名称", text: $editDisplayName)

                    Picker("照护角色", selection: $editCaregiverRole) {
                        Text("未选择").tag("")
                        Text("妈妈").tag("mother")
                        Text("爸爸").tag("father")
                        Text("祖辈").tag("grandparent")
                        Text("其他照护者").tag("other")
                    }
                }

                if let saveErrorMessage {
                    Section {
                        Text(saveErrorMessage)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("编辑资料")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { isEditing = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task { await saveProfile() }
                    } label: {
                        if isSubmitting {
                            ProgressView()
                        } else {
                            Text("保存")
                        }
                    }
                    .disabled(isSubmitting)
                }
            }
        }
    }

    // MARK: - Actions

    @MainActor
    private func saveProfile() async {
        isSubmitting = true
        saveErrorMessage = nil
        let update = UserProfileUpdate(
            displayName: editDisplayName.isEmpty ? nil : editDisplayName,
            caregiverRole: editCaregiverRole.isEmpty ? nil : editCaregiverRole
        )

        do {
            let _: UserProfileResponse = try await apiClient.request(.updateProfile(update))
            await appState.refreshProfile()
            isEditing = false
        } catch {
            saveErrorMessage = "保存失败：\(error.localizedDescription)"
        }
        isSubmitting = false
    }

    // MARK: - Helpers

    private var avatarText: String {
        if let name = appState.userProfile?.displayName, !name.isEmpty {
            return String(name.prefix(1))
        }
        return "U"
    }

    private func roleDisplayName(_ role: String) -> String {
        switch role {
        case "mother": return "妈妈"
        case "father": return "爸爸"
        case "grandparent": return "祖辈"
        case "other": return "其他照护者"
        default: return role
        }
    }
}
