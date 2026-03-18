import SwiftUI

/// 创建记录视图
///
/// 类型选择（快检/事件）、标签选择、内容输入、场景和时段标注。
/// 支持从计划页或即时求助携带来源 ID 建立证据链。
/// 支持快速打点区域（联动 Plan 的 observationCandidates）。
public struct RecordCreateView: View {

    public let childId: UUID
    public let viewModel: RecordViewModel
    public let onDismiss: () -> Void

    /// 来源计划 ID（从计划页"去记录"桥梁传入）
    public var sourcePlanId: UUID?
    /// 来源 AI 会话 ID（从即时求助"补记为记录"传入）
    public var sourceSessionId: UUID?
    /// 预填的关注主题（从计划页传入）
    public var prefillTheme: String?
    /// 快速打点候选项（联动 Plan 的 observationCandidates）
    public var observationCandidates: [ObservationCandidateItem]

    @State private var recordType: RecordType = .quickCheck
    @State private var content = ""
    @State private var selectedTags: Set<String> = []
    @State private var scene = ""
    @State private var timeOfDay = ""
    @State private var selectedCandidates: Set<String> = []
    @State private var showSaveSuccess = false

    private let tagOptions = ["语言", "社交", "情绪", "运动", "认知", "自理", "感觉调节", "依恋安全", "进步", "困难"]
    private let sceneOptions = ["家中", "户外", "学校", "游乐场", "其他"]
    private let timeOptions = ["早晨", "上午", "中午", "下午", "傍晚", "晚上"]

    public init(
        childId: UUID,
        viewModel: RecordViewModel,
        onDismiss: @escaping () -> Void,
        sourcePlanId: UUID? = nil,
        sourceSessionId: UUID? = nil,
        prefillTheme: String? = nil,
        observationCandidates: [ObservationCandidateItem] = []
    ) {
        self.childId = childId
        self.viewModel = viewModel
        self.onDismiss = onDismiss
        self.sourcePlanId = sourcePlanId
        self.sourceSessionId = sourceSessionId
        self.prefillTheme = prefillTheme
        self.observationCandidates = observationCandidates
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // 来源关联提示
                    if sourcePlanId != nil || sourceSessionId != nil {
                        HStack(spacing: 8) {
                            Image(systemName: "link")
                                .font(.caption)
                            Text(sourceSessionId != nil ? "来自即时求助 — 记录将关联到此次求助" : "来自计划任务 — 记录将关联到本周计划")
                                .font(.caption)
                        }
                        .padding(10)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(.blue.opacity(0.08))
                        )
                        .foregroundStyle(.blue)
                    }

                    // 快速打点区域（联动 Plan 的 observationCandidates）
                    if !observationCandidates.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Label("快速打点", systemImage: "checkmark.circle")
                                    .font(.subheadline)
                                    .fontWeight(.semibold)
                                Spacer()
                                if !selectedCandidates.isEmpty {
                                    Button {
                                        Task { await quickSubmit() }
                                    } label: {
                                        Text("一键提交 (\(selectedCandidates.count))")
                                            .font(.caption)
                                            .fontWeight(.semibold)
                                            .padding(.horizontal, 12)
                                            .padding(.vertical, 6)
                                            .background(Capsule().fill(.blue))
                                            .foregroundStyle(.white)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }

                            Text("点选观察到的表现，一键提交快速记录")
                                .font(.caption)
                                .foregroundStyle(.secondary)

                            FlowLayout(spacing: 8) {
                                ForEach(observationCandidates) { candidate in
                                    let isSelected = selectedCandidates.contains(candidate.id)
                                    Button {
                                        if isSelected {
                                            selectedCandidates.remove(candidate.id)
                                        } else {
                                            selectedCandidates.insert(candidate.id)
                                        }
                                    } label: {
                                        HStack(spacing: 4) {
                                            Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                                                .font(.caption2)
                                            Text(candidate.text)
                                                .font(.caption)
                                                .fontWeight(.medium)
                                        }
                                        .padding(.horizontal, 10)
                                        .padding(.vertical, 6)
                                        .background(
                                            Capsule()
                                                .fill(isSelected ? .teal.opacity(0.15) : .gray.opacity(0.08))
                                        )
                                        .foregroundStyle(isSelected ? .teal : .primary)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                        }
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(.teal.opacity(0.03))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12)
                                        .stroke(.teal.opacity(0.15), lineWidth: 1)
                                )
                        )

