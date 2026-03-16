import SwiftUI

/// 日任务详情视图
///
/// 主题练习描述、自然融入描述、示范话术、观察要点、完成状态选择器。
public struct DayTaskDetailView: View {

    public let task: DayTaskResponse
    public let onUpdateStatus: (CompletionStatus) -> Void

    @State private var showStatusPicker = false

    public init(task: DayTaskResponse, onUpdateStatus: @escaping (CompletionStatus) -> Void) {
        self.task = task
        self.onUpdateStatus = onUpdateStatus
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

            // 完成状态
            VStack(alignment: .leading, spacing: 8) {
                Text("完成状态")
                    .font(.subheadline)
                    .fontWeight(.semibold)

                HStack(spacing: 8) {
                    ForEach(CompletionStatus.allCases, id: \.rawValue) { status in
                        let isActive = task.completionStatus == status.rawValue
                        Button {
                            onUpdateStatus(status)
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
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
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
