import SwiftUI

/// 创建儿童档案视图
///
/// 表单包含：昵称、出生年月、关注主题、风险层级。
/// 提交后调用 API 创建并回调通知父视图。
public struct ChildCreateView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(\.dismiss) private var dismiss

    @State private var nickname = ""
    @State private var birthYear = Calendar.current.component(.year, from: Date()) - 2
    @State private var birthMonth = Calendar.current.component(.month, from: Date())
    @State private var selectedThemes: Set<FocusTheme> = []
    @State private var riskLevel: RiskLevel = .normal
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    public var onCreated: ((ChildResponse) -> Void)?

    public init(onCreated: ((ChildResponse) -> Void)? = nil) {
        self.onCreated = onCreated
    }

    public var body: some View {
        NavigationStack {
            Form {
                basicInfoSection
                focusThemeSection
                riskSection
                errorSection
            }
            .navigationTitle("添加儿童")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    saveButton
                }
            }
        }
    }

    // MARK: - Basic Info Section

    private var basicInfoSection: some View {
        Section("基本信息") {
            TextField("孩子的昵称", text: $nickname)

            HStack {
                Text("出生年月")
                Spacer()
                yearPicker
                monthPicker
            }
        }
    }

    private var yearPicker: some View {
        Picker("年", selection: $birthYear) {
            let currentYear = Calendar.current.component(.year, from: Date())
            ForEach((currentYear - 4)...(currentYear - 1), id: \.self) { year in
                Text("\(String(year))年").tag(year)
            }
        }
        .pickerStyle(.menu)
    }

    private var monthPicker: some View {
        Picker("月", selection: $birthMonth) {
            ForEach(1...12, id: \.self) { month in
                Text("\(month)月").tag(month)
            }
        }
        .pickerStyle(.menu)
    }

    // MARK: - Focus Theme Section

    private var focusThemeSection: some View {
        Section("关注方向") {
            themeGrid
                .padding(.vertical, 4)
        }
    }

    private var themeGrid: some View {
        let columns = [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())]
        return LazyVGrid(columns: columns, spacing: 10) {
            ForEach(FocusTheme.allCases, id: \.rawValue) { theme in
                themeButton(theme)
            }
        }
    }

    private func themeButton(_ theme: FocusTheme) -> some View {
        let isSelected = selectedThemes.contains(theme)
        return Button {
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
                .background(isSelected ? Color.appPrimary.opacity(0.15) : Color.gray.opacity(0.08))
                .foregroundStyle(isSelected ? Color.appPrimary : Color.primary)
                .clipShape(Capsule())
                .overlay(
                    Capsule()
                        .stroke(isSelected ? Color.appPrimary : Color.clear, lineWidth: 1.5)
                )
        }
        .buttonStyle(.plain)
    }

    // MARK: - Risk Section

    private var riskSection: some View {
        Section("风险评估") {
            Picker("风险层级", selection: $riskLevel) {
                ForEach(RiskLevel.allCases, id: \.rawValue) { level in
                    Text(level.displayName).tag(level)
                }
            }
        }
    }

    // MARK: - Error Section

    @ViewBuilder
    private var errorSection: some View {
        if let errorMessage {
            Section {
                Text(errorMessage)
                    .foregroundStyle(.red)
                    .font(.caption)
            }
        }
    }

    // MARK: - Save Button

    private var saveButton: some View {
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

    // MARK: - Submit

    @MainActor
    private func submit() async {
        isSubmitting = true
        errorMessage = nil

        let birthYearMonth = String(format: "%04d-%02d", birthYear, birthMonth)
        let data = ChildCreate(
            nickname: nickname.trimmingCharacters(in: .whitespaces),
            birthYearMonth: birthYearMonth,
            focusThemes: selectedThemes.map(\.rawValue),
            riskLevel: riskLevel.rawValue
        )

        do {
            let child: ChildResponse = try await apiClient.request(.createChild(data))
            onCreated?(child)
        } catch {
            errorMessage = error.localizedDescription
        }

        isSubmitting = false
    }
}