                        Divider()
                            .padding(.vertical, 4)
                    }

                    // 类型选择
                    VStack(alignment: .leading, spacing: 8) {
                        Text("记录类型")
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        HStack(spacing: 12) {
                            typeButton(.quickCheck, icon: "checkmark.circle", label: "快速检查")
                            typeButton(.event, icon: "doc.text", label: "事件记录")
                        }
                    }

                    // 内容输入
                    VStack(alignment: .leading, spacing: 8) {
                        Text("记录内容")
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        ZStack(alignment: .topLeading) {
                            TextEditor(text: $content)
                                .frame(minHeight: 120)
                                .padding(8)
                                .scrollDismissesKeyboard(.interactively)

                            if content.isEmpty {
                                Text("描述一下观察到的情况...")
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
                    }

                    // 标签选择
                    VStack(alignment: .leading, spacing: 8) {
                        Text("标签")
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        FlowLayout(spacing: 8) {
                            ForEach(tagOptions, id: \.self) { tag in
                                let isSelected = selectedTags.contains(tag)
                                Button {
                                    if isSelected {
                                        selectedTags.remove(tag)
                                    } else {
                                        selectedTags.insert(tag)
                                    }
                                } label: {
                                    Text(tag)
                                        .font(.caption)
                                        .fontWeight(.medium)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 6)
                                        .background(
                                            Capsule()
                                                .fill(isSelected ? Color.blue : Color.gray.opacity(0.1))
                                        )
                                        .foregroundStyle(isSelected ? .white : .primary)
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }

                    // 场景
                    VStack(alignment: .leading, spacing: 8) {
                        Text("场景")
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(sceneOptions, id: \.self) { option in
                                    chipButton(option, isSelected: scene == option) {
                                        scene = scene == option ? "" : option
                                    }
                                }
                            }
                        }
                    }

                    // 时段
                    VStack(alignment: .leading, spacing: 8) {
                        Text("时段")
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(timeOptions, id: \.self) { option in
                                    chipButton(option, isSelected: timeOfDay == option) {
                                        timeOfDay = timeOfDay == option ? "" : option
                                    }
                                }
                            }
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("新建记录")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { onDismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task { await createRecord() }
                    } label: {
                        if viewModel.isCreating {
                            ProgressView()
                        } else {
                            Text("保存")
                                .fontWeight(.semibold)
                        }
                    }
                    .disabled(content.isEmpty || viewModel.isCreating)
                }
            }
            .overlay {
                if showSaveSuccess {
                    VStack(spacing: 12) {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 48))
                            .foregroundStyle(.green)
                        Text("保存成功")
                            .font(.headline)
                            .foregroundStyle(.primary)
                    }
                    .padding(32)
                    .background(.ultraThinMaterial)
                    .clipShape(RoundedRectangle(cornerRadius: 20))
                    .transition(.scale.combined(with: .opacity))
                }
            }
            .animation(.spring(response: 0.3), value: showSaveSuccess)
        }
    }

    // MARK: - Actions

    private func createRecord() async {
        let create = RecordCreate(
            childId: childId,
            type: recordType.rawValue,
            tags: selectedTags.isEmpty ? nil : Array(selectedTags),
            content: content.isEmpty ? nil : content,
            scene: scene.isEmpty ? nil : scene,
            timeOfDay: timeOfDay.isEmpty ? nil : timeOfDay,
            theme: prefillTheme,
            sourcePlanId: sourcePlanId,
            sourceSessionId: sourceSessionId
        )
        let success = await viewModel.createRecord(create)
        if success {
            // 触觉反馈
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.success)
            // 短暂显示成功提示后关闭
            showSaveSuccess = true
            try? await Task.sleep(nanoseconds: 600_000_000) // 0.6s
            onDismiss()
        }
    }

    /// 快速打点一键提交：将选中的候选项作为标签创建 quick_check 记录
    private func quickSubmit() async {
        let candidateTexts = observationCandidates
            .filter { selectedCandidates.contains($0.id) }
            .map { $0.text }

        let create = RecordCreate(
            childId: childId,
            type: RecordType.quickCheck.rawValue,
            tags: candidateTexts,
            content: "快速打点：\(candidateTexts.joined(separator: "、"))",
            theme: prefillTheme,
            sourcePlanId: sourcePlanId,
            sourceSessionId: sourceSessionId
        )
        let success = await viewModel.createRecord(create)
        if success {
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.success)
            showSaveSuccess = true
            try? await Task.sleep(nanoseconds: 600_000_000)
            onDismiss()
        }
    }

    // MARK: - Components

    private func typeButton(_ type: RecordType, icon: String, label: String) -> some View {
        let isSelected = recordType == type
        return Button {
            recordType = type
        } label: {
            HStack {
                Image(systemName: icon)
                Text(label)
                    .font(.subheadline)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? Color.blue.opacity(0.1) : Color.gray.opacity(0.05))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 1.5)
                    )
            )
            .foregroundStyle(isSelected ? .blue : .secondary)
        }
        .buttonStyle(.plain)
    }

    private func chipButton(_ label: String, isSelected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(label)
                .font(.caption)
                .fontWeight(.medium)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    Capsule()
                        .fill(isSelected ? Color.blue : Color.gray.opacity(0.1))
                )
                .foregroundStyle(isSelected ? .white : .primary)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Flow Layout

/// 简易 Flow Layout 用于标签自动换行
public struct FlowLayout: Layout {
    public var spacing: CGFloat

    public init(spacing: CGFloat = 8) {
        self.spacing = spacing
    }

    public func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let result = layoutSubviews(proposal: proposal, subviews: subviews)
        return result.size
    }

    public func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = layoutSubviews(proposal: proposal, subviews: subviews)
        for (index, position) in result.positions.enumerated() {
            subviews[index].place(at: CGPoint(x: bounds.minX + position.x, y: bounds.minY + position.y), proposal: .unspecified)
        }
    }

    private func layoutSubviews(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, positions: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var positions: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0

        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > maxWidth && x > 0 {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            positions.append(CGPoint(x: x, y: y))
            rowHeight = max(rowHeight, size.height)
            x += size.width + spacing
        }

        return (CGSize(width: maxWidth, height: y + rowHeight), positions)
    }
}
