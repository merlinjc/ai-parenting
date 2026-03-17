import SwiftUI

/// 即时求助视图
///
/// 场景选择、文字输入、发送按钮、AI 响应展示（结构化三步卡片 + 上下文 + 回流动作）。
public struct InstantHelpView: View {

    @Environment(APIClient.self) private var apiClient
    @State private var viewModel: InstantHelpViewModel?
    @State private var selectedScenario: String?
    @State private var inputText = ""
    public let childId: UUID
    public let planId: UUID?

    /// 回流动作：补记为记录（传回 sessionId）
    public var onRecordFromResult: ((_ sessionId: UUID) -> Void)?
    /// 回流动作：加入本周关注（传回 planId 和场景摘要）
    public var onAddToFocus: ((_ planId: UUID?, _ scenarioSummary: String) -> Void)?

    private let scenarios = [
        ("不愿说话", "speech.bubble"),
        ("情绪失控", "flame"),
        ("不配合", "hand.raised"),
        ("社交困难", "person.2"),
        ("睡眠问题", "moon.zzz"),
        ("饮食问题", "fork.knife"),
        ("其他", "ellipsis.circle"),
    ]

    public init(childId: UUID, planId: UUID?, onRecordFromResult: ((_ sessionId: UUID) -> Void)? = nil, onAddToFocus: ((_ planId: UUID?, _ scenarioSummary: String) -> Void)? = nil) {
        self.childId = childId
        self.planId = planId
        self.onRecordFromResult = onRecordFromResult
        self.onAddToFocus = onAddToFocus
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

                    ZStack(alignment: .topLeading) {
                        TextEditor(text: $inputText)
                            .frame(minHeight: 100)
                            .padding(8)
                            .scrollDismissesKeyboard(.interactively)
                            .onChange(of: inputText) { _, newValue in
                                if newValue.count > 500 {
                                    inputText = String(newValue.prefix(500))
                                }
                            }

                        if inputText.isEmpty {
                            Text("例如：孩子今天在超市突然大哭不止，怎么哄都不行...")
                                .font(.body)
                                .foregroundStyle(.tertiary)
                                .padding(.horizontal, 13)
                                .padding(.vertical, 16)
                                .allowsHitTesting(false)
                        }
                    }
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                    )

                    Text("\(inputText.count)/500")
                        .font(.caption)
                        .foregroundStyle(inputText.count >= 480 ? .orange : .secondary)
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

    // MARK: - Result View（结构化三步卡片 + 上下文 + 回流按钮）

