import SwiftUI

/// 计划生成过渡页
///
/// 引导完成后展示此页面，让用户知道 AI 正在生成第一份计划。
/// 自动轮询计划状态，生成完成后自动跳转首页。
/// 如果超时或失败，提供手动跳转选项。
struct PlanGeneratingView: View {

    let childName: String
    let childId: UUID?
    let apiClient: APIClientProtocol
    let appState: AppState

    @State private var progress: Double = 0
    @State private var currentTipIndex = 0
    @State private var planReady = false
    @State private var showSkipButton = false
    @State private var elapsedSeconds = 0

    private let tips = [
        "正在分析 {name} 的发展阶段特点…",
        "正在匹配适合的互动场景…",
        "正在设计 7 天循序渐进的活动…",
        "正在为每天准备示范话术…",
        "正在生成观察要点…",
        "最后检查，马上就好…"
    ]

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            // 动画图标
            ZStack {
                // 外圈旋转动画
                Circle()
                    .trim(from: 0, to: 0.7)
                    .stroke(
                        LinearGradient(
                            colors: [Color.appPrimary, Color.appSecondary],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        style: StrokeStyle(lineWidth: 4, lineCap: .round)
                    )
                    .frame(width: 100, height: 100)
                    .rotationEffect(.degrees(progress * 360))
                    .animation(
                        .linear(duration: 2).repeatForever(autoreverses: false),
                        value: progress
                    )

                // 中心图标
                Image(systemName: planReady ? "checkmark.circle.fill" : "sparkles")
                    .font(.system(size: 40))
                    .foregroundStyle(
                        planReady ? Color.appSuccess :
                        LinearGradient(
                            colors: [Color.appPrimary, Color.appSecondary],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .scaleEffect(planReady ? 1.2 : 1.0)
                    .animation(.spring(response: 0.5, dampingFraction: 0.6), value: planReady)
            }

            // 标题
            VStack(spacing: 8) {
                Text(planReady ? "计划已生成！" : "正在为 \(displayName) 生成专属计划")
                    .font(.title3)
                    .fontWeight(.bold)
                    .multilineTextAlignment(.center)
                    .animation(.easeInOut, value: planReady)

                // 滚动提示文本
                Text(currentTip)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 32)
                    .animation(.easeInOut, value: currentTipIndex)
                    .id(currentTipIndex) // 触发转场动画
                    .transition(.opacity)
            }

            // 进度条
            if !planReady {
                VStack(spacing: 8) {
                    ProgressView(value: estimatedProgress)
                        .tint(Color.appPrimary)
                        .padding(.horizontal, 48)

                    Text("预计需要 30 秒左右")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }

            Spacer()

            // 底部按钮
            VStack(spacing: 12) {
                if planReady {
                    Button {
                        navigateToHome()
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: "house.fill")
                            Text("查看我的计划")
                        }
                        .font(.headline)
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(
                            RoundedRectangle(cornerRadius: 14)
                                .fill(
                                    LinearGradient(
                                        colors: [Color.appPrimary, Color.appSecondary],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                        )
                    }
                }

                if showSkipButton && !planReady {
                    Button {
                        navigateToHome()
                    } label: {
                        Text("先进入首页")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 32)
        }
        .background(Color.appBackground)
        .onAppear {
            startAnimations()
            startPolling()
        }
    }

    // MARK: - Computed

    private var displayName: String {
        childName.isEmpty ? "宝宝" : childName
    }

    private var currentTip: String {
        let tip = tips[currentTipIndex % tips.count]
        return tip.replacingOccurrences(of: "{name}", with: displayName)
    }

    /// 基于时间的估计进度（0-0.95，不到 1.0 防止误导）
    private var estimatedProgress: Double {
        if planReady { return 1.0 }
        // 30 秒内从 0 到 0.9，之后缓慢增长
        let fastPhase = min(Double(elapsedSeconds) / 30.0, 0.9)
        let slowPhase = Double(max(elapsedSeconds - 30, 0)) / 200.0
        return min(fastPhase + slowPhase, 0.95)
    }

    // MARK: - Actions

    private func startAnimations() {
        // 启动旋转
        progress = 1.0

        // 每 5 秒切换提示文本
        Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { timer in
            if planReady {
                timer.invalidate()
                return
            }
            withAnimation {
                currentTipIndex = (currentTipIndex + 1) % tips.count
            }
        }

        // 每秒更新计时器
        Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { timer in
            if planReady {
                timer.invalidate()
                return
            }
            elapsedSeconds += 1
        }

        // 15 秒后显示跳过按钮
        DispatchQueue.main.asyncAfter(deadline: .now() + 15) {
            withAnimation {
                showSkipButton = true
            }
        }
    }

    private func startPolling() {
        guard let childId = childId else { return }

        // 每 3 秒检查一次计划是否已生成
        Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { timer in
            Task { @MainActor in
                if planReady {
                    timer.invalidate()
                    return
                }
                do {
                    let summary: HomeSummaryResponse = try await apiClient.request(
                        .homeSummary(childId: childId)
                    )
                    if summary.activePlan != nil {
                        timer.invalidate()
                        withAnimation(.spring(response: 0.5, dampingFraction: 0.7)) {
                            planReady = true
                        }
                        // 自动跳转（延迟 2 秒让用户看到"已完成"状态）
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                            navigateToHome()
                        }
                    }
                } catch {
                    // 轮询失败静默忽略，继续重试
                    print("[PlanGenerating] Poll failed: \(error)")
                }

                // 60 秒超时：停止轮询，让用户手动跳转
                if elapsedSeconds >= 60 {
                    timer.invalidate()
                }
            }
        }
    }

    @MainActor
    private func navigateToHome() {
        // 刷新 AppState 并切换到首页
        Task {
            await appState.refreshChildren()
        }
    }
}
