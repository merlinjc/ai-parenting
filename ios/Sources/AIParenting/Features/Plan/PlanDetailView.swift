import SwiftUI

/// 计划详情视图
///
/// 7 天任务日历视图 + 完成率进度 + 日任务列表。
public struct PlanDetailView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var viewModel: PlanViewModel?
    @State private var selectedDay: Int = 1
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
            }
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
                            onUpdateStatus: { status in
                                Task { await vm.updateCompletion(dayNumber: task.dayNumber, status: status) }
                            }
                        )
                    }
                }
                .padding()
            }
            .refreshable {
                await vm.loadActivePlan()
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
                    Label(plan.focusTheme, systemImage: "target")
                        .font(.caption)
                        .foregroundStyle(.blue)
                    Text("第 \(plan.currentDay)/7 天")
                        .font(.caption)
                        .foregroundStyle(.secondary)
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
}
