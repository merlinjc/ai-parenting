import SwiftUI

/// 首页视图
///
/// 展示 child 信息卡、今日任务卡、最近记录、未读角标、周反馈状态提示。
/// 支持下拉刷新。周反馈横幅绑定 NavigationLink 到 FeedbackView。
/// 右上角显示 Profile 入口。
public struct HomeView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var viewModel: HomeViewModel?
    @State private var showProfile = false
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
            VStack(spacing: 16) {
                ProgressView()
                    .scaleEffect(1.2)
                Text("正在加载首页...")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
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
                    // 儿童信息区
                    if let child = vm.child {
                        childInfoCard(child, unreadCount: vm.unreadCount)
                    }

                    // 周反馈提示（修复：绑定 NavigationLink）
                    if vm.hasWeeklyFeedbackReady {
                        weeklyFeedbackBanner(vm)
                    }

                    // 今日任务卡片（点击跳转到计划页查看完整详情）
                    if let task = vm.todayTask {
                        NavigationLink {
                            PlanDetailView(childId: childId)
                        } label: {
                            todayTaskCard(task)
                        }
                        .buttonStyle(.plain)
                    }

                    // 最近记录
                    if !vm.recentRecords.isEmpty {
                        recentRecordsSection(vm.recentRecords)
                    }
                }
                .padding()
            }
            .refreshable {
                await vm.refresh()
            }
        }
    }

    // MARK: - Child Info Card

    private func childInfoCard(_ child: ChildResponse, unreadCount: Int) -> some View {
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

                    Text(child.stage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Spacer()

            // 消息角标
            ZStack(alignment: .topTrailing) {
                Image(systemName: "bell.fill")
                    .font(.title3)
                    .foregroundStyle(.secondary)

                if unreadCount > 0 {
                    Text(unreadCount > 99 ? "99+" : "\(unreadCount)")
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
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
    }

    // MARK: - Weekly Feedback Banner (修复：绑定 NavigationLink)

    private func weeklyFeedbackBanner(_ vm: HomeViewModel) -> some View {
        NavigationLink {
            FeedbackView(
                feedbackId: vm.weeklyFeedbackId,
                planId: vm.activePlan?.id
            )
        } label: {
            HStack {
                Image(systemName: "chart.bar.doc.horizontal.fill")
                    .foregroundStyle(.orange)
                Text("本周反馈已生成，点击查看")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundStyle(.primary)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(
                        LinearGradient(
                            colors: [.orange.opacity(0.1), .yellow.opacity(0.1)],
                            startPoint: .leading,
                            endPoint: .trailing
                        )
                    )
            )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Today Task Card

    private func todayTaskCard(_ task: DayTaskResponse) -> some View {
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

            Text(task.mainExerciseTitle)
                .font(.body)
                .fontWeight(.medium)

            Text(task.mainExerciseDescription)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .lineLimit(2)

            HStack {
                statusBadge(task.completionStatus)
                Spacer()
                Image(systemName: "chevron.right")
                    .foregroundStyle(.secondary)
            }
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

    // MARK: - Recent Records

    private func recentRecordsSection(_ records: [RecordResponse]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("最近记录")
                .font(.headline)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(records) { record in
                        recordCard(record)
                    }
                }
            }
        }
    }

    private func recordCard(_ record: RecordResponse) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: record.type == "quick_check" ? "checkmark.circle" : "note.text")
                    .foregroundStyle(.blue)
                Text(record.type == "quick_check" ? "快检" : "事件")
                    .font(.caption)
                    .fontWeight(.medium)
            }

            if let content = record.content {
                Text(content)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Text(record.createdAt, style: .relative)
                .font(.caption2)
                .foregroundStyle(.tertiary)
        }
        .frame(width: 140)
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(.background)
                .shadow(color: .black.opacity(0.04), radius: 4, y: 2)
        )
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
