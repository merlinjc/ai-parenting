import SwiftUI

/// 周反馈视图
///
/// 生成中轮询动画、正向变化、改进方向、总结文本、保守路径警示、决策选项、
/// 决策后自动创建下周计划并导航。
public struct FeedbackView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(AppState.self) private var appState
    @State private var viewModel: FeedbackViewModel?
    @State private var showPlanCreatedAlert = false

    public let feedbackId: UUID?
    public let planId: UUID?

    public init(feedbackId: UUID?, planId: UUID?) {
        self.feedbackId = feedbackId
        self.planId = planId
    }

    public var body: some View {
        Group {
            if let vm = viewModel {
                feedbackContent(vm)
            } else {
                ProgressView("加载中...")
            }
        }
        .navigationTitle(viewModel?.statusText ?? "周反馈")
        .task {
            if viewModel == nil {
                let vm = FeedbackViewModel(apiClient: apiClient)
                viewModel = vm
                if let feedbackId {
                    await vm.loadFeedback(feedbackId: feedbackId)
                    await vm.markViewed()
                } else if let planId {
                    await vm.triggerGeneration(planId: planId)
                }
            }
        }
        .onDisappear {
            viewModel?.stopPolling()
        }
        .alert("下周计划已创建", isPresented: $showPlanCreatedAlert) {
            Button("查看新计划") {
                if let newPlanId = viewModel?.newPlanId {
                    appState.navigate(to: .planDetail(planId: newPlanId))
                }
            }
            Button("留在反馈页", role: .cancel) { }
        } message: {
            Text("已根据本周反馈自动生成下周训练计划")
        }
    }

    // MARK: - Content Router

    @ViewBuilder
    private func feedbackContent(_ vm: FeedbackViewModel) -> some View {
        if vm.isLoading || vm.feedback?.status == "generating" {
            generatingView()
        } else if vm.isFailed {
            failedView(vm)
        } else if let feedback = vm.feedback {
            completedView(feedback, vm)
        }
    }

    // MARK: - Generating State

    private func generatingView() -> some View {
        VStack(spacing: 20) {
            ProgressView()
                .scaleEffect(1.3)
                .tint(.blue)

            Text("正在生成本周反馈...")
                .font(.title3)
                .fontWeight(.medium)

            Text("AI 正在分析本周的观察记录和计划完成情况")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
    }

    // MARK: - Failed State

    private func failedView(_ vm: FeedbackViewModel) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundStyle(.orange)

            Text("反馈生成失败")
                .font(.title3)
                .fontWeight(.medium)

            if let errorInfo = vm.feedback?.errorInfo {
                Text(errorInfo)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if let planId {
                Button("重新生成") {
                    Task { await vm.triggerGeneration(planId: planId) }
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    // MARK: - Completed State

    private func completedView(_ feedback: WeeklyFeedbackResponse, _ vm: FeedbackViewModel) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // 统计概览
                statsCard(feedback)

                // 总结文本
                if let summary = feedback.summaryText {
                    summaryCard(summary)
                }

                // 正向变化分区（结构化卡片）
                if !vm.parsedPositiveChanges.isEmpty {
                    positiveChangesSection(vm.parsedPositiveChanges)
                }

                // 改进方向分区（结构化卡片）
                if !vm.parsedOpportunities.isEmpty {
                    opportunitiesSection(vm.parsedOpportunities)
                }

                // 保守路径警示卡
                if let note = vm.conservativePathNote, !note.isEmpty {
                    conservativePathCard(note)
                }

                // 决策区（未决策时展示）
                if vm.isReady {
                    decisionSection(vm)
                } else if vm.isDecided {
                    decidedBadge(feedback)
                }
            }
            .padding()
        }
    }

    // MARK: - Stats Card

    private func statsCard(_ feedback: WeeklyFeedbackResponse) -> some View {
        HStack(spacing: 0) {
            statItem(
                value: "\(feedback.recordCountThisWeek)",
                label: "观察记录",
                icon: "doc.text",
                color: .blue
            )
            Divider()
                .frame(height: 40)
            statItem(
                value: "\(Int(feedback.completionRateThisWeek * 100))%",
                label: "完成率",
                icon: "chart.pie",
                color: .green
            )
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
    }

    private func statItem(value: String, label: String, icon: String, color: Color) -> some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .foregroundStyle(color)
            Text(value)
                .font(.title2)
                .fontWeight(.bold)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Summary Card

    private func summaryCard(_ text: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("本周总结", systemImage: "text.quote")
                .font(.headline)

            Text(text)
                .font(.body)
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(
                            LinearGradient(
                                colors: [.blue.opacity(0.05), .cyan.opacity(0.03)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                )
        }
    }

    // MARK: - Positive Changes Section

    private func positiveChangesSection(_ changes: [FeedbackChangeItem]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("正向变化", systemImage: "arrow.up.circle.fill")
                .font(.headline)
                .foregroundStyle(.green)

            ForEach(changes) { item in
                VStack(alignment: .leading, spacing: 6) {
                    Text(item.title)
                        .font(.subheadline)
                        .fontWeight(.semibold)

                    Text(item.description)
                        .font(.body)
                        .foregroundStyle(.secondary)

                    if let evidence = item.supportingEvidence, !evidence.isEmpty {
                        HStack(alignment: .top, spacing: 6) {
                            Image(systemName: "quote.opening")
                                .font(.caption2)
                                .foregroundStyle(.green.opacity(0.6))
                            Text(evidence)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .italic()
                        }
                        .padding(.top, 2)
                    }
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.green.opacity(0.06))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .strokeBorder(.green.opacity(0.15), lineWidth: 1)
                        )
                )
            }
        }
    }

    // MARK: - Opportunities Section

    private func opportunitiesSection(_ items: [FeedbackChangeItem]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("改进方向", systemImage: "lightbulb.fill")
                .font(.headline)
                .foregroundStyle(.orange)

            ForEach(items) { item in
                VStack(alignment: .leading, spacing: 6) {
                    Text(item.title)
                        .font(.subheadline)
                        .fontWeight(.semibold)

                    Text(item.description)
                        .font(.body)
                        .foregroundStyle(.secondary)

                    if let evidence = item.supportingEvidence, !evidence.isEmpty {
                        HStack(alignment: .top, spacing: 6) {
                            Image(systemName: "quote.opening")
                                .font(.caption2)
                                .foregroundStyle(.orange.opacity(0.6))
                            Text(evidence)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .italic()
                        }
                        .padding(.top, 2)
                    }
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.orange.opacity(0.06))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .strokeBorder(.orange.opacity(0.15), lineWidth: 1)
                        )
                )
            }
        }
    }

    // MARK: - Conservative Path Card

    private func conservativePathCard(_ note: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: "exclamationmark.shield.fill")
                    .foregroundStyle(.red.opacity(0.8))
                Text("保守路径说明")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(.red.opacity(0.8))
            }

            Text(note)
                .font(.body)
                .foregroundStyle(.primary.opacity(0.85))
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.red.opacity(0.04))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .strokeBorder(.red.opacity(0.25), lineWidth: 1.5)
                )
        )
    }

    // MARK: - Decision Section

    private func decisionSection(_ vm: FeedbackViewModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("下周方向")
                .font(.headline)

            Text("根据本周情况，请选择下周计划的方向")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            // 优先使用 AI 生成的决策选项，回退到硬编码枚举
            let aiOptions = vm.parsedDecisionOptions
            if !aiOptions.isEmpty {
                aiDecisionOptions(aiOptions, vm)
            } else {
                fallbackDecisionOptions(vm)
            }

            if vm.isSubmitting || vm.isCreatingPlan {
                HStack {
                    ProgressView()
                    Text(vm.isCreatingPlan ? "正在生成下周计划..." : "正在提交...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    /// AI 生成的决策选项卡片
    private func aiDecisionOptions(_ options: [DecisionOptionItem], _ vm: FeedbackViewModel) -> some View {
        ForEach(options) { option in
            Button {
                handleDecision(option.decisionValue ?? .continue, vm: vm)
            } label: {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(option.text)
                            .font(.body)
                            .fontWeight(.medium)

                        Text(option.rationale)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(3)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.background)
                        .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
                )
            }
            .buttonStyle(.plain)
            .disabled(vm.isSubmitting || vm.isCreatingPlan)
        }
    }

    /// 回退的硬编码决策选项（AI 选项解析失败时使用）
    private func fallbackDecisionOptions(_ vm: FeedbackViewModel) -> some View {
        ForEach(DecisionValue.allCases, id: \.rawValue) { decision in
            Button {
                handleDecision(decision, vm: vm)
            } label: {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(decision.displayName)
                            .font(.body)
                            .fontWeight(.medium)

                        Text(decisionDescription(decision))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.background)
                        .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
                )
            }
            .buttonStyle(.plain)
            .disabled(vm.isSubmitting || vm.isCreatingPlan)
        }
    }

    /// 统一处理决策提交 + 计划创建 + 导航
    private func handleDecision(_ decision: DecisionValue, vm: FeedbackViewModel) {
        Task {
            await vm.submitDecision(decision)
            // 决策成功后自动创建下周计划
            if vm.isDecided {
                if let newPlanId = await vm.createNewPlanAfterDecision() {
                    showPlanCreatedAlert = true
                    _ = newPlanId // 用于 alert 中的导航
                }
            }
        }
    }

    // MARK: - Decided Badge

    private func decidedBadge(_ feedback: WeeklyFeedbackResponse) -> some View {
        VStack(spacing: 12) {
            HStack {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.green)

                VStack(alignment: .leading) {
                    Text("已完成决策")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    if let decision = feedback.selectedDecision {
                        Text(DecisionValue(rawValue: decision)?.displayName ?? decision)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(.green.opacity(0.08))
            )

            // 已决策后仍可手动创建新计划
            if let vm = viewModel, vm.newPlanId == nil {
                Button {
                    Task {
                        if let newPlanId = await vm.createNewPlanAfterDecision() {
                            showPlanCreatedAlert = true
                            _ = newPlanId
                        }
                    }
                } label: {
                    Label("生成下周计划", systemImage: "calendar.badge.plus")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.blue)
                .disabled(vm.isCreatingPlan)
            } else if let vm = viewModel, let newPlanId = vm.newPlanId {
                Button {
                    appState.navigate(to: .planDetail(planId: newPlanId))
                } label: {
                    Label("查看下周计划", systemImage: "arrow.right.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.blue)
            }
        }
    }

    // MARK: - Helpers

    private func decisionDescription(_ decision: DecisionValue) -> String {
        switch decision {
        case .continue: return "保持当前主题和难度继续练习"
        case .lowerDifficulty: return "降低练习难度，巩固已有进步"
        case .changeFocus: return "更换关注主题，探索其他发展领域"
        }
    }
}
