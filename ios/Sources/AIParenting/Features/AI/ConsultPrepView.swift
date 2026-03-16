import SwiftUI

/// 咨询准备数据模型
struct ConsultPrepData: Codable, Sendable {
    let childInfo: ConsultPrepChildInfo
    let recentRecords: [ConsultPrepRecord]
    let aiSuggestions: [ConsultPrepSuggestion]
    let checklist: [ConsultPrepCheckItem]
    let recordCount: Int
    let generatedAt: String
}

struct ConsultPrepChildInfo: Codable, Sendable {
    let nickname: String
    let ageMonths: Int
    let stage: String
    let riskLevel: String
    let focusThemes: [String]
}

struct ConsultPrepRecord: Codable, Sendable, Identifiable {
    var id: String { date }
    let date: String
    let type: String
    let content: String
    let tags: [String]
    let theme: String?
}

struct ConsultPrepSuggestion: Codable, Sendable, Identifiable {
    var id: String { date }
    let date: String
    let scenario: String?
    let reason: String
    let summary: String
}

struct ConsultPrepCheckItem: Codable, Sendable, Identifiable {
    var id: String { item }
    let item: String
    let checked: Bool
}

/// 咨询准备页面
///
/// 当 AI 建议就诊/咨询时，展示结构化的就诊准备数据：
/// - 儿童基本信息
/// - 最近观察记录摘要
/// - AI 咨询建议
/// - 就诊准备清单
struct ConsultPrepView: View {

    let childId: UUID
    let apiClient: APIClientProtocol

    @State private var data: ConsultPrepData?
    @State private var isLoading = true
    @State private var errorMessage: String?
    @State private var checkedItems: Set<String> = []

    var body: some View {
        ScrollView {
            if isLoading {
                VStack(spacing: 16) {
                    ProgressView()
                    Text("正在准备咨询资料…")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, minHeight: 300)
            } else if let errorMessage {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 40))
                        .foregroundStyle(.orange)
                    Text(errorMessage)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Button("重试") {
                        Task { await loadData() }
                    }
                    .buttonStyle(.bordered)
                }
                .frame(maxWidth: .infinity, minHeight: 300)
            } else if let data {
                contentView(data)
            }
        }
        .navigationTitle("咨询准备")
        .navigationBarTitleDisplayMode(.large)
        .task { await loadData() }
    }

    // MARK: - Content

    @ViewBuilder
    private func contentView(_ data: ConsultPrepData) -> some View {
        LazyVStack(alignment: .leading, spacing: 20) {
            // 儿童信息卡片
            childInfoCard(data.childInfo)

            // AI 咨询建议
            if !data.aiSuggestions.isEmpty {
                suggestionsSection(data.aiSuggestions)
            }

            // 最近记录摘要
            if !data.recentRecords.isEmpty {
                recordsSection(data.recentRecords)
            }

            // 就诊准备清单
            checklistSection(data.checklist)

            // 提示文字
            Text("提示：您可以截图本页面内容，在就诊时作为参考。")
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 16)
                .padding(.bottom, 20)
        }
        .padding(.top, 16)
    }

    private func childInfoCard(_ info: ConsultPrepChildInfo) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "person.fill")
                    .foregroundStyle(.tint)
                Text("儿童信息")
                    .font(.headline)
            }

            HStack(spacing: 16) {
                infoChip(label: "昵称", value: info.nickname)
                infoChip(label: "月龄", value: "\(info.ageMonths) 个月")
                infoChip(label: "关注等级", value: riskLevelText(info.riskLevel))
            }

            if !info.focusThemes.isEmpty {
                HStack {
                    Text("关注领域：")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(info.focusThemes.joined(separator: "、"))
                        .font(.caption)
                        .fontWeight(.medium)
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
        .padding(.horizontal, 16)
    }

    private func suggestionsSection(_ suggestions: [ConsultPrepSuggestion]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "heart.text.clipboard")
                    .foregroundStyle(.red)
                Text("AI 咨询建议")
                    .font(.headline)
            }
            .padding(.horizontal, 16)

            ForEach(suggestions) { suggestion in
                VStack(alignment: .leading, spacing: 6) {
                    if let scenario = suggestion.scenario {
                        Text("场景：\(scenario)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    Text(suggestion.reason)
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Text(suggestion.summary)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                }
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(.red.opacity(0.04))
                )
                .padding(.horizontal, 16)
            }
        }
    }

    private func recordsSection(_ records: [ConsultPrepRecord]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "doc.text")
                    .foregroundStyle(.blue)
                Text("最近观察记录（\(records.count) 条）")
                    .font(.headline)
            }
            .padding(.horizontal, 16)

            ForEach(records.prefix(5)) { record in
                HStack(alignment: .top, spacing: 10) {
                    Circle()
                        .fill(.blue.opacity(0.3))
                        .frame(width: 8, height: 8)
                        .padding(.top, 6)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(record.content.isEmpty ? "（无文字内容）" : record.content)
                            .font(.subheadline)
                            .lineLimit(2)
                        HStack {
                            Text(record.type)
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Capsule().fill(.blue.opacity(0.1)))
                            if let theme = record.theme {
                                Text(theme)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                .padding(.horizontal, 16)
            }
        }
    }

    private func checklistSection(_ items: [ConsultPrepCheckItem]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "checklist")
                    .foregroundStyle(.green)
                Text("就诊准备清单")
                    .font(.headline)
            }
            .padding(.horizontal, 16)

            ForEach(items) { item in
                Button {
                    if checkedItems.contains(item.item) {
                        checkedItems.remove(item.item)
                    } else {
                        checkedItems.insert(item.item)
                    }
                } label: {
                    HStack(spacing: 10) {
                        Image(systemName: checkedItems.contains(item.item) ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(checkedItems.contains(item.item) ? .green : .gray)
                        Text(item.item)
                            .font(.subheadline)
                            .strikethrough(checkedItems.contains(item.item))
                            .foregroundStyle(checkedItems.contains(item.item) ? .secondary : .primary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 8)
                    .padding(.horizontal, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(.systemBackground))
                    )
                }
                .buttonStyle(.plain)
                .padding(.horizontal, 16)
            }
        }
    }

    // MARK: - Helpers

    private func infoChip(label: String, value: String) -> some View {
        VStack(spacing: 2) {
            Text(label)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.caption)
                .fontWeight(.medium)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.secondarySystemBackground))
        )
    }

    private func riskLevelText(_ level: String) -> String {
        switch level {
        case "normal": return "正常"
        case "attention": return "关注"
        case "consult": return "建议咨询"
        default: return level
        }
    }

    // MARK: - Data Loading

    @MainActor
    private func loadData() async {
        isLoading = true
        errorMessage = nil

        do {
            let result: ConsultPrepData = try await apiClient.request(.getConsultPrep(childId: childId))
            data = result
        } catch {
            errorMessage = "加载失败，请稍后重试"
        }

        isLoading = false
    }
}
