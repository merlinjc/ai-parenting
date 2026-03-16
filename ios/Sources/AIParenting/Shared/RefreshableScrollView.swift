import SwiftUI

/// 可刷新滚动容器
///
/// 封装 .refreshable 修饰符 + 分页加载更多触发。
public struct RefreshableList<Content: View>: View {
    public let hasMore: Bool
    public let onRefresh: () async -> Void
    public let onLoadMore: () async -> Void
    @ViewBuilder public let content: () -> Content

    public init(hasMore: Bool, onRefresh: @escaping () async -> Void, onLoadMore: @escaping () async -> Void, @ViewBuilder content: @escaping () -> Content) {
        self.hasMore = hasMore
        self.onRefresh = onRefresh
        self.onLoadMore = onLoadMore
        self.content = content
    }

    public var body: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                content()

                if hasMore {
                    ProgressView()
                        .padding()
                        .task {
                            await onLoadMore()
                        }
                }
            }
            .padding()
        }
        .refreshable {
            await onRefresh()
        }
    }
}
