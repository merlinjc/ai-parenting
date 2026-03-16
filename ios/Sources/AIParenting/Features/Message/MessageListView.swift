import SwiftUI

/// 消息列表视图
///
/// 未读优先排序、游标分页、消息卡片（点击深链到目标页）、risk_alert 特殊样式。
public struct MessageListView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(AppState.self) private var appState
    @State private var viewModel: MessageViewModel?

    public init() {}

    public var body: some View {
        NavigationStack {
            Group {
                if let vm = viewModel {
                    messageContent(vm)
                } else {
                    ProgressView("加载中...")
                }
            }
            .navigationTitle("消息")
            .task {
                if viewModel == nil {
                    let vm = MessageViewModel(apiClient: apiClient)
                    viewModel = vm
                    await vm.loadMessages()
                }
            }
        }
    }

    @ViewBuilder
    private func messageContent(_ vm: MessageViewModel) -> some View {
        if vm.isLoading && vm.messages.isEmpty {
            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.2)
                Text("正在加载消息...")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        } else if vm.messages.isEmpty {
            VStack(spacing: 20) {
                Image(systemName: "bell.slash")
                    .font(.system(size: 56))
                    .foregroundStyle(.gray.opacity(0.4))

                Text("暂无消息")
                    .font(.title3)
                    .fontWeight(.medium)

                Text("新的提醒和通知会显示在这里")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        } else {
            ScrollView {
                LazyVStack(spacing: 8) {
                    // 未读计数
                    if vm.totalUnread > 0 {
                        HStack {
                            Text("\(vm.totalUnread) 条未读消息")
                                .font(.caption)
                                .fontWeight(.medium)
                                .foregroundStyle(.blue)
                            Spacer()
                        }
                        .padding(.horizontal)
                        .padding(.top, 4)
                    }

                    ForEach(vm.messages) { message in
                        messageCard(message, vm: vm)
                            .swipeActions(edge: .trailing) {
                                if message.readStatus == "unread" {
                                    Button {
                                        Task { await vm.markAsRead(message.id) }
                                    } label: {
                                        Label("已读", systemImage: "envelope.open")
                                    }
                                    .tint(.blue)
                                }
                            }
                    }

                    // 加载更多
                    if vm.hasMore {
                        ProgressView()
                            .padding()
                            .task {
                                await vm.loadMore()
                            }
                    }
                }
                .padding(.vertical, 8)
            }
            .refreshable {
                await vm.refresh()
            }
        }
    }

    // MARK: - Message Card（支持深链导航）

    private func messageCard(_ message: MessageResponse, vm: MessageViewModel) -> some View {
        Button {
            Task {
                await vm.reportClick(message.id)
                if message.readStatus == "unread" {
                    await vm.markAsRead(message.id)
                }
                // 根据 targetPage 执行深链导航
                navigateToTarget(message)
            }
        } label: {
            HStack(alignment: .top, spacing: 12) {
                // 类型图标
                ZStack {
                    Circle()
                        .fill(messageTypeColor(message.type).opacity(message.isRiskAlert ? 0.2 : 0.12))
                        .frame(width: 40, height: 40)

                    Image(systemName: messageTypeIcon(message.type))
                        .font(.body)
                        .foregroundStyle(messageTypeColor(message.type))
                }

                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(message.title)
                            .font(.subheadline)
                            .fontWeight(message.readStatus == "unread" ? .bold : .regular)
                            .foregroundStyle(message.isRiskAlert ? .red : .primary)
                            .lineLimit(1)

                        Spacer()

                        Text(message.createdAt, style: .relative)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }

                    Text(message.summary)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)

                    // 深链目标提示
                    if let targetPage = message.targetPage {
                        HStack(spacing: 4) {
                            Image(systemName: "arrow.right.circle")
                                .font(.caption2)
                            Text(targetPageLabel(targetPage))
                                .font(.caption2)
                                .fontWeight(.medium)
                        }
                        .foregroundStyle(messageTypeColor(message.type))
                        .padding(.top, 2)
                    }
                }

                // 未读指示点
                if message.readStatus == "unread" {
                    Circle()
                        .fill(message.isRiskAlert ? .red : .blue)
                        .frame(width: 8, height: 8)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 10)
            .background(
                message.isRiskAlert
                    ? RoundedRectangle(cornerRadius: 8).fill(.red.opacity(0.04)).eraseToAnyView()
                    : RoundedRectangle(cornerRadius: 8).fill(.clear).eraseToAnyView()
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Deep Link Navigation

    private func navigateToTarget(_ message: MessageResponse) {
        guard let targetPage = message.targetPage else { return }
        let params = message.parsedTargetParams

        switch targetPage {
        case "plan_detail":
            if let planIdStr = params?.planId, let planId = UUID(uuidString: planIdStr) {
                appState.navigate(to: .planDetail(planId: planId))
            } else {
                appState.navigate(to: .planDetail(planId: UUID()))
            }

        case "record_create":
            appState.navigate(to: .recordCreate(sourcePlanId: nil, sourceSessionId: nil, theme: nil))

        case "record_list":
            appState.navigate(to: .recordList)

        case "weekly_feedback":
            if let feedbackIdStr = params?.feedbackId, let feedbackId = UUID(uuidString: feedbackIdStr) {
                appState.navigate(to: .weeklyFeedback(feedbackId: feedbackId))
            }

        default:
            break
        }

        // 如果是 risk_alert，额外触发 child 数据刷新
        if message.isRiskAlert {
            Task {
                await appState.refreshActiveChild()
            }
        }
    }

    // MARK: - Helpers

    private func messageTypeIcon(_ type: String) -> String {
        switch type {
        case "plan_reminder": return "calendar.badge.clock"
        case "record_prompt": return "square.and.pencil"
        case "weekly_feedback_ready": return "chart.bar.doc.horizontal"
        case "risk_alert": return "exclamationmark.triangle.fill"
        case "system": return "bell"
        default: return "bell"
        }
    }

    private func messageTypeColor(_ type: String) -> Color {
        switch type {
        case "plan_reminder": return .blue
        case "record_prompt": return .green
        case "weekly_feedback_ready": return .orange
        case "risk_alert": return .red
        case "system": return .gray
        default: return .gray
        }
    }

    private func targetPageLabel(_ targetPage: String) -> String {
        switch targetPage {
        case "plan_detail": return "查看计划"
        case "record_create": return "去记录"
        case "record_list": return "查看记录"
        case "weekly_feedback": return "查看周反馈"
        default: return "查看详情"
        }
    }
}

// MARK: - View Type Eraser

extension View {
    func eraseToAnyView() -> AnyView {
        AnyView(self)
    }
}
