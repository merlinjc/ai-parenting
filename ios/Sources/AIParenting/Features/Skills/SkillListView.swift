import SwiftUI

/// AI 能力列表页 (Phase 3 升级)
///
/// 从后端 GET /skills API 动态获取技能列表，替代硬编码数据。
/// 每个技能展示为卡片：图标 + 名称 + 一句话描述 + 开启/关闭开关。
/// 后端未注册的"即将上线"技能以灰色卡片预告。
public struct SkillListView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var remoteSkills: [SkillInfoResponse] = []
    @State private var isLoading = true
    @State private var errorMessage: String?

    /// 即将上线的技能（前端定义，后端暂未注册）
    private let comingSoonSkills: [ComingSoonItem] = [
        ComingSoonItem(
            id: "food_recommendation",
            name: "辅食推荐",
            description: "根据月龄和过敏史，推荐适合的辅食方案",
            icon: "fork.knife"
        ),
        ComingSoonItem(
            id: "language_assessment",
            name: "语言评估",
            description: "评估语言发育水平，提供针对性训练建议",
            icon: "text.bubble.fill"
        ),
    ]

    public init() {}

    public var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // 说明区
                headerSection

                if isLoading {
                    ProgressView("正在加载技能列表...")
                        .padding(.top, 40)
                } else if let error = errorMessage {
                    errorView(error)
                } else {
                    // 已上线的技能（从后端获取）
                    activeSkillsSection

                    // 即将上线（前端硬编码，过滤掉已在后端注册的）
                    comingSoonSection
                }
            }
            .padding(.vertical)
        }
        .navigationTitle("AI 能力")
        .task {
            await loadSkills()
        }
    }

    // MARK: - Header

    private var headerSection: some View {
        VStack(spacing: 8) {
            Image(systemName: "cpu")
                .font(.system(size: 36))
                .foregroundStyle(
                    LinearGradient(colors: [.blue, .purple], startPoint: .topLeading, endPoint: .bottomTrailing)
                )
            Text("AI 能力中心")
                .font(.title3)
                .fontWeight(.bold)
            Text("管理 AI 助手可以为您提供的能力模块")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if !remoteSkills.isEmpty {
                Text("\(remoteSkills.count) 个已上线")
                    .font(.caption)
                    .foregroundStyle(.blue)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(.blue.opacity(0.1)))
            }
        }
        .padding(.top, 8)
        .padding(.bottom, 4)
    }

    // MARK: - Active Skills

    private var activeSkillsSection: some View {
        VStack(spacing: 12) {
            ForEach(remoteSkills) { skill in
                skillCard(skill: skill)
            }
        }
        .padding(.horizontal)
    }

    private func skillCard(skill: SkillInfoResponse) -> some View {
        let display = SkillDisplay.from(skill)

        return HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(
                        LinearGradient(
                            colors: display.gradientColors,
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 44, height: 44)

                Image(systemName: display.sfSymbol)
                    .font(.system(size: 18))
                    .foregroundStyle(.white)
            }

            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(skill.displayName)
                        .font(.subheadline)
                        .fontWeight(.semibold)

                    Text("v\(skill.version)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal, 4)
                        .padding(.vertical, 1)
                        .background(
                            RoundedRectangle(cornerRadius: 4)
                                .fill(.secondary.opacity(0.1))
                        )
                }
                Text(skill.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer()

            // 启用状态指示
            Circle()
                .fill(skill.isEnabled ? .green : .gray.opacity(0.3))
                .frame(width: 10, height: 10)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 6, y: 3)
        )
    }

    // MARK: - Coming Soon

    private var comingSoonSection: some View {
        let filteredComingSoon = comingSoonSkills.filter { item in
            !remoteSkills.contains(where: { $0.name == item.id })
        }

        return Group {
            if !filteredComingSoon.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    Text("即将上线")
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal)

                    ForEach(filteredComingSoon) { skill in
                        comingSoonCard(skill: skill)
                    }
                    .padding(.horizontal)
                }
                .padding(.top, 8)
            }
        }
    }

    private func comingSoonCard(skill: ComingSoonItem) -> some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(.gray.opacity(0.15))
                    .frame(width: 44, height: 44)

                Image(systemName: skill.icon)
                    .font(.system(size: 18))
                    .foregroundStyle(.gray.opacity(0.5))
            }

            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(skill.name)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundStyle(.secondary)
                    Text("即将上线")
                        .font(.caption2)
                        .fontWeight(.medium)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(.orange.opacity(0.12)))
                        .foregroundStyle(.orange)
                }
                Text(skill.description)
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .lineLimit(2)
            }

            Spacer()
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(.gray.opacity(0.04))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(.gray.opacity(0.1), lineWidth: 1)
                )
        )
    }

    // MARK: - Error

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 30))
                .foregroundStyle(.orange)
            Text("加载失败")
                .font(.headline)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("重试") {
                Task { await loadSkills() }
            }
            .buttonStyle(.bordered)
        }
        .padding(.top, 40)
    }

    // MARK: - Load Data

    private func loadSkills() async {
        isLoading = true
        errorMessage = nil

        do {
            let response: SkillListResponse = try await apiClient.request(.listSkills)
            remoteSkills = response.skills
        } catch let apiError as APIError {
            errorMessage = "加载技能列表失败：\(apiError.localizedDescription)"
        } catch {
            errorMessage = "加载技能列表失败：\(error.localizedDescription)"
        }

        isLoading = false
    }
}

// MARK: - Supporting Types

/// 即将上线技能项（前端定义）
private struct ComingSoonItem: Identifiable {
    let id: String
    let name: String
    let description: String
    let icon: String
}

/// 技能展示样式映射
private struct SkillDisplay {
    let sfSymbol: String
    let gradientColors: [Color]

    static func from(_ skill: SkillInfoResponse) -> SkillDisplay {
        switch skill.name {
        case "instant_help":
            return SkillDisplay(
                sfSymbol: "bubble.left.and.text.bubble.right.fill",
                gradientColors: [.blue, .purple]
            )
        case "plan_generation":
            return SkillDisplay(
                sfSymbol: "calendar.badge.plus",
                gradientColors: [.green, .mint]
            )
        case "weekly_feedback":
            return SkillDisplay(
                sfSymbol: "chart.bar.doc.horizontal.fill",
                gradientColors: [.orange, .yellow]
            )
        case "sleep_analysis":
            return SkillDisplay(
                sfSymbol: "moon.stars.fill",
                gradientColors: [.indigo, .purple]
            )
        default:
            return SkillDisplay(
                sfSymbol: "sparkles",
                gradientColors: [.gray, .secondary]
            )
        }
    }
}
