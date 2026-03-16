import SwiftUI

/// 编辑儿童档案视图
///
/// 支持修改昵称、关注主题、风险层级。
/// 出生年月不可修改（需要通过 refresh-stage 更新月龄）。
public struct ChildEditView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(\.dismiss) private var dismiss

    public let child: ChildResponse
    public var onUpdated: (() -> Void)?

    @State private var nickname: String
    @State private var selectedThemes: Set<FocusTheme>
    @State private var riskLevel: RiskLevel
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    public init(child: ChildResponse, onUpdated: (() -> Void)? = nil) {
        self.child = child
        self.onUpdated = onUpdated
        self._nickname = State(initialValue: child.nickname)
        let themes = Set((child.focusThemes ?? []).compactMap { FocusTheme(rawValue: $0) })
        self._selectedThemes = State(initialValue: themes)
        self._riskLevel = State(initialValue: RiskLevel(rawValue: child.riskLevel) ?? .normal)
    }

    public var body: some View {
        NavigationStack {
            Form {
                Section("基本信息") {
                    TextField("孩子的昵称", text: $nickname)

                    HStack {
                        Text("出生年月")
                        Spacer()
                        Text(child.birthYearMonth)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("月龄")
                        Spacer()
                        Text("\(child.ageMonths)个月")
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("发展阶段")
                        Spacer()
                        Text(child.stage)
                            .foregroundStyle(Color.appPrimary)
                    }
                }

                Section("关注方向") {
                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                        ForEach(FocusTheme.allCases, id: \.rawValue) { theme in
                            Button {
                                if selectedThemes.contains(theme) {
                                    selectedThemes.remove(theme)
                                } else {
                                    selectedThemes.insert(theme)
                                }
                            } label: {
                                Text(theme.displayName)
                                    .font(.caption)
                                    .fontWeight(.medium)
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 8)
                                    .frame(maxWidth: .infinity)
                                    .background(selectedThemes.contains(theme) ? Color.appPrimary.opacity(0.15) : Color.gray.opacity(0.08))
                                    .foregroundStyle(selectedThemes.contains(theme) ? Color.appPrimary : Color.primary)
                                    .clipShape(Capsule())
                                    .overlay(
                                        Capsule()
                                            .stroke(selectedThemes.contains(theme) ? Color.appPrimary : Color.clear, lineWidth: 1.5)
                                    )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.vertical, 4)
                }

                Section("风险评估") {
                    Picker("风险层级", selection: $riskLevel) {
                        ForEach(RiskLevel.allCases, id: \.rawValue) { level in
                            Text(level.displayName).tag(level)
                        }
                    }
                }

                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("编辑档案")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task { await submit() }
                    } label: {
                        if isSubmitting {
                            ProgressView()
                        } else {
                            Text("保存")
                        }
                    }
                    .disabled(nickname.trimmingCharacters(in: .whitespaces).isEmpty || isSubmitting)
                }
            }
        }
    }

    @MainActor
    private func submit() async {
        isSubmitting = true
        errorMessage = nil

        let data = ChildUpdate(
            nickname: nickname.trimmingCharacters(in: .whitespaces),
            focusThemes: selectedThemes.map(\.rawValue),
            riskLevel: riskLevel.rawValue
        )

        do {
            let _: ChildResponse = try await apiClient.request(.updateChild(child.id, data))
            onUpdated?()
        } catch {
            errorMessage = error.localizedDescription
        }

        isSubmitting = false
    }
}
