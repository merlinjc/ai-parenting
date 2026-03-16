import SwiftUI

/// 周反馈视图
///
/// 生成中轮询动画、正向变化、改进方向、总结文本、决策选项。
public struct FeedbackView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var viewModel: FeedbackViewModel?
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
    }

    @ViewBuilder
    private func feedbackContent(_ vm: FeedbackViewModel) -> some View {
        if vm.isLoading || vm.feedback?.status == "generating" {
            // 生成中
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
        } else if vm.isFailed {
            // 失败
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
        } else if let feedback = vm.feedback {
            // 正常展示
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // 统计概览
                    statsCard(feedback)

                    // 总结文本
                    if let summary = feedback.summaryText {
                        summaryCard(summary)
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

    // MARK: - Decision Section

    private func decisionSection(_ vm: FeedbackViewModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("下周方向")
                .font(.headline)

            Text("根据本周情况，请选择下周计划的方向")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            ForEach(DecisionValue.allCases, id: \.rawValue) { decision in
                Button {
                    Task { await vm.submitDecision(decision) }
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
                .disabled(vm.isSubmitting)
            }

            if vm.isSubmitting {
                HStack {
                    ProgressView()
                    Text("正在提交...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    // MARK: - Decided Badge

    private func decidedBadge(_ feedback: WeeklyFeedbackResponse) -> some View {
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
