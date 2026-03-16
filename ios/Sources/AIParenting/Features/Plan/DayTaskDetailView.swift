import SwiftUI

/// 日任务详情视图
///
/// 主题练习描述、自然融入描述、示范话术、观察要点、完成状态选择器。
/// 完成后弹出导航选项（去记录/现在求助/留在计划页）。
public struct DayTaskDetailView: View {

    public let task: DayTaskResponse
    public let planId: UUID?
    public let focusTheme: String?
    public let observationCandidates: [ObservationCandidateItem]
    public let weekendReviewPrompt: String?
    public let conservativeNote: String?
    public let onUpdateStatus: (CompletionStatus) -> Void
    public var onNavigateToRecord: ((_ sourcePlanId: UUID, _ theme: String?) -> Void)?
    public var onNavigateToInstantHelp: ((_ planId: UUID) -> Void)?

    @State private var showPostCompletionSheet = false
    @State private var lastSelectedStatus: CompletionStatus?

    public init(
        task: DayTaskResponse,
        planId: UUID? = nil,
        focusTheme: String? = nil,
        observationCandidates: [ObservationCandidateItem] = [],
        weekendReviewPrompt: String? = nil,
        conservativeNote: String? = nil,
        onUpdateStatus: @escaping (CompletionStatus) -> Void,
        onNavigateToRecord: ((_ sourcePlanId: UUID, _ theme: String?) -> Void)? = nil,
        onNavigateToInstantHelp: ((_ planId: UUID) -> Void)? = nil
    ) {
        self.task = task
        self.planId = planId
        self.focusTheme = focusTheme
        self.observationCandidates = observationCandidates
        self.weekendReviewPrompt = weekendReviewPrompt
        self.conservativeNote = conservativeNote
        self.onUpdateStatus = onUpdateStatus
        self.onNavigateToRecord = onNavigateToRecord
        self.onNavigateToInstantHelp = onNavigateToInstantHelp
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // 主题练习
            sectionCard(
                icon: "star.fill",
                iconColor: .orange,
                title: "主题练习",
                subtitle: task.mainExerciseTitle,
                body: task.mainExerciseDescription
            )

            // 自然融入
            sectionCard(
                icon: "leaf.fill",
                iconColor: .green,
                title: "自然融入",
                subtitle: task.naturalEmbedTitle,
                body: task.naturalEmbedDescription
            )

            // 示范话术
            VStack(alignment: .leading, spacing: 8) {
                Label("示范话术", systemImage: "quote.bubble.fill")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(.purple)

                Text(task.demoScript)
                    .font(.body)
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(.purple.opacity(0.05))
                    )
            }

            // 观察要点
            VStack(alignment: .leading, spacing: 8) {
                Label("观察要点", systemImage: "eye.fill")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .foregroundStyle(.blue)

                Text(task.observationPoint)
                    .font(.body)
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(.blue.opacity(0.05))
                    )
            }

            // 快速打点候选项
            if !observationCandidates.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Label("快速观察打点", systemImage: "checklist")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.teal)

                    FlowLayout(spacing: 8) {
                        ForEach(observationCandidates) { candidate in
                            HStack(spacing: 4) {
                                Image(systemName: candidate.defaultSelected ? "checkmark.circle.fill" : "circle")
                                    .font(.caption2)
                                Text(candidate.text)
                                    .font(.caption)
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(
                                Capsule()
                                    .fill(candidate.defaultSelected ? .teal.opacity(0.12) : .gray.opacity(0.08))
                            )
                            .foregroundStyle(candidate.defaultSelected ? .teal : .secondary)
                        }
                    }
                }
            }

            // 周末复盘引导（Day 6-7）
            if let prompt = weekendReviewPrompt, task.dayNumber >= 6 {
                VStack(alignment: .leading, spacing: 8) {
                    Label("周末复盘", systemImage: "calendar.badge.checkmark")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.indigo)

                    Text(prompt)
                        .font(.subheadline)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(.indigo.opacity(0.05))
                        )
                }
            }

            // 保守路径说明
            if let note = conservativeNote {
                VStack(alignment: .leading, spacing: 8) {
                    Label("更温和的方式", systemImage: "heart.fill")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.pink)

                    Text(note)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(.pink.opacity(0.05))
                        )
                }
            }

            // 完成状态
            VStack(alignment: .leading, spacing: 8) {
                Text("完成状态")
                    .font(.subheadline)
                    .fontWeight(.semibold)

                HStack(spacing: 8) {
                    ForEach(CompletionStatus.allCases, id: \.rawValue) { status in
                        let isActive = task.completionStatus == status.rawValue
                        Button {
                            lastSelectedStatus = status
                            onUpdateStatus(status)
                            // 当标记为已执行或部分完成时，弹出后续操作选项
                            if status == .executed || status == .partial {
                                showPostCompletionSheet = true
                            }
                        } label: {
                            Text(status.displayName)
                                .font(.caption)
                                .fontWeight(.medium)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(
                                    RoundedRectangle(cornerRadius: 8)
                                        .fill(isActive ? statusColor(status).opacity(0.15) : .gray.opacity(0.08))
                                )
                                .foregroundStyle(isActive ? statusColor(status) : .secondary)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 8)
                                        .stroke(isActive ? statusColor(status).opacity(0.3) : .clear, lineWidth: 1)
                                )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            // "现在求助"快捷按钮
            if let planId = planId {
                Button {
                    onNavigateToInstantHelp?(planId)
                } label: {
                    Label("现在求助", systemImage: "questionmark.bubble.fill")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 10)
                                .fill(.orange.opacity(0.1))
                        )
                        .foregroundStyle(.orange)
                }
                .buttonStyle(.plain)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
        .confirmationDialog(
            "任务已更新，下一步想做什么？",
            isPresented: $showPostCompletionSheet,
            titleVisibility: .visible
        ) {
            if let planId = planId {
                Button("去记录这次练习") {
                    onNavigateToRecord?(planId, focusTheme)
                }
                Button("现在求助") {
                    onNavigateToInstantHelp?(planId)
                }
            }
            Button("留在计划页", role: .cancel) {}
        } message: {
            Text("记录练习过程可以帮助系统更好地了解孩子的状态")
        }
    }

    // MARK: - Section Card

    private func sectionCard(icon: String, iconColor: Color, title: String, subtitle: String, body: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: icon)
                .font(.subheadline)
                .fontWeight(.semibold)
                .foregroundStyle(iconColor)

            Text(subtitle)
                .font(.body)
                .fontWeight(.medium)

            Text(body)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Helpers

    private func statusColor(_ status: CompletionStatus) -> Color {
        switch status {
        case .executed: return .green
        case .partial: return .orange
        case .needsRecord: return .purple
        case .pending: return .gray
        }
    }
}