    private func resultView(_ vm: InstantHelpViewModel) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // 降级状态标记
                if vm.isDegraded {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                        Text("AI 响应降级，以下为备用建议")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(.yellow.opacity(0.12))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(.orange.opacity(0.3), lineWidth: 1)
                            )
                    )
                }

                if let session = vm.session {
                    // 尝试解析结构化结果
                    if let parsed = session.parsedResult {
                        structuredResultView(parsed, session: session)
                    } else if vm.isDegraded, let degraded = session.parsedDegradedResult {
                        // 降级结果文本展示
                        degradedResultView(degraded, session: session)
                    } else {
                        // 兜底：无法解析时展示原始状态
                        fallbackResultView(session)
                    }

                    // 上下文透明化展示
                    if let context = session.parsedContextSnapshot {
                        contextSnapshotView(context)
                    }

                    // 回流动作按钮
                    if let parsed = session.parsedResult {
                        returnFlowButtons(parsed, sessionId: session.id)
                    }

                    // 响应耗时
                    if let latency = session.latencyMs {
                        Text("响应耗时：\(latency)ms")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                            .frame(maxWidth: .infinity, alignment: .trailing)
                    }
                }

                // 边界声明
                if let session = vm.session, let parsed = session.parsedResult {
                    Text(parsed.boundaryNote)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(.gray.opacity(0.06))
                        )
                }

                // 再次提问
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

    // MARK: - Structured Three-Step Cards

    private func structuredResultView(_ result: InstantHelpResultContent, session: AISessionResponse) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            // 场景理解摘要
            if let scenario = session.inputScenario {
                Label(scenario, systemImage: "tag")
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.blue.opacity(0.1))
                    .foregroundStyle(.blue)
                    .clipShape(Capsule())
            }

            Text(result.scenarioSummary)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            // 三步卡片（安全处理后端返回步骤数超过 3 的情况）
            let stepColors: [Color] = [.blue, .green, .orange]
            let stepIcons = ["1.circle.fill", "2.circle.fill", "3.circle.fill"]

            ForEach(Array(zip(result.steps.prefix(3).indices, result.steps.prefix(3))), id: \.0) { index, step in
                stepCard(
                    step: step,
                    index: index,
                    color: stepColors[index % stepColors.count],
                    icon: stepIcons[index % stepIcons.count],
                    label: index < InstantHelpResultContent.stepLabels.count
                        ? InstantHelpResultContent.stepLabels[index]
                        : "步骤 \(index + 1)"
                )
            }
        }
    }

    private func stepCard(step: StepContent, index: Int, color: Color, icon: String, label: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.title3)
                    .foregroundStyle(color)
                VStack(alignment: .leading, spacing: 2) {
                    Text(label)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(step.title)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                }
            }

            Text(step.body)
                .font(.body)
                .foregroundStyle(.primary)

            if let script = step.exampleScript {
                HStack(alignment: .top, spacing: 6) {
                    Image(systemName: "quote.opening")
                        .font(.caption2)
                        .foregroundStyle(color.opacity(0.6))
                    Text(script)
                        .font(.subheadline)
                        .italic()
                        .foregroundStyle(.primary.opacity(0.85))
                }
                .padding(10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(color.opacity(0.05))
                )
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(.background)
                .shadow(color: color.opacity(0.08), radius: 6, y: 3)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(color.opacity(0.15), lineWidth: 1)
        )
    }

    // MARK: - Degraded Result

    private func degradedResultView(_ degraded: DegradedResultContent, session: AISessionResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("备用建议")
                .font(.headline)

            Text(degraded.displayText)
                .font(.body)
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(.yellow.opacity(0.08))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(.yellow.opacity(0.2), lineWidth: 1)
                        )
                )
        }
    }

    // MARK: - Fallback Result

    private func fallbackResultView(_ session: AISessionResponse) -> some View {
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

            Text("AI 已生成个性化指导建议，但结果格式无法完整解析。请联系支持团队。")
                .font(.body)
                .foregroundStyle(.secondary)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(.background)
                .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
        )
    }

    // MARK: - Context Snapshot

    private func contextSnapshotView(_ context: ContextSnapshotContent) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("系统已引用的上下文", systemImage: "info.circle")
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(.secondary)

            HStack(spacing: 16) {
                contextChip(icon: "person.fill", text: "\(context.childAgeMonths)个月")
                contextChip(icon: "chart.bar.fill", text: context.stageDisplayName)
                contextChip(icon: "shield.fill", text: context.riskLevelDisplayName)
            }

            if !context.focusThemeDisplayNames.isEmpty {
                HStack(spacing: 6) {
                    Image(systemName: "tag.fill")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(context.focusThemeDisplayNames.joined(separator: "、"))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            if let day = context.activePlanDay {
                HStack(spacing: 6) {
                    Image(systemName: "calendar")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text("当前计划第 \(day) 天")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            if let keywords = context.recentRecordKeywords, !keywords.isEmpty {
                HStack(spacing: 6) {
                    Image(systemName: "note.text")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text("近期记录关键词：\(keywords.joined(separator: "、"))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(.blue.opacity(0.04))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(.blue.opacity(0.1), lineWidth: 1)
                )
        )
    }

    private func contextChip(icon: String, text: String) -> some View {
        HStack(spacing: 4) {
            Image(systemName: icon)
                .font(.caption2)
            Text(text)
                .font(.caption)
        }
        .foregroundStyle(.secondary)
    }

    // MARK: - Return Flow Buttons

    private func returnFlowButtons(_ result: InstantHelpResultContent, sessionId: UUID) -> some View {
        VStack(spacing: 10) {
            if result.suggestRecord {
                Button {
                    onRecordFromResult?(sessionId)
                } label: {
                    Label("补记为记录", systemImage: "doc.badge.plus")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 10)
                                .fill(.blue.opacity(0.08))
                        )
                        .foregroundStyle(.blue)
                }
                .buttonStyle(.plain)
            }

            if result.suggestAddFocus {
                Button {
                    onAddToFocus?(planId, result.scenarioSummary)
                } label: {
                    Label("加入本周关注", systemImage: "star.badge.plus")
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(
                            RoundedRectangle(cornerRadius: 10)
                                .fill(.orange.opacity(0.08))
                        )
                        .foregroundStyle(.orange)
                }
                .buttonStyle(.plain)
            }

            if result.suggestConsultPrep {
                NavigationLink {
                    ConsultPrepView(childId: childId, apiClient: apiClient)
                } label: {
                    VStack(spacing: 4) {
                        Label("建议查看咨询准备", systemImage: "heart.text.clipboard")
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .foregroundStyle(.red)

                        if let reason = result.consultPrepReason {
                            Text(reason)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Text("点击查看就诊准备资料 →")
                            .font(.caption2)
                            .foregroundStyle(.red.opacity(0.7))
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 10)
                            .fill(.red.opacity(0.06))
                            .overlay(
                                RoundedRectangle(cornerRadius: 10)
                                    .stroke(.red.opacity(0.2), lineWidth: 1)
                            )
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }
}
