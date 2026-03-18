import SwiftUI

/// 首页视图
///
/// 问候语 → 周焦点主卡（阶段+主题+风险+一句话建议+连续打卡+7 天进度）→
/// 待处理回流摘要 → 周反馈横幅 → 今日任务双栏+行动按钮 →
/// 最近记录 → AI 即时求助入口卡片。
/// 无活跃计划时展示空状态引导卡片。
public struct HomeView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(AppState.self) private var appState
    @State private var viewModel: HomeViewModel?
    @State private var showProfile = false
    @State private var showInstantHelp = false
    public let childId: UUID

    public init(childId: UUID) {
        self.childId = childId
    }

    public var body: some View {
        NavigationStack {
            Group {
                if let vm = viewModel {
                    homeContent(vm)
                } else {
                    ProgressView("加载中...")
                }
            }
            .navigationTitle("首页")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showProfile = true
                    } label: {
                        Image(systemName: "person.circle")
                            .font(.title3)
                    }
                }
            }
            .sheet(isPresented: $showProfile) {
                ProfileView()
            }
            .sheet(isPresented: $showInstantHelp) {
                InstantHelpView(
                    childId: childId,
                    planId: viewModel?.activePlan?.id
                )
            }
            .task {
                if viewModel == nil {
                    let vm = HomeViewModel(apiClient: apiClient, childId: childId)
                    viewModel = vm
                    await vm.loadSummary()
                }
            }
        }
    }

    @ViewBuilder
    private func homeContent(_ vm: HomeViewModel) -> some View {
        if vm.isLoading && vm.summary == nil {
            // 骨架屏加载态
            ScrollView {
                VStack(spacing: 16) {
                    // 问候语骨架
                    HStack {
                        VStack(alignment: .leading, spacing: 8) {
                            RoundedRectangle(cornerRadius: 4)
                                .fill(.gray.opacity(0.15))
                                .frame(width: 180, height: 24)
                            RoundedRectangle(cornerRadius: 4)
                                .fill(.gray.opacity(0.1))
                                .frame(width: 120, height: 16)
                        }
                        Spacer()
                    }
                    .shimmer()

                    // 周焦点骨架
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            RoundedRectangle(cornerRadius: 4).fill(.gray.opacity(0.15)).frame(width: 80, height: 28)
                            Spacer()
                        }
                        RoundedRectangle(cornerRadius: 4).fill(.gray.opacity(0.1)).frame(height: 16)
                        RoundedRectangle(cornerRadius: 4).fill(.gray.opacity(0.08)).frame(width: 200, height: 14)
                        HStack(spacing: 8) {
                            ForEach(0..<7, id: \.self) { _ in
                                Circle().fill(.gray.opacity(0.1)).frame(width: 28, height: 28)
                            }
                        }
                    }
                    .padding()
                    .background(RoundedRectangle(cornerRadius: 16).fill(.background).shadow(color: .black.opacity(0.03), radius: 8, y: 4))
                    .shimmer()

                    // 今日任务骨架
                    VStack(spacing: 12) {
                        HStack {
                            RoundedRectangle(cornerRadius: 4).fill(.gray.opacity(0.15)).frame(width: 80, height: 20)
                            Spacer()
                        }
                        HStack(spacing: 12) {
                            RoundedRectangle(cornerRadius: 10).fill(.gray.opacity(0.08)).frame(height: 80)
                            RoundedRectangle(cornerRadius: 10).fill(.gray.opacity(0.08)).frame(height: 80)
                        }
                        RoundedRectangle(cornerRadius: 12).fill(.gray.opacity(0.1)).frame(height: 44)
                    }
                    .padding()
                    .background(RoundedRectangle(cornerRadius: 16).fill(.blue.opacity(0.03)))
                    .shimmer()
                }
                .padding()
            }
        } else if let error = vm.error, vm.summary == nil {
            VStack(spacing: 16) {
                Image(systemName: "wifi.slash")
                    .font(.system(size: 48))
                    .foregroundStyle(.secondary)
                Text(error.localizedDescription)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Button("重试") {
                    Task { await vm.refresh() }
                }
                .buttonStyle(.borderedProminent)
            }
            .padding()
        } else {
            ScrollView {
                VStack(spacing: 16) {
                    // 1. 问候语区域
                    if !vm.greeting.isEmpty {
                        greetingSection(vm)
                    }

                    // 2. 周焦点主卡（含连续打卡 + 7 天进度可视化）
                    if let child = vm.child {
                        if vm.activePlan != nil {
                            weekFocusCard(child: child, plan: vm.activePlan, vm: vm)
                        } else if vm.planGenerating {
                            planGeneratingCard(child: child)
                        } else {
                            emptyPlanGuideCard(child: child)
                        }
                    }

                    // 3. 今日任务（提权到第 2 位，紧接周焦点之后）
                    if let task = vm.todayTask {
                        todayTaskCard(task, plan: vm.activePlan, vm: vm)
                    }

                    // 4. 通知条区域（合并回流摘要 + 周反馈为横滑通知条）
                    if vm.hasPendingReturnFlow || vm.hasWeeklyFeedbackReady {
                        notificationBannerStrip(vm)
                    }

                    // 5. 最近记录（单条预览 + 查看更多）
                    if !vm.recentRecords.isEmpty {
                        recentRecordPreview(vm.recentRecords)
                    }

                    // AI 入口已移至浮动按钮，首页不再重复展示
                }
                .padding()
            }
            .refreshable {
                await vm.refresh()
            }
        }
    }

    // MARK: - 1. Greeting Section

    private func greetingSection(_ vm: HomeViewModel) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(vm.greeting)
                    .font(.title3)
                    .fontWeight(.semibold)
                    .foregroundStyle(.primary)

                if vm.streakDays > 0 {
                    HStack(spacing: 4) {
                        Image(systemName: "flame.fill")
                            .font(.caption)
                            .foregroundStyle(.orange)
                        Text("已连续坚持 \(vm.streakDays) 天")
                            .font(.caption)
                            .fontWeight(.medium)
                            .foregroundStyle(.orange)
                    }
                }
            }

            Spacer()

            // 消息角标（点击跳转消息 Tab）
            if let vm2 = viewModel {
                Button {
                    appState.navigate(to: .messageList)
                } label: {
                    ZStack(alignment: .topTrailing) {
                        Image(systemName: "bell.fill")
                            .font(.title3)
                            .foregroundStyle(.secondary)

                        if vm2.unreadCount > 0 {
                            Text(vm2.unreadCount > 99 ? "99+" : "\(vm2.unreadCount)")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(.white)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.red)
                                .clipShape(Capsule())
                                .offset(x: 8, y: -8)
                        }
                    }
                }
            }
        }
        .padding(.bottom, 4)
    }

    // MARK: - Week Focus Card

    private func weekFocusCard(child: ChildResponse, plan: PlanResponse?, vm: HomeViewModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // 头部：昵称 + 月龄
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(child.nickname)
                        .font(.title2)
                        .fontWeight(.bold)

                    HStack(spacing: 8) {
                        Text("\(child.ageMonths)个月")
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(Color.blue.opacity(0.1))
                            .foregroundStyle(.blue)
                            .clipShape(Capsule())

                        if let stageName = vm.stageDisplayName {
                            Text(stageName)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Spacer()
            }

            // 计划信息区（阶段+主题+风险+目标）
            if let plan = plan {
                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    // 本周主题
                    HStack(spacing: 6) {
                        Image(systemName: "target")
                            .font(.caption)
                            .foregroundStyle(.blue)
                        Text("本周主题：")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(FocusTheme(rawValue: plan.focusTheme)?.displayName ?? plan.focusTheme)
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundStyle(.blue)
                    }

                    // 一句话目标
                    Text(plan.primaryGoal)
                        .font(.subheadline)
                        .foregroundStyle(.primary)
                        .lineLimit(2)

                    // 风险标签 + 完成率
                    HStack(spacing: 12) {
                        if let risk = vm.riskLevel, risk != .normal {
                            HStack(spacing: 4) {
                                Image(systemName: risk == .consult ? "exclamationmark.triangle.fill" : "eye.fill")
                                    .font(.caption2)
                                Text(risk.displayName)
                                    .font(.caption)
                                    .fontWeight(.medium)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(
                                Capsule()
                                    .fill(risk == .consult ? .red.opacity(0.12) : .orange.opacity(0.12))
                            )
                            .foregroundStyle(risk == .consult ? .red : .orange)
                        }

                        HStack(spacing: 4) {
                            Image(systemName: "chart.line.uptrend.xyaxis")
                                .font(.caption2)
                            Text("完成率 \(Int(plan.completionRate * 100))%")
                                .font(.caption)
                        }
                        .foregroundStyle(.secondary)

                        Text("第\(plan.currentDay)/7天")
                            .font(.caption)
                            .foregroundStyle(.tertiary)
                    }

                    // 6. 本周 7 天进度可视化
                    if !vm.weekDayStatuses.isEmpty {
                        weekProgressBar(statuses: vm.weekDayStatuses, currentDay: plan.currentDay)
                    }
                }
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
    }

    // MARK: - 6. Week Progress Bar (7 Dots)

    private func weekProgressBar(statuses: [String], currentDay: Int) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 0) {
                ForEach(0..<min(statuses.count, 7), id: \.self) { index in
                    let status = statuses[index]
                    let dayNum = index + 1
                    let isCurrent = dayNum == currentDay

                    VStack(spacing: 4) {
                        ZStack {
                            Circle()
                                .fill(progressDotColor(for: status))
                                .frame(width: isCurrent ? 28 : 22, height: isCurrent ? 28 : 22)

                            if status == "executed" {
                                Image(systemName: "checkmark")
                                    .font(.system(size: isCurrent ? 12 : 10, weight: .bold))
                                    .foregroundStyle(.white)
                            } else if status == "partial" || status == "needs_record" {
                                Circle()
                                    .fill(.white)
                                    .frame(width: isCurrent ? 8 : 6, height: isCurrent ? 8 : 6)
                            }

                            if isCurrent && status == "pending" {
                                Circle()
                                    .strokeBorder(.blue, lineWidth: 2)
                                    .frame(width: 28, height: 28)
                            }
                        }

                        Text(weekdayLabel(for: dayNum))
                            .font(.system(size: 10))
                            .foregroundStyle(isCurrent ? .primary : .tertiary)
                    }
                    .frame(maxWidth: .infinity)
                }
            }
        }
        .padding(.top, 4)
    }

    private func progressDotColor(for status: String) -> Color {
        switch status {
        case "executed": .green
        case "partial": .orange.opacity(0.7)
        case "needs_record": .purple.opacity(0.6)
        case "pending": .gray.opacity(0.2)
        default: .gray.opacity(0.1) // future
        }
    }

    private func weekdayLabel(for dayNumber: Int) -> String {
        let labels = ["一", "二", "三", "四", "五", "六", "日"]
        let index = (dayNumber - 1) % 7
        return labels[index]
    }

    // MARK: - 5a. Plan Generating Card

    private func planGeneratingCard(child: ChildResponse) -> some View {
        VStack(spacing: 16) {
            // 动画脉冲效果
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [.blue.opacity(0.1), .purple.opacity(0.1)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 72, height: 72)

                Image(systemName: "sparkles")
                    .font(.system(size: 32))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .symbolEffect(.pulse, options: .repeating)
            }

            VStack(spacing: 6) {
                Text("正在为\(child.nickname)生成专属计划")
                    .font(.headline)
                    .fontWeight(.semibold)

                Text("AI 正在根据您的信息设计 7 天微计划，预计 30 秒内完成")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            ProgressView()
                .tint(.blue)
                .scaleEffect(1.2)
                .padding(.vertical, 4)

            Text("完成后将自动刷新")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(
                    LinearGradient(
                        colors: [.blue.opacity(0.04), .purple.opacity(0.04)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(
                            LinearGradient(
                                colors: [.blue.opacity(0.15), .purple.opacity(0.15)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 1
                        )
                )
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
        .task {
            // 自动轮询：每 5 秒刷新一次，直到计划出现
            while viewModel?.activePlan == nil {
                try? await Task.sleep(for: .seconds(5))
                await viewModel?.refresh()
            }
        }
    }

    // MARK: - 5. Empty Plan Guide Card

    private func emptyPlanGuideCard(child: ChildResponse) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "sparkles")
                .font(.system(size: 40))
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            VStack(spacing: 6) {
                Text("还没有训练计划")
                    .font(.headline)
                    .fontWeight(.semibold)

                Text("3 分钟完成评估，为\(child.nickname)生成专属训练计划")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }

            if child.onboardingCompleted {
                NavigationLink {
                    PlanDetailView(childId: childId)
                } label: {
                    Text("创建训练计划")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(
                                    LinearGradient(
                                        colors: [.blue, .blue.opacity(0.8)],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                        )
                }
            } else {
                NavigationLink {
                    OnboardingView()
                } label: {
                    Text("开始评估")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(
                                    LinearGradient(
                                        colors: [.purple, .blue],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                        )
                }
            }
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
    }

    // MARK: - Notification Banner Strip（合并回流 + 周反馈为横滑通知条）

    private func notificationBannerStrip(_ vm: HomeViewModel) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 10) {
                // 周反馈通知
                if vm.hasWeeklyFeedbackReady {
                    NavigationLink {
                        FeedbackView(
                            feedbackId: vm.weeklyFeedbackId,
                            planId: vm.activePlan?.id
                        )
                    } label: {
                        notificationPill(
                            icon: "chart.bar.doc.horizontal.fill",
                            iconColor: .orange,
                            text: "本周反馈已生成",
                            gradientColors: [.orange.opacity(0.1), .yellow.opacity(0.08)]
                        )
                    }
                    .buttonStyle(.plain)
                }

                // 未读消息通知
                if vm.unreadCount > 0 {
                    notificationPill(
                        icon: "envelope.badge.fill",
                        iconColor: .blue,
                        text: "\(vm.unreadCount) 条未读消息",
                        gradientColors: [.blue.opacity(0.08), .cyan.opacity(0.06)]
                    )
                }
            }
        }
    }

    private func notificationPill(icon: String, iconColor: Color, text: String, gradientColors: [Color]) -> some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.subheadline)
                .foregroundStyle(iconColor)
            Text(text)
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundStyle(.primary)
            Image(systemName: "chevron.right")
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(
                    LinearGradient(
                        colors: gradientColors,
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(iconColor.opacity(0.12), lineWidth: 1)
                )
        )
    }

    // MARK: - Today Task Card（双栏拆分 + 2. 行动按钮）

    private func todayTaskCard(_ task: DayTaskResponse, plan: PlanResponse?, vm: HomeViewModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("今日任务")
                    .font(.headline)
                Spacer()
                Text("第\(task.dayNumber)天")
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(Color.blue.opacity(0.1))
                    .foregroundStyle(.blue)
                    .clipShape(Capsule())
            }

            // 双栏：主练习 + 自然嵌入
            HStack(alignment: .top, spacing: 12) {
                // 主练习栏
                VStack(alignment: .leading, spacing: 6) {
                    Label("主练习", systemImage: "star.fill")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.orange)

                    Text(task.mainExerciseTitle)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(2)

                    Text(task.mainExerciseDescription)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(.orange.opacity(0.04))
                )

                // 自然嵌入栏
                VStack(alignment: .leading, spacing: 6) {
                    Label("自然嵌入", systemImage: "leaf.fill")
                        .font(.caption)
                        .fontWeight(.semibold)
                        .foregroundStyle(.green)

                    Text(task.naturalEmbedTitle)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(2)

                    Text(task.naturalEmbedDescription)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(10)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(.green.opacity(0.04))
                )
            }

            // 2. 行动按钮（状态化）
            let actionState = vm.taskActionState
            NavigationLink {
                PlanDetailView(childId: childId)
            } label: {
                HStack {
                    Image(systemName: actionState.icon)
                        .font(.subheadline)
                    Text(actionState.title)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
                .foregroundStyle(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(actionButtonColor(for: actionState))
                )
            }
            .buttonStyle(.plain)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(
                    LinearGradient(
                        colors: [Color.blue.opacity(0.08), Color.cyan.opacity(0.05)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
        )
    }

    private func actionButtonColor(for state: HomeViewModel.TaskActionState) -> Color {
        switch state {
        case .start: .blue
        case .record: .purple
        case .completed: .green
        }
    }

    // MARK: - Recent Record Preview（单条预览 + 查看更多）

    private func recentRecordPreview(_ records: [RecordResponse]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("最近记录")
                    .font(.headline)
                Spacer()
                if records.count > 1 {
                    Button {
                        appState.navigate(to: .recordList)
                    } label: {
                        HStack(spacing: 2) {
                            Text("查看更多")
                                .font(.caption)
                            Image(systemName: "chevron.right")
                                .font(.caption2)
                        }
                        .foregroundStyle(.blue)
                    }
                }
            }

            // 仅展示最近 1 条
            if let latest = records.first {
                HStack(spacing: 12) {
                    // 类型图标
                    ZStack {
                        Circle()
                            .fill(recordTypeColor(latest.type).opacity(0.12))
                            .frame(width: 36, height: 36)
                        Image(systemName: recordTypeIcon(latest.type))
                            .font(.system(size: 14))
                            .foregroundStyle(recordTypeColor(latest.type))
                    }

                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 6) {
                            Text(RecordType(rawValue: latest.type)?.displayName ?? latest.type)
                                .font(.subheadline)
                                .fontWeight(.medium)

                            if latest.syncedToPlan {
                                Image(systemName: "link")
                                    .font(.caption2)
                                    .foregroundStyle(.blue.opacity(0.6))
                            }
                        }

                        if let content = latest.content {
                            Text(content)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    }

                    Spacer()

                    Text(latest.createdAt, style: .relative)
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
                .padding(12)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.background)
                        .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
                )
            }
        }
    }

    private func recordTypeIcon(_ type: String) -> String {
        switch type {
        case "quick_check": return "checkmark.circle"
        case "voice": return "mic.fill"
        default: return "note.text"
        }
    }

    private func recordTypeColor(_ type: String) -> Color {
        switch type {
        case "quick_check": return .green
        case "voice": return .purple
        default: return .blue
        }
    }

    // MARK: - Helpers

    private func statusBadge(_ status: String) -> some View {
        let (text, color): (String, Color) = switch status {
        case "executed": ("已完成", .green)
        case "partial": ("部分完成", .orange)
        case "needs_record": ("待记录", .purple)
        default: ("待执行", .gray)
        }

        return Text(text)
            .font(.caption)
            .fontWeight(.medium)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(color.opacity(0.12))
            .foregroundStyle(color)
            .clipShape(Capsule())
    }
}

// MARK: - Shimmer Effect

private struct ShimmerModifier: ViewModifier {
    @State private var phase: CGFloat = 0

    func body(content: Content) -> some View {
        content
            .overlay(
                GeometryReader { geometry in
                    LinearGradient(
                        colors: [.clear, .white.opacity(0.4), .clear],
                        startPoint: .leading,
                        endPoint: .trailing
                    )
                    .offset(x: phase)
                    .onAppear {
                        withAnimation(.linear(duration: 1.5).repeatForever(autoreverses: false)) {
                            phase = geometry.size.width
                        }
                    }
                }
                .mask(content)
            )
    }
}

extension View {
    func shimmer() -> some View {
        modifier(ShimmerModifier())
    }
}
