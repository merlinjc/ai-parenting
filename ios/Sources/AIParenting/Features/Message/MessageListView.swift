import SwiftUI

/// 消息列表视图
///
/// 未读优先排序、游标分页、消息卡片、滑动标已读。
public struct MessageListView: View {

    @Environment(APIClient.self) private var apiClient
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

    // MARK: - Message Card

    private func messageCard(_ message: MessageResponse, vm: MessageViewModel) -> some View {
        Button {
            Task {
                await vm.reportClick(message.id)
                if message.readStatus == "unread" {
                    await vm.markAsRead(message.id)
                }
            }
        } label: {
            HStack(alignment: .top, spacing: 12) {
                // 类型图标
                ZStack {
                    Circle()
                        .fill(messageTypeColor(message.type).opacity(0.12))
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
                            .foregroundStyle(.primary)
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
                }

                // 未读指示点
                if message.readStatus == "unread" {
                    Circle()
                        .fill(.blue)
                        .frame(width: 8, height: 8)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 10)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Helpers

    private func messageTypeIcon(_ type: String) -> String {
        switch type {
        case "plan_reminder": return "calendar.badge.clock"
        case "record_prompt": return "square.and.pencil"
        case "weekly_feedback_ready": return "chart.bar.doc.horizontal"
        case "risk_alert": return "exclamationmark.triangle"
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
}
