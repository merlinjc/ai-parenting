import SwiftUI

/// 底部 TabView 导航（首页/计划/记录/消息四个标签）
///
/// 从 AppState 获取当前活跃的 childId，支持 DeepLinkTarget 跨 Tab 导航。
/// 即时求助浮动按钮在所有 Tab 可见。
public struct MainTabView: View {

    @Environment(AppState.self) private var appState
    @Environment(APIClient.self) private var apiClient
    @State private var selectedTab = 0
    @State private var showInstantHelp = false
    @State private var showRecordCreate = false
    @State private var showVoiceOverlay = false

    // 浮动按钮菜单
    @State private var showFABMenu = false

    // 跨 Tab 导航携带的参数
    @State private var recordSourcePlanId: UUID?
    @State private var recordSourceSessionId: UUID?
    @State private var recordPrefillTheme: String?
    @State private var instantHelpPlanId: UUID?

    // Toast 反馈
    @State private var toastMessage: String?
    @State private var showToast = false

    public init() {}

    public var body: some View {
        if let childId = appState.activeChildId {
            ZStack(alignment: .bottomTrailing) {
                TabView(selection: $selectedTab) {
                    HomeView(childId: childId)
                        .id(childId)
                        .tabItem {
                            Label("首页", systemImage: "house.fill")
                        }
                        .tag(0)

                    PlanDetailView(childId: childId)
                        .id(childId)
                        .tabItem {
                            Label("计划", systemImage: "calendar")
                        }
                        .tag(1)

                    RecordListView(childId: childId)
                        .id(childId)
                        .tabItem {
                            Label("记录", systemImage: "square.and.pencil")
                        }
                        .tag(2)

                    MessageListView()
                        .tabItem {
                            Label("消息", systemImage: "bell.fill")
                        }
                        .badge(appState.unreadMessageCount)
                        .tag(3)
                }

                // 浮动操作按钮（点击即时求助 / 长按展开菜单）
                VStack(spacing: 10) {
                    // 展开的菜单项（从下到上动画展开）
                    if showFABMenu {
                        VStack(spacing: 8) {
                            fabMenuItem(
                                icon: "mic.circle.fill",
                                label: "语音求助",
                                gradient: [.purple, .pink]
                            ) {
                                showFABMenu = false
                                showVoiceOverlay = true
                            }

                            fabMenuItem(
                                icon: "waveform.circle.fill",
                                label: "语音记录",
                                gradient: [.green, .mint]
                            ) {
                                showFABMenu = false
                                recordSourcePlanId = nil
                                recordSourceSessionId = nil
                                recordPrefillTheme = nil
                                showRecordCreate = true
                            }

                            fabMenuItem(
                                icon: "text.bubble.fill",
                                label: "文字求助",
                                gradient: [Color.appPrimary, Color.appSecondary]
                            ) {
                                showFABMenu = false
                                instantHelpPlanId = nil
                                showInstantHelp = true
                            }
                        }
                        .transition(.asymmetric(
                            insertion: .scale(scale: 0.5, anchor: .bottom).combined(with: .opacity),
                            removal: .scale(scale: 0.8, anchor: .bottom).combined(with: .opacity)
                        ))
                    }

                    // 主浮动按钮
                    Button {
                        if showFABMenu {
                            // 菜单已展开时，点击关闭菜单
                            withAnimation(.spring(response: 0.35, dampingFraction: 0.7)) {
                                showFABMenu = false
                            }
                        } else {
                            // 菜单未展开时，直接打开即时求助
                            instantHelpPlanId = nil
                            showInstantHelp = true
                        }
                    } label: {
                        Image(systemName: showFABMenu ? "xmark" : "questionmark.circle.fill")
                            .font(.system(size: 24))
                            .foregroundStyle(.white)
                            .frame(width: 56, height: 56)
                            .background(
                                LinearGradient(
                                    colors: showFABMenu ? [.gray, .gray.opacity(0.8)] : [Color.appPrimary, Color.appSecondary],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .clipShape(Circle())
                            .shadow(color: Color.appPrimary.opacity(0.4), radius: 8, y: 4)
                    }
                    .simultaneousGesture(
                        LongPressGesture(minimumDuration: 0.4)
                            .onEnded { _ in
                                if !showFABMenu {
                                    withAnimation(.spring(response: 0.35, dampingFraction: 0.7)) {
                                        showFABMenu = true
                                    }
                                }
                            }
                    )
                }
                .padding(.trailing, 20)
                .padding(.bottom, 80)
            }
            .sheet(isPresented: $showInstantHelp) {
                InstantHelpView(
                    childId: childId,
                    planId: instantHelpPlanId,
                    onRecordFromResult: { sessionId in
                        showInstantHelp = false
                        // 延迟到 sheet dismiss 完成后再打开记录
                        Task { @MainActor in
                            try? await Task.sleep(nanoseconds: 300_000_000)
                            recordSourceSessionId = sessionId
                            recordSourcePlanId = nil
                            appState.navigate(to: .recordCreate(sourcePlanId: nil, sourceSessionId: sessionId, theme: nil))
                        }
                    },
                    onAddToFocus: { focusPlanId, scenarioSummary in
                        showInstantHelp = false
                        // 调用「加入本周关注」API
                        Task {
                            await addToWeeklyFocus(
                                planId: focusPlanId,
                                childId: childId,
                                scenarioSummary: scenarioSummary
                            )
                        }
                    }
                )
            }
            .sheet(isPresented: $showRecordCreate) {
                RecordCreateView(
                    childId: childId,
                    viewModel: RecordViewModel(apiClient: appState.apiClientRef, childId: childId),
                    onDismiss: { showRecordCreate = false },
                    sourcePlanId: recordSourcePlanId,
                    sourceSessionId: recordSourceSessionId,
                    prefillTheme: recordPrefillTheme
                )
            }
            .sheet(isPresented: $showVoiceOverlay) {
                VoiceOverlayView(childId: childId)
                    .presentationDetents([.medium])
                    .presentationDragIndicator(.visible)
            }
            .onChange(of: appState.pendingNavigation) { _, newValue in
                guard let target = newValue else { return }
                handleDeepLink(target, childId: childId)
                appState.consumeNavigation()
            }
            .overlay(alignment: .top) {
                if showToast, let message = toastMessage {
                    Text(message)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 10)
                        .background(
                            Capsule()
                                .fill(.ultraThinMaterial)
                                .shadow(color: .black.opacity(0.1), radius: 8, y: 4)
                        )
                        .transition(.move(edge: .top).combined(with: .opacity))
                        .padding(.top, 8)
                }
            }
            .animation(.easeInOut(duration: 0.3), value: showToast)
        } else {
            // 无活跃儿童
            EmptyStateView(
                icon: "person.crop.circle.badge.plus",
                title: "还没有儿童档案",
                description: "请先添加一个儿童档案以开始使用"
            )
        }
    }

    // MARK: - FAB Menu Item

    private func fabMenuItem(icon: String, label: String, gradient: [Color], action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Text(label)
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(.primary)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(
                        Capsule()
                            .fill(.ultraThinMaterial)
                            .shadow(color: .black.opacity(0.08), radius: 4, y: 2)
                    )

                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundStyle(.white)
                    .frame(width: 40, height: 40)
                    .background(
                        LinearGradient(colors: gradient, startPoint: .topLeading, endPoint: .bottomTrailing)
                    )
                    .clipShape(Circle())
                    .shadow(color: gradient.first?.opacity(0.3) ?? .clear, radius: 4, y: 2)
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Deep Link Handler

    private func handleDeepLink(_ target: DeepLinkTarget, childId: UUID) {
        switch target {
        case .planDetail:
            selectedTab = 1

        case .recordCreate(let sourcePlanId, let sourceSessionId, let theme):
            recordSourcePlanId = sourcePlanId
            recordSourceSessionId = sourceSessionId
            recordPrefillTheme = theme
            selectedTab = 2
            // 短暂延迟确保 Tab 切换完成后弹出 sheet
            Task { @MainActor in
                try? await Task.sleep(nanoseconds: 200_000_000)
                showRecordCreate = true
            }

        case .recordList:
            selectedTab = 2

        case .messageList:
            selectedTab = 3

        case .weeklyFeedback:
            // 切到计划 Tab（周反馈从计划页入口进入）
            selectedTab = 1

        case .instantHelp(let planId):
            instantHelpPlanId = planId
            showInstantHelp = true
        }
    }

    // MARK: - Add to Weekly Focus

    /// 调用「加入本周关注」API，将即时求助场景摘要追加到活跃计划
    private func addToWeeklyFocus(planId: UUID?, childId: UUID, scenarioSummary: String) async {
        // 如果没有传入 planId，尝试获取活跃计划
        var targetPlanId = planId
        if targetPlanId == nil {
            do {
                let planWithFeedback: PlanWithFeedbackStatus = try await apiClient.request(.getActivePlan(childId: childId))
                targetPlanId = planWithFeedback.plan.id
            } catch {
                showToastMessage("未找到活跃计划")
                return
            }
        }

        guard let finalPlanId = targetPlanId else {
            showToastMessage("未找到活跃计划")
            return
        }

        do {
            let update = PlanFocusNoteUpdate(note: scenarioSummary)
            let _: PlanResponse = try await apiClient.request(.appendFocusNote(planId: finalPlanId, update))
            showToastMessage("已加入本周关注 ✓")
        } catch {
            showToastMessage("加入关注失败，请稍后重试")
        }
    }

    @MainActor
    private func showToastMessage(_ message: String) {
        toastMessage = message
        showToast = true
        Task { @MainActor in
            try? await Task.sleep(nanoseconds: 2_500_000_000)
            showToast = false
        }
    }
}
