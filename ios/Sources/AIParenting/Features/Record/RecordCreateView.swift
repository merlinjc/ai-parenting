import SwiftUI

/// 创建记录视图
///
/// 类型选择（快检/事件）、标签选择、内容输入、场景和时段标注。
public struct RecordCreateView: View {

    public let childId: UUID
    public let viewModel: RecordViewModel
    public let onDismiss: () -> Void

    @State private var recordType: RecordType = .quickCheck
    @State private var content = ""
    @State private var selectedTags: Set<String> = []
    @State private var scene = ""
    @State private var timeOfDay = ""

    private let tagOptions = ["语言", "社交", "情绪", "运动", "认知", "自理", "进步", "困难"]
    private let sceneOptions = ["家中", "户外", "学校", "游乐场", "其他"]
    private let timeOptions = ["早晨", "上午", "中午", "下午", "傍晚", "晚上"]

    public init(childId: UUID, viewModel: RecordViewModel, onDismiss: @escaping () -> Void) {
        self.childId = childId
        self.viewModel = viewModel
        self.onDismiss = onDismiss
    }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
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

                        TextEditor(text: $content)
                            .frame(minHeight: 120)
                            .padding(8)
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
            timeOfDay: timeOfDay.isEmpty ? nil : timeOfDay
        )
        let success = await viewModel.createRecord(create)
        if success {
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
