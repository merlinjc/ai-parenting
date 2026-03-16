import SwiftUI

/// 底部 TabView 导航（首页/计划/记录/消息四个标签）
///
/// 从 AppState 获取当前活跃的 childId（替代硬编码）。
/// 首页 Tab 右下角有即时求助浮动按钮。
public struct MainTabView: View {

    @Environment(AppState.self) private var appState
    @State private var selectedTab = 0
    @State private var showInstantHelp = false

    public init() {}

    public var body: some View {
        if let childId = appState.activeChildId {
            ZStack(alignment: .bottomTrailing) {
                TabView(selection: $selectedTab) {
                    HomeView(childId: childId)
                        .tabItem {
                            Label("首页", systemImage: "house.fill")
                        }
                        .tag(0)

                    PlanDetailView(childId: childId)
                        .tabItem {
                            Label("计划", systemImage: "calendar")
                        }
                        .tag(1)

                    RecordListView(childId: childId)
                        .tabItem {
                            Label("记录", systemImage: "square.and.pencil")
                        }
                        .tag(2)

                    MessageListView()
                        .tabItem {
                            Label("消息", systemImage: "bell.fill")
                        }
                        .tag(3)
                }

                // 即时求助浮动按钮（仅首页 Tab 显示）
                if selectedTab == 0 {
                    Button {
                        showInstantHelp = true
                    } label: {
                        Image(systemName: "questionmark.circle.fill")
                            .font(.system(size: 24))
                            .foregroundStyle(.white)
                            .frame(width: 56, height: 56)
                            .background(
                                LinearGradient(
                                    colors: [Color.appPrimary, Color.appSecondary],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .clipShape(Circle())
                            .shadow(color: Color.appPrimary.opacity(0.4), radius: 8, y: 4)
                    }
                    .padding(.trailing, 20)
                    .padding(.bottom, 80)
                }
            }
            .sheet(isPresented: $showInstantHelp) {
                InstantHelpView(childId: childId, planId: nil)
            }
        } else {
            // 无活跃儿童（不应该出现，因为 RootView 会路由到 Onboarding）
            EmptyStateView(
                icon: "person.crop.circle.badge.plus",
                title: "还没有儿童档案",
                description: "请先添加一个儿童档案以开始使用"
            )
        }
    }
}
