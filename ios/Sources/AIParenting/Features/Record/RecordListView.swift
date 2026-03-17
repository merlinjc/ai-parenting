import SwiftUI

/// 记录列表视图
///
/// 按时间倒序、游标分页加载、类型过滤标签。
public struct RecordListView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var viewModel: RecordViewModel?
    @State private var showCreateSheet = false
    public let childId: UUID

    /// 过滤选项：(filterValue, displayLabel, stableId)
    private let filterOptions: [(String?, String, String)] = [
        (nil, "全部", "all"),
        ("quick_check", "快检", "quick_check"),
        ("event", "事件", "event"),
        ("voice", "语音", "voice"),
    ]

    public init(childId: UUID) {
        self.childId = childId
    }

    public var body: some View {
        NavigationStack {
            Group {
                if let vm = viewModel {
                    recordContent(vm)
                } else {
                    ProgressView("加载中...")
                }
            }
            .navigationTitle("观察记录")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showCreateSheet = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                            .font(.title3)
                    }
                }
            }
            .sheet(isPresented: $showCreateSheet) {
                if let vm = viewModel {
                    RecordCreateView(childId: childId, viewModel: vm) {
                        showCreateSheet = false
                    }
                }
            }
            .task {
                if viewModel == nil {
                    let vm = RecordViewModel(apiClient: apiClient, childId: childId)
                    viewModel = vm
                    await vm.loadRecords()
                }
            }
        }
    }

    @ViewBuilder
    private func recordContent(_ vm: RecordViewModel) -> some View {
        if vm.isLoading && vm.records.isEmpty {
            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.2)
                Text("正在加载记录...")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        } else if vm.records.isEmpty && !vm.isLoading {
            VStack(spacing: 20) {
                Image(systemName: "square.and.pencil")
                    .font(.system(size: 56))
                    .foregroundStyle(.blue.opacity(0.5))

                Text("还没有观察记录")
                    .font(.title3)
                    .fontWeight(.medium)

                Text("开始记录宝宝的成长瞬间")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                Button("创建记录") {
                    showCreateSheet = true
                }
                .buttonStyle(.borderedProminent)
            }
        } else {
            VStack(spacing: 0) {
                // 过滤栏
                filterBar(vm)

                // 记录列表
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(vm.records) { record in
                            recordCard(record)
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
                    .padding()
                }
                .refreshable {
                    await vm.refresh()
                }
            }
        }
    }

    // MARK: - Filter Bar

    private func filterBar(_ vm: RecordViewModel) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(filterOptions, id: \.2) { (filter, label, _) in
                    let isActive = vm.selectedFilter == filter
                    Button {
                        Task { await vm.applyFilter(filter) }
                    } label: {
                        Text(label)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .background(
                                Capsule()
                                    .fill(isActive ? Color.blue : Color.gray.opacity(0.1))
                            )
                            .foregroundStyle(isActive ? .white : .primary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 8)
        }
    }

    // MARK: - Record Card

    private func recordCard(_ record: RecordResponse) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: recordIcon(record.type))
                    .foregroundStyle(recordIconColor(record.type))

                Text(RecordType(rawValue: record.type)?.displayName ?? record.type)
                    .font(.subheadline)
                    .fontWeight(.medium)

                Spacer()

                Text(record.createdAt, style: .relative)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            // 来源关联标注
            if record.sourcePlanId != nil || record.sourceSessionId != nil {
                HStack(spacing: 6) {
                    Image(systemName: "link")
                        .font(.caption2)
                    if record.sourceSessionId != nil {
                        Text("来自即时求助")
                            .font(.caption2)
                    } else {
                        Text("来自计划任务")
                            .font(.caption2)
                    }
                    if record.syncedToPlan {
                        Text("· 已同步到计划页，影响本周判断")
                            .font(.caption2)
                    }
                }
                .foregroundStyle(.blue.opacity(0.7))
            }

            // 标签
            if let tags = record.tags, !tags.isEmpty {
                HStack(spacing: 6) {
                    ForEach(tags, id: \.self) { tag in
                        Text(tag)
                            .font(.caption2)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.blue.opacity(0.1))
                            .foregroundStyle(.blue)
                            .clipShape(Capsule())
                    }
                }
            }

            // 内容
            if let content = record.content, !content.isEmpty {
                Text(content)
                    .font(.body)
                    .lineLimit(3)
            }

            // 场景 + 时段
            HStack(spacing: 12) {
                if let scene = record.scene {
                    Label(scene, systemImage: "mappin")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let timeOfDay = record.timeOfDay {
                    Label(timeOfDay, systemImage: "clock")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.background)
                .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
        )
    }

    private func recordIcon(_ type: String) -> String {
        switch type {
        case "quick_check": return "checkmark.circle.fill"
        case "voice": return "mic.circle.fill"
        default: return "doc.text.fill"
        }
    }

    private func recordIconColor(_ type: String) -> Color {
        switch type {
        case "quick_check": return .green
        case "voice": return .purple
        default: return .blue
        }
    }
}
