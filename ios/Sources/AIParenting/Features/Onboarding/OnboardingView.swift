import SwiftUI

/// 首次使用引导流程
///
/// 对应低保真原型的"进入层"：4步引导
/// Step 1: 欢迎 + 角色选择
/// Step 2: 儿童基础信息（昵称、出生年月）
/// Step 3: 初始关注主题选择
/// Step 4: 确认并进入
///
/// 完成后创建儿童档案、调用 completeOnboarding、刷新 AppState。
public struct OnboardingView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(AppState.self) private var appState

    @State private var currentStep = 0
    @State private var caregiverRole = ""
    @State private var childNickname = ""
    @State private var birthYear = Calendar.current.component(.year, from: Date()) - 2
    @State private var birthMonth = Calendar.current.component(.month, from: Date())
    @State private var selectedThemes: Set<FocusTheme> = []
    @State private var recentSituation = ""
    @State private var isSubmitting = false
    @State private var errorMessage: String?

    private let totalSteps = 4

    public init() {}

    public var body: some View {
        VStack(spacing: 0) {
            // 进度条
            progressBar

            // 内容区
            TabView(selection: $currentStep) {
                welcomeStep.tag(0)
                childInfoStep.tag(1)
                focusThemeStep.tag(2)
                confirmStep.tag(3)
            }
            .tabViewStyle(.page(indexDisplayMode: .never))
            .animation(.easeInOut, value: currentStep)

            // 底部按钮
            bottomActions
        }
        .background(Color.appBackground)
    }

    // MARK: - Progress Bar

    private var progressBar: some View {
        HStack(spacing: 6) {
            ForEach(0..<totalSteps, id: \.self) { step in
                Capsule()
                    .fill(step <= currentStep ? Color.appPrimary : Color.appPrimary.opacity(0.15))
                    .frame(height: 4)
            }
        }
        .padding(.horizontal, 24)
        .padding(.top, 60)
        .padding(.bottom, 8)
    }

    // MARK: - Step 1: Welcome

    private var welcomeStep: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "figure.and.child.holdinghands")
                .font(.system(size: 72))
                .foregroundStyle(
                    LinearGradient(
                        colors: [Color.appPrimary, Color.appSecondary],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )

            Text("欢迎来到 AI Parenting")
                .font(.title)
                .fontWeight(.bold)

            Text("我们帮助 18-48 个月幼儿的家长，通过每周微计划和观察记录，让养育更有方向感。")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            VStack(alignment: .leading, spacing: 12) {
                Text("您是孩子的：")
                    .font(.headline)
                    .padding(.horizontal)

                let roles: [(String, String, String)] = [
                    ("mother", "妈妈", "figure.stand.dress"),
                    ("father", "爸爸", "figure.stand"),
                    ("grandparent", "祖辈", "figure.2"),
                    ("other", "其他照护者", "person.fill")
                ]

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                    ForEach(roles, id: \.0) { role in
                        Button {
                            caregiverRole = role.0
                        } label: {
                            VStack(spacing: 8) {
                                Image(systemName: role.2)
                                    .font(.title2)
                                Text(role.1)
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(caregiverRole == role.0 ? Color.appPrimary.opacity(0.12) : Color.appSurface)
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .stroke(caregiverRole == role.0 ? Color.appPrimary : Color.clear, lineWidth: 2)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal)
            }

            Spacer()
        }
    }

    // MARK: - Step 2: Child Info

    private var childInfoStep: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "person.crop.circle.badge.plus")
                .font(.system(size: 56))
                .foregroundStyle(Color.appPrimary)

            Text("建立儿童档案")
                .font(.title2)
                .fontWeight(.bold)

            Text("告诉我们孩子的基本信息，用于个性化推荐")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            VStack(spacing: 16) {
                // 昵称
                VStack(alignment: .leading, spacing: 6) {
                    Text("孩子的昵称")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    TextField("例如：小北", text: $childNickname)
                        .textFieldStyle(.roundedBorder)
                        .font(.body)
                }

                // 出生年月
                VStack(alignment: .leading, spacing: 6) {
                    Text("出生年月")
                        .font(.subheadline)
                        .fontWeight(.medium)

                    HStack(spacing: 12) {
                        Picker("年", selection: $birthYear) {
                            let currentYear = Calendar.current.component(.year, from: Date())
                            ForEach((currentYear - 4)...(currentYear - 1), id: \.self) { year in
                                Text("\(String(year))年").tag(year)
                            }
                        }
                        .pickerStyle(.menu)

                        Picker("月", selection: $birthMonth) {
                            ForEach(1...12, id: \.self) { month in
                                Text("\(month)月").tag(month)
                            }
                        }
                        .pickerStyle(.menu)
                    }
                }

                // 月龄提示
                let ageMonths = computeAgeMonths()
                if ageMonths >= 18 && ageMonths <= 48 {
                    Text("约 \(ageMonths) 个月")
                        .font(.caption)
                        .foregroundStyle(Color.appPrimary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(Color.appPrimary.opacity(0.1))
                        .clipShape(Capsule())
                } else if ageMonths > 0 {
                    Text("建议年龄范围为 18-48 个月")
                        .font(.caption)
                        .foregroundStyle(Color.appWarning)
                }
            }
            .padding(.horizontal, 24)

            Spacer()
        }
    }

    // MARK: - Step 3: Focus Themes

    private var focusThemeStep: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "sparkle.magnifyingglass")
                .font(.system(size: 56))
                .foregroundStyle(Color.appPrimary)

            Text("当前关注方向")
                .font(.title2)
                .fontWeight(.bold)

            Text("选择您目前最想关注的发展领域（可多选）")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                ForEach(FocusTheme.allCases, id: \.rawValue) { theme in
                    Button {
                        if selectedThemes.contains(theme) {
                            selectedThemes.remove(theme)
                        } else {
                            selectedThemes.insert(theme)
                        }
                    } label: {
                        VStack(spacing: 8) {
                            Image(systemName: themeIcon(theme))
                                .font(.title2)
                            Text(theme.displayName)
                                .font(.subheadline)
                                .fontWeight(.medium)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(selectedThemes.contains(theme) ? Color.appPrimary.opacity(0.12) : Color.appSurface)
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(selectedThemes.contains(theme) ? Color.appPrimary : Color.clear, lineWidth: 2)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 24)

            // 近况描述（可选）
            VStack(alignment: .leading, spacing: 8) {
                Text("近况一句话（可选）")
                    .font(.subheadline)
                    .fontWeight(.medium)

                Text("简单描述孩子最近的状态，帮助 AI 生成更贴合的第一份计划")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                TextField("例如：最近开始对同龄小朋友感兴趣了", text: $recentSituation, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .lineLimit(2...4)
                    .font(.body)
            }
            .padding(.horizontal, 24)

            Spacer()
        }
    }

    // MARK: - Step 4: Confirm

    private var confirmStep: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "checkmark.seal.fill")
                .font(.system(size: 56))
                .foregroundStyle(Color.appSuccess)

            Text("准备就绪")
                .font(.title2)
                .fontWeight(.bold)

            Text("确认信息后，我们将为 \(childNickname.isEmpty ? "您的孩子" : childNickname) 生成第一份微计划")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            VStack(alignment: .leading, spacing: 12) {
                confirmRow(label: "照护角色", value: roleDisplayName(caregiverRole))
                confirmRow(label: "孩子昵称", value: childNickname.isEmpty ? "未填写" : childNickname)
                confirmRow(label: "出生年月", value: "\(birthYear)年\(birthMonth)月")
                confirmRow(label: "月龄", value: "约 \(computeAgeMonths()) 个月")
                confirmRow(label: "关注方向", value: selectedThemes.isEmpty ? "未选择" : selectedThemes.map(\.displayName).joined(separator: "、"))
                if !recentSituation.trimmingCharacters(in: .whitespaces).isEmpty {
                    confirmRow(label: "近况", value: recentSituation.trimmingCharacters(in: .whitespaces))
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.appSurface)
                    .shadow(color: .black.opacity(0.05), radius: 8, y: 4)
            )
            .padding(.horizontal, 24)

            if let errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(Color.appError)
                    .padding(.horizontal)
            }

            Spacer()
        }
    }

    // MARK: - Bottom Actions

    private var bottomActions: some View {
        HStack(spacing: 16) {
            if currentStep > 0 {
                Button("上一步") {
                    withAnimation { currentStep -= 1 }
                }
                .buttonStyle(.bordered)
            }

            Spacer()

            if currentStep < totalSteps - 1 {
                Button("下一步") {
                    withAnimation { currentStep += 1 }
                }
                .buttonStyle(.borderedProminent)
                .disabled(!canProceed)
            } else {
                Button {
                    Task { await submitOnboarding() }
                } label: {
                    if isSubmitting {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("进入首页")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isSubmitting || !canProceed)
            }
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
        .background(.ultraThinMaterial)
    }

    // MARK: - Validation

    private var canProceed: Bool {
        switch currentStep {
        case 0: return !caregiverRole.isEmpty
        case 1: return !childNickname.trimmingCharacters(in: .whitespaces).isEmpty
        case 2: return true // themes optional
        case 3: return !childNickname.trimmingCharacters(in: .whitespaces).isEmpty
        default: return true
        }
    }

    // MARK: - Submit

    @MainActor
    private func submitOnboarding() async {
        isSubmitting = true
        errorMessage = nil

        do {
            // 1. 更新用户 Profile（角色）
            if !caregiverRole.isEmpty {
                let _: UserProfileResponse = try await apiClient.request(
                    .updateProfile(UserProfileUpdate(caregiverRole: caregiverRole))
                )
            }

            // 2. 创建儿童档案
            let birthYearMonth = String(format: "%04d-%02d", birthYear, birthMonth)
            let childCreate = ChildCreate(
                nickname: childNickname.trimmingCharacters(in: .whitespaces),
                birthYearMonth: birthYearMonth,
                focusThemes: selectedThemes.map(\.rawValue),
                riskLevel: "normal"
            )
            let child: ChildResponse = try await apiClient.request(.createChild(childCreate))

            // 3. 完成引导标记
            let _: ChildResponse = try await apiClient.request(.completeOnboarding(child.id))

            // 4. 刷新 AppState
            await appState.refreshChildren()

            // 5. 自动生成首份计划（静默失败，不阻塞引导完成）
            Task {
                do {
                    let _: PlanResponse = try await apiClient.request(.createPlan(childId: child.id))
                } catch {
                    // 静默失败：首份计划生成失败不影响引导流程
                    // 用户后续可在首页手动触发
                    print("[Onboarding] Auto-plan generation failed: \(error)")
                }
            }

        } catch let apiError as APIError {
            errorMessage = apiError.localizedDescription
        } catch {
            errorMessage = error.localizedDescription
        }

        isSubmitting = false
    }

    // MARK: - Helpers

    private func computeAgeMonths() -> Int {
        let now = Date()
        let calendar = Calendar.current
        let currentYear = calendar.component(.year, from: now)
        let currentMonth = calendar.component(.month, from: now)
        return (currentYear - birthYear) * 12 + (currentMonth - birthMonth)
    }

    private func roleDisplayName(_ role: String) -> String {
        switch role {
        case "mother": return "妈妈"
        case "father": return "爸爸"
        case "grandparent": return "祖辈"
        case "other": return "其他照护者"
        default: return "未选择"
        }
    }

    private func themeIcon(_ theme: FocusTheme) -> String {
        switch theme {
        case .language: return "mouth.fill"
        case .social: return "person.2.fill"
        case .emotion: return "heart.fill"
        case .motor: return "figure.run"
        case .cognition: return "brain.head.profile"
        case .selfCare: return "hands.sparkles.fill"
        }
    }

    private func confirmRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
        }
    }
}
