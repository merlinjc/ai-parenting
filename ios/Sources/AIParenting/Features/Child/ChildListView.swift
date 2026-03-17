import SwiftUI

/// 儿童档案列表与管理页面
///
/// 展示当前用户下的所有儿童档案，支持：
/// - 查看儿童基本信息（昵称、月龄、阶段、关注主题）
/// - 切换活跃儿童
/// - 新增儿童档案
/// - 编辑儿童档案
public struct ChildListView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(AppState.self) private var appState
    @State private var viewModel: ChildViewModel?
    @State private var showCreateSheet = false
    @State private var editingChild: ChildResponse?
    @State private var switchToast: String?
    @State private var showSwitchToast = false

    public init() {}

    public var body: some View {
        NavigationStack {
            Group {
                if let vm = viewModel {
                    childListContent(vm)
                } else {
                    ProgressView("加载中...")
                }
            }
            .navigationTitle("儿童档案")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        showCreateSheet = true
                    } label: {
                        Image(systemName: "plus.circle.fill")
                    }
                }
            }
            .sheet(isPresented: $showCreateSheet) {
                ChildCreateView { newChild in
                    showCreateSheet = false
                    Task {
                        await appState.refreshChildren()
                        await viewModel?.loadChildren()
                    }
                }
            }
            .sheet(item: $editingChild) { child in
                ChildEditView(child: child) {
                    editingChild = nil
                    Task {
                        await appState.refreshChildren()
                        await viewModel?.loadChildren()
                    }
                }
            }
            .task {
                if viewModel == nil {
                    let vm = ChildViewModel(apiClient: apiClient)
                    viewModel = vm
                    await vm.loadChildren()
                }
            }
            .overlay(alignment: .top) {
                if showSwitchToast, let message = switchToast {
                    Text(message)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.white)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 10)
                        .background(
                            Capsule()
                                .fill(Color.appPrimary)
                                .shadow(color: .black.opacity(0.1), radius: 8, y: 4)
                        )
                        .transition(.move(edge: .top).combined(with: .opacity))
                        .padding(.top, 8)
                }
            }
            .animation(.easeInOut(duration: 0.3), value: showSwitchToast)
        }
    }

    @ViewBuilder
    private func childListContent(_ vm: ChildViewModel) -> some View {
        if vm.isLoading && vm.children.isEmpty {
            ProgressView()
        } else if let error = vm.error, vm.children.isEmpty {
            EmptyStateView(
                icon: "exclamationmark.triangle",
                title: "加载失败",
                description: error.localizedDescription,
                actionTitle: "重试"
            ) {
                Task { await vm.loadChildren() }
            }
        } else if vm.children.isEmpty {
            EmptyStateView(
                icon: "person.crop.circle.badge.plus",
                title: "还没有儿童档案",
                description: "点击右上角添加第一个儿童档案",
                actionTitle: "添加儿童"
            ) {
                showCreateSheet = true
            }
        } else {
            List {
                ForEach(vm.children) { child in
                    childRow(child)
                        .contentShape(Rectangle())
                        .onTapGesture {
                            if child.id != appState.activeChildId {
                                appState.setActiveChild(child)
                                let generator = UIImpactFeedbackGenerator(style: .medium)
                                generator.impactOccurred()
                                switchToast = "已切换到 \(child.nickname)"
                                showSwitchToast = true
                                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                    showSwitchToast = false
                                }
                            }
                        }
                }
            }
            .refreshable {
                await vm.loadChildren()
            }
        }
    }

    private func childRow(_ child: ChildResponse) -> some View {
        HStack(spacing: 14) {
            // 头像
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color.appPrimary.opacity(0.2), Color.appSecondary.opacity(0.15)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 48, height: 48)

                Text(String(child.nickname.prefix(1)))
                    .font(.title3)
                    .fontWeight(.medium)
                    .foregroundStyle(Color.appPrimary)
            }

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(child.nickname)
                        .font(.body)
                        .fontWeight(.semibold)

                    if child.id == appState.activeChildId {
                        Text("当前")
                            .font(.caption2)
                            .fontWeight(.medium)
                            .foregroundStyle(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.appPrimary)
                            .clipShape(Capsule())
                    }
                }

                HStack(spacing: 8) {
                    Text("\(child.ageMonths)个月")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    Text(child.stage)
                        .font(.caption)
                        .foregroundStyle(Color.appPrimary)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 1)
                        .background(Color.appPrimary.opacity(0.1))
                        .clipShape(Capsule())
                }

                if let themes = child.focusThemes, !themes.isEmpty {
                    HStack(spacing: 4) {
                        ForEach(themes, id: \.self) { theme in
                            Text(FocusTheme(rawValue: theme)?.displayName ?? theme)
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.appAccent.opacity(0.1))
                                .foregroundStyle(Color.appAccent)
                                .clipShape(Capsule())
                        }
                    }
                }
            }

            Spacer()

            Button {
                editingChild = child
            } label: {
                Image(systemName: "pencil.circle")
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.vertical, 4)
    }
}
