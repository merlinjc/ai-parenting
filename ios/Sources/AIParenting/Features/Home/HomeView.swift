import SwiftUI

/// 首页视图
///
/// 周焦点主卡（阶段+主题+风险+一句话建议）、待处理回流摘要、
/// 今日任务双栏（主练习+自然嵌入）、周反馈横幅、最近记录。
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
                    // 周焦点主卡
                    if let child = vm.child {
                        weekFocusCard(child: child, plan: vm.activePlan, vm: vm)
                    }

                    // 待处理回流摘要
                    if vm.hasPendingReturnFlow {
                        returnFlowSummaryCard(vm)
                    }

                    // 周反馈提示
                    if vm.hasWeeklyFeedbackReady {
                        weeklyFeedbackBanner(vm)
                    }

                    // 今日任务（双栏拆分）
                    if let task = vm.todayTask {
                        NavigationLink {
                            PlanDetailView(childId: childId)
                        } label: {
                            todayTaskCard(task, plan: vm.activePlan)
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

    // MARK: - Week Focus Card

    private func weekFocusCard(child: ChildResponse, plan: PlanResponse?, vm: HomeViewModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // 头部：昵称 + 月龄 + 消息角标
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

                // 消息角标
                ZStack(alignment: .topTrailing) {
                    Image(systemName: "bell.fill")
                        .font(.title3)
                        .foregroundStyle(.secondary)

                    if vm.unreadCount > 0 {
                        Text(vm.unreadCount > 99 ? "99+" : "\(vm.unreadCount)")
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

    // MARK: - Return Flow Summary Card

    private func returnFlowSummaryCard(_ vm: HomeViewModel) -> some View {
        HStack(spacing: 10) {
            Image(systemName: "arrow.uturn.backward.circle.fill")
                .font(.title3)
                .foregroundStyle(.purple)

            VStack(alignment: .leading, spacing: 2) {
                Text("待处理")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(vm.returnFlowSummary)
                    .font(.subheadline)
                    .fontWeight(.medium)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(.purple.opacity(0.06))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(.purple.opacity(0.15), lineWidth: 1)
                )
        )
    }

    // MARK: - Weekly Feedback Banner

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

    // MARK: - Today Task Card（双栏拆分）

    private func todayTaskCard(_ task: DayTaskResponse, plan: PlanResponse?) -> some View {
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

            HStack {
                statusBadge(task.completionStatus)

                if task.completionStatus == "executed", let plan = plan {
                    Text("已同步到计划页")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }

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
                Image(systemName: record.type == "quick_check" ? "checkmark.circle" : record.type == "voice" ? "mic.fill" : "note.text")
                    .foregroundStyle(.blue)
                Text(RecordType(rawValue: record.type)?.displayName ?? record.type)
                    .font(.caption)
                    .fontWeight(.medium)
            }

            if let content = record.content {
                Text(content)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            HStack(spacing: 4) {
                Text(record.createdAt, style: .relative)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)

                if record.syncedToPlan {
                    Image(systemName: "link")
                        .font(.caption2)
                        .foregroundStyle(.blue.opacity(0.6))
                }
            }
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
