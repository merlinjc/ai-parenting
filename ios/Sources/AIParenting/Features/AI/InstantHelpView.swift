import SwiftUI

/// 即时求助视图
///
/// 场景选择、文字输入、发送按钮、AI 响应展示（含降级结果）、加载动画。
public struct InstantHelpView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var viewModel: InstantHelpViewModel?
    @State private var selectedScenario: String?
    @State private var inputText = ""
    public let childId: UUID
    public let planId: UUID?

    private let scenarios = [
        ("不愿说话", "speech.bubble"),
        ("情绪失控", "flame"),
        ("不配合", "hand.raised"),
        ("社交困难", "person.2"),
        ("睡眠问题", "moon.zzz"),
        ("饮食问题", "fork.knife"),
        ("其他", "ellipsis.circle"),
    ]

    public init(childId: UUID, planId: UUID?) {
        self.childId = childId
        self.planId = planId
    }

    public var body: some View {
        NavigationStack {
            Group {
                if let vm = viewModel {
                    helpContent(vm)
                } else {
                    ProgressView()
                }
            }
            .navigationTitle("即时求助")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .task {
                if viewModel == nil {
                    viewModel = InstantHelpViewModel(apiClient: apiClient)
                }
            }
        }
    }

    @ViewBuilder
    private func helpContent(_ vm: InstantHelpViewModel) -> some View {
        if vm.isLoading {
            // 等待 AI 响应
            VStack(spacing: 24) {
                ProgressView()
                    .scaleEffect(1.5)
                    .tint(.blue)

                Text("AI 正在思考...")
                    .font(.title3)
                    .fontWeight(.medium)

                Text("正在分析场景并生成个性化建议，请稍候")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                Text("通常需要 10-30 秒")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(40)
        } else if vm.hasResult {
            // 显示结果
            resultView(vm)
        } else {
            // 输入界面
            inputView(vm)
        }
    }

    // MARK: - Input View

    private func inputView(_ vm: InstantHelpViewModel) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // 场景选择
                VStack(alignment: .leading, spacing: 12) {
                    Text("遇到什么问题？")
                        .font(.headline)

                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                    ], spacing: 12) {
                        ForEach(scenarios, id: \.0) { (name, icon) in
                            let isSelected = selectedScenario == name
                            Button {
                                selectedScenario = isSelected ? nil : name
                            } label: {
                                HStack(spacing: 8) {
                                    Image(systemName: icon)
                                        .font(.body)
                                    Text(name)
                                        .font(.subheadline)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                                .background(
                                    RoundedRectangle(cornerRadius: 12)
                                        .fill(isSelected ? Color.blue.opacity(0.1) : Color.gray.opacity(0.06))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 12)
                                                .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 1.5)
                                        )
                                )
                                .foregroundStyle(isSelected ? .blue : .primary)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }

                // 文字描述
                VStack(alignment: .leading, spacing: 8) {
                    Text("描述一下具体情况")
                        .font(.headline)

                    TextEditor(text: $inputText)
                        .frame(minHeight: 100)
                        .padding(8)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                        )

                    Text("\(inputText.count)/500")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                }

                // 错误提示
                if let error = vm.error {
                    Text(error.localizedDescription)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(12)
                        .frame(maxWidth: .infinity)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(.red.opacity(0.08))
                        )
                }

                // 发送按钮
                Button {
                    Task {
                        await vm.sendHelp(
                            childId: childId,
                            scenario: selectedScenario,
                            inputText: inputText.isEmpty ? nil : inputText,
                            planId: planId
                        )
                    }
                } label: {
                    Text("获取 AI 指导")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            LinearGradient(colors: [.blue, .cyan], startPoint: .leading, endPoint: .trailing)
                        )
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                }
                .disabled(selectedScenario == nil && inputText.isEmpty)
            }
            .padding()
        }
    }

    // MARK: - Result View

    private func resultView(_ vm: InstantHelpViewModel) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // 状态标记
                if vm.isDegraded {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                        Text("AI 响应降级，以下为备用建议")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                    .padding(12)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(.orange.opacity(0.08))
                    )
                }

                // 结果内容
                if let session = vm.session {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("AI 建议")
                            .font(.title3)
                            .fontWeight(.bold)

                        if let scenario = session.inputScenario {
                            Label(scenario, systemImage: "tag")
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.blue.opacity(0.1))
                                .foregroundStyle(.blue)
                                .clipShape(Capsule())
                        }

                        // 结果文本（简化展示 AnyCodable 内容）
                        Text("AI 已生成个性化指导建议。请参考以上内容与宝宝互动。")
                            .font(.body)
                            .foregroundStyle(.secondary)

                        if let latency = session.latencyMs {
                            Text("响应耗时：\(latency)ms")
                                .font(.caption2)
                                .foregroundStyle(.tertiary)
                        }
                    }
                    .padding()
                    .background(
                        RoundedRectangle(cornerRadius: 16)
                            .fill(.background)
                            .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
                    )
                }

                // 重新提问
                Button {
                    vm.reset()
                    inputText = ""
                    selectedScenario = nil
                } label: {
                    Text("再次提问")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(Color.blue, lineWidth: 1.5)
                        )
                        .foregroundStyle(.blue)
                }
            }
            .padding()
        }
    }
}
