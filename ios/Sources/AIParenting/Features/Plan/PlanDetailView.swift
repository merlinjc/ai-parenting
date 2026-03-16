import SwiftUI

/// 计划详情视图
///
/// 7 天任务日历视图 + 完成率进度 + 日任务列表 + 观察候选项 + 周反馈入口 + 历次计划入口。
/// DayTaskDetailView 携带 planId / focusTheme / observationCandidates / weekendReviewPrompt / conservativeNote，
/// 支持完成后导航到记录页或即时求助。
public struct PlanDetailView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(AppState.self) private var appState
    @State private var viewModel: PlanViewModel?
    @State private var selectedDay: Int = 1
    @State private var showFeedbackSheet = false
    @State private var showPlanHistory = false

    public let childId: UUID

    public init(childId: UUID) {
        self.childId = childId
    }

    public var body: some View {
        NavigationStack {
            Group {
                if let vm = viewModel {
                    planContent(vm)
                } else {
                    ProgressView("加载中...")
                }
            }
            .navigationTitle("微计划")
            .task {
                if viewModel == nil {
                    let vm = PlanViewModel(apiClient: apiClient, childId: childId)
                    viewModel = vm
                    await vm.loadActivePlan()
                    if let plan = vm.plan {
                        selectedDay = plan.currentDay
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func planContent(_ vm: PlanViewModel) -> some View {
        if vm.isLoading && vm.plan == nil {
            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.2)
                Text("正在加载计划...")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        } else if vm.plan == nil {
            // 无活跃计划
            emptyPlanView(vm)
        } else if let plan = vm.plan {
            ScrollView {
                VStack(spacing: 20) {
                    // 进度区
                    progressSection(plan)

                    // 7 天日历
                    dayCalendar(plan)

                    // 选中日的任务详情
                    if let task = plan.dayTasks.first(where: { $0.dayNumber == selectedDay }) {
                        DayTaskDetailView(
                            task: task,
                            planId: plan.id,
                            focusTheme: plan.focusTheme,
                            observationCandidates: vm.cachedObservationCandidates,
                            weekendReviewPrompt: plan.weekendReviewPrompt,
                            conservativeNote: plan.conservativeNote,
                            onUpdateStatus: { status in
                                Task { await vm.updateCompletion(dayNumber: task.dayNumber, status: status) }
                            },
                            onNavigateToRecord: { sourcePlanId, theme in
                                appState.navigate(to: .recordCreate(
                                    sourcePlanId: sourcePlanId,
                                    sourceSessionId: nil,
                                    theme: theme
                                ))
                            },
                            onNavigateToInstantHelp: { planId in
                                appState.navigate(to: .instantHelp(planId: planId))
                            }
                        )
                    }

                    // 底部操作入口
                    bottomActions(vm, plan: plan)
                }
                .padding()
            }
            .refreshable {
                await vm.loadActivePlan()
            }
            .sheet(isPresented: $showFeedbackSheet) {
                NavigationStack {
                    FeedbackView(
                        feedbackId: nil,
                        planId: vm.plan?.id
                    )
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("关闭") { showFeedbackSheet = false }
                        }
                    }
                }
            }
            .sheet(isPresented: $showPlanHistory) {
                NavigationStack {
                    planHistoryView(vm)
                        .navigationTitle("历次计划")
                        .toolbar {
                            ToolbarItem(placement: .cancellationAction) {
                                Button("关闭") { showPlanHistory = false }
                            }
                        }
                }
            }
        }
    }

    // MARK: - Empty Plan

    private func emptyPlanView(_ vm: PlanViewModel) -> some View {
        VStack(spacing: 20) {
            Image(systemName: "calendar.badge.plus")
                .font(.system(size: 56))
                .foregroundStyle(.blue.opacity(0.6))

            Text("暂无活跃计划")
                .font(.title3)
                .fontWeight(.medium)

            Text("为宝宝生成一份个性化的 7 天微计划")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Button {
                Task { await vm.createNewPlan() }
            } label: {
                HStack {
                    if vm.isCreating {
                        ProgressView()
                            .tint(.white)
                    }
                    Text(vm.isCreating ? "AI 生成中..." : "生成新计划")
                }
                .frame(maxWidth: .infinity)
                .padding()
                .background(
                    LinearGradient(colors: [.blue, .cyan], startPoint: .leading, endPoint: .trailing)
                )
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            .disabled(vm.isCreating)
            .padding(.horizontal, 40)

            // 即使无活跃计划也可查看历次计划
            Button {
                showPlanHistory = true
                Task { await vm.loadPlanHistory() }
            } label: {
                Label("查看历次计划", systemImage: "clock.arrow.circlepath")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .sheet(isPresented: $showPlanHistory) {
            NavigationStack {
                planHistoryView(vm)
                    .navigationTitle("历次计划")
                    .toolbar {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("关闭") { showPlanHistory = false }
                        }
                    }
            }
        }
    }

    // MARK: - Progress Section

    private func progressSection(_ plan: PlanResponse) -> some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(plan.title)
                        .font(.headline)
                    Text(plan.primaryGoal)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }

            HStack {
                // 圆形进度
                ZStack {
                    Circle()
                        .stroke(Color.gray.opacity(0.2), lineWidth: 6)
                    Circle()
                        .trim(from: 0, to: plan.completionRate)
                        .stroke(
                            LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing),
                            style: StrokeStyle(lineWidth: 6, lineCap: .round)
                        )
                        .rotationEffect(.degrees(-90))
                    Text("\(Int(plan.completionRate * 100))%")
                        .font(.system(.title3, design: .rounded))
                        .fontWeight(.bold)
                }
                .frame(width: 72, height: 72)

                Spacer()

                VStack(alignment: .trailing, spacing: 4) {
                    Label(
                        FocusTheme(rawValue: plan.focusTheme)?.displayName ?? plan.focusTheme,
                        systemImage: "target"
                    )
                    .font(.caption)
                    .foregroundStyle(.blue)

                    Text("第 \(plan.currentDay)/7 天")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    // 风险等级标签
                    let riskLevel = RiskLevel(rawValue: plan.riskLevelAtCreation)
                    if let riskLevel, riskLevel != .normal {
                        Text(riskLevel.displayName)
                            .font(.caption2)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(
                                Capsule()
                                    .fill(riskLevel == .attention ? .orange.opacity(0.12) : .red.opacity(0.12))
                            )
                            .foregroundStyle(riskLevel == .attention ? .orange : .red)
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

    // MARK: - Day Calendar

    private func dayCalendar(_ plan: PlanResponse) -> some View {
        HStack(spacing: 8) {
            ForEach(1...7, id: \.self) { day in
                let task = plan.dayTasks.first { $0.dayNumber == day }
                let isCompleted = task?.completionStatus == "executed"
                let isCurrent = day == plan.currentDay
                let isSelected = day == selectedDay

                Button {
                    selectedDay = day
                } label: {
                    VStack(spacing: 4) {
                        Text("D\(day)")
                            .font(.system(.caption, design: .rounded))
                            .fontWeight(isSelected ? .bold : .regular)

                        ZStack {
                            Circle()
                                .fill(isSelected ? Color.blue : (isCurrent ? Color.blue.opacity(0.15) : Color.gray.opacity(0.08)))
                                .frame(width: 36, height: 36)

                            if isCompleted {
                                Image(systemName: "checkmark")
                                    .font(.caption)
                                    .fontWeight(.bold)
                                    .foregroundStyle(isSelected ? .white : .green)
                            } else {
                                Text("\(day)")
                                    .font(.caption)
                                    .fontWeight(.medium)
                                    .foregroundStyle(isSelected ? .white : .primary)
                            }
                        }
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.background)
                .shadow(color: .black.opacity(0.03), radius: 4, y: 2)
        )
    }

    // MARK: - Bottom Actions

    private func bottomActions(_ vm: PlanViewModel, plan: PlanResponse) -> some View {
        VStack(spacing: 12) {
            // 查看本周反馈入口
            if vm.hasWeeklyFeedback {
                Button {
                    showFeedbackSheet = true
                } label: {
                    HStack {
                        Image(systemName: "chart.bar.doc.horizontal")
                            .foregroundStyle(.purple)
                        Text(vm.weeklyFeedbackButtonText)
                            .font(.subheadline)
                            .fontWeight(.medium)
                        Spacer()
                        if vm.weeklyFeedbackStatus == "ready" {
                            Circle()
                                .fill(.red)
                                .frame(width: 8, height: 8)
                        }
                        Image(systemName: "chevron.right")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .padding()
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(.purple.opacity(0.06))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .strokeBorder(.purple.opacity(0.15), lineWidth: 1)
                            )
                    )
                }
                .buttonStyle(.plain)
            }

            // 查看历次计划入口
            Button {
                showPlanHistory = true
                Task { await vm.loadPlanHistory() }
            } label: {
                HStack {
                    Image(systemName: "clock.arrow.circlepath")
                        .foregroundStyle(.blue)
                    Text("查看历次计划")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.gray.opacity(0.06))
                )
            }
            .buttonStyle(.plain)
        }
    }

    // MARK: - Plan History

    private func planHistoryView(_ vm: PlanViewModel) -> some View {
        Group {
            if vm.isLoadingHistory {
                ProgressView("加载中...")
            } else if vm.planHistory.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "tray")
                        .font(.system(size: 40))
                        .foregroundStyle(.secondary)
                    Text("暂无历史计划")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            } else {
                List(vm.planHistory) { plan in
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(plan.title)
                                .font(.subheadline)
                                .fontWeight(.medium)
                            Spacer()
                            Text("v\(plan.version)")
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Capsule().fill(.blue.opacity(0.1)))
                                .foregroundStyle(.blue)
                        }

                        Text(plan.primaryGoal)
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        HStack(spacing: 12) {
                            Label(
                                FocusTheme(rawValue: plan.focusTheme)?.displayName ?? plan.focusTheme,
                                systemImage: "target"
                            )
                            .font(.caption2)
                            .foregroundStyle(.blue)

                            Text("\(Int(plan.completionRate * 100))% 完成")
                                .font(.caption2)
                                .foregroundStyle(plan.completionRate >= 0.7 ? .green : .orange)

                            Spacer()

                            Text(plan.createdAt, style: .date)
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .task {
            if vm.planHistory.isEmpty {
                await vm.loadPlanHistory()
            }
        }
    }
}
