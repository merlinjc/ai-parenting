import SwiftUI

/// 登录/注册页面
///
/// 提供邮箱+密码的登录和注册功能，登录成功后保存 JWT Token
/// 并触发 AppState 初始化。
struct LoginView: View {

    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var displayName = ""
    @State private var isRegistering = false
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var agreedToTerms = false
    @State private var showTerms = false
    @State private var showPrivacy = false

    let apiClient: APIClientProtocol
    let authProvider: JWTAuthProvider
    let onLoginSuccess: () -> Void

    /// 邮箱格式校验
    private var isValidEmail: Bool {
        let pattern = #"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"#
        return email.range(of: pattern, options: .regularExpression) != nil
    }

    /// 密码强度校验（至少 8 位）
    private var isValidPassword: Bool {
        password.count >= 8
    }

    /// 密码确认匹配
    private var passwordsMatch: Bool {
        !isRegistering || password == confirmPassword
    }

    /// 表单是否可提交
    private var canSubmit: Bool {
        if isRegistering {
            return isValidEmail && isValidPassword && passwordsMatch && agreedToTerms && !isLoading
        }
        return !email.isEmpty && !password.isEmpty && !isLoading
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                // Logo / Title
                VStack(spacing: 8) {
                    Image(systemName: "figure.and.child.holdinghands")
                        .font(.system(size: 60))
                        .foregroundStyle(.tint)
                    Text("AI 育儿助手")
                        .font(.title)
                        .fontWeight(.bold)
                    Text("科学育儿，从这里开始")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 40)

                // Form
                VStack(spacing: 16) {
                    if isRegistering {
                        TextField("昵称（选填）", text: $displayName)
                            .textFieldStyle(.roundedBorder)
                            .textContentType(.name)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        TextField("邮箱", text: $email)
                            .textFieldStyle(.roundedBorder)
                            .textContentType(.emailAddress)
                            .keyboardType(.emailAddress)
                            .autocapitalization(.none)

                        if !email.isEmpty && !isValidEmail {
                            Text("请输入有效的邮箱地址")
                                .font(.caption2)
                                .foregroundStyle(.red)
                        }
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        SecureField("密码", text: $password)
                            .textFieldStyle(.roundedBorder)
                            .textContentType(isRegistering ? .newPassword : .password)

                        if isRegistering && !password.isEmpty && !isValidPassword {
                            Text("密码至少需要 8 个字符")
                                .font(.caption2)
                                .foregroundStyle(.red)
                        }
                    }

                    if isRegistering {
                        VStack(alignment: .leading, spacing: 4) {
                            SecureField("确认密码", text: $confirmPassword)
                                .textFieldStyle(.roundedBorder)
                                .textContentType(.newPassword)

                            if !confirmPassword.isEmpty && !passwordsMatch {
                                Text("两次输入的密码不一致")
                                    .font(.caption2)
                                    .foregroundStyle(.red)
                            }
                        }
                    }
                }
                .padding(.horizontal, 32)

                // 用户协议（注册时显示）
                if isRegistering {
                    HStack(spacing: 8) {
                        Button {
                            agreedToTerms.toggle()
                        } label: {
                            Image(systemName: agreedToTerms ? "checkmark.square.fill" : "square")
                                .foregroundStyle(agreedToTerms ? .blue : .secondary)
                        }
                        .buttonStyle(.plain)

                        Text("我已阅读并同意")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Button("《用户协议》") { showTerms = true }
                            .font(.caption)

                        Text("和")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        Button("《隐私政策》") { showPrivacy = true }
                            .font(.caption)
                    }
                    .padding(.horizontal, 32)
                }

                // Error Message
                if let errorMessage {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal, 32)
                }

                // Action Buttons
                VStack(spacing: 12) {
                    Button {
                        Task { await performAuth() }
                    } label: {
                        HStack {
                            if isLoading {
                                ProgressView()
                                    .tint(.white)
                            }
                            Text(isRegistering ? "注册" : "登录")
                                .fontWeight(.semibold)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!canSubmit)
                    .padding(.horizontal, 32)

                    HStack(spacing: 16) {
                        Button {
                            withAnimation {
                                isRegistering.toggle()
                                errorMessage = nil
                                confirmPassword = ""
                                agreedToTerms = false
                            }
                        } label: {
                            Text(isRegistering ? "已有账号？去登录" : "没有账号？去注册")
                                .font(.subheadline)
                        }

                        if !isRegistering {
                            Text("·")
                                .foregroundStyle(.secondary)

                            Button {
                                // TODO: 实现忘记密码流程（发送重置邮件）
                                errorMessage = "忘记密码功能开发中，请联系客服重置"
                            } label: {
                                Text("忘记密码？")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }

                Spacer()

                #if DEBUG
                // Skip Login (Dev Mode) — 仅在 DEBUG 构建中可见
                // 注意：不清除凭证，保留可能已有的 token；如果没有 token 将回退到 X-User-Id 模式
                Button {
                    onLoginSuccess()
                } label: {
                    Text("跳过登录（开发模式）")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 20)
                #endif
            }
            .navigationBarHidden(true)
            .sheet(isPresented: $showTerms) {
                termsView(title: "用户协议", content: "AI 育儿助手用户服务协议\n\n本协议是您与 AI Parenting 之间关于使用本产品服务所订立的协议。\n\n1. 服务内容\n本产品提供基于 AI 的育儿指导建议，仅供参考，不构成医疗建议。\n\n2. 用户义务\n用户应提供真实信息，不得滥用服务。\n\n3. 免责声明\nAI 生成的建议仅供参考，如有健康问题请咨询专业医生。")
            }
            .sheet(isPresented: $showPrivacy) {
                termsView(title: "隐私政策", content: "AI 育儿助手隐私政策\n\n我们重视您和孩子的隐私保护。\n\n1. 信息收集\n我们收集您主动提供的信息（邮箱、昵称、儿童档案信息）。\n\n2. 信息使用\n收集的信息仅用于提供个性化育儿指导服务。\n\n3. 信息安全\n我们采用行业标准的加密技术保护您的数据安全。\n\n4. 数据删除\n您可以随时申请删除您的账号和所有相关数据。")
            }
        }
    }

    // MARK: - Terms View

    private func termsView(title: String, content: String) -> some View {
        NavigationStack {
            ScrollView {
                Text(content)
                    .font(.body)
                    .padding()
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("关闭") {
                        showTerms = false
                        showPrivacy = false
                    }
                }
            }
        }
    }

    // MARK: - Actions

    @MainActor
    private func performAuth() async {
        isLoading = true
        errorMessage = nil

        do {
            let response: AuthTokenResponse
            if isRegistering {
                let request = AuthRegisterRequest(
                    email: email,
                    password: password,
                    displayName: displayName.isEmpty ? nil : displayName
                )
                response = try await apiClient.request(.register(request))
            } else {
                let request = AuthLoginRequest(email: email, password: password)
                response = try await apiClient.request(.login(request))
            }

            // 保存 Token
            authProvider.saveCredentials(token: response.accessToken, userId: response.userId)

            // 通知登录成功
            onLoginSuccess()
        } catch let error as APIError {
            switch error {
            case .unauthorized:
                errorMessage = "邮箱或密码错误"
            case .conflict:
                errorMessage = "该邮箱已注册"
            case .serverError(let msg):
                errorMessage = msg ?? "服务器错误，请稍后重试"
            default:
                errorMessage = "网络错误，请检查连接"
            }
        } catch {
            errorMessage = "未知错误：\(error.localizedDescription)"
        }

        isLoading = false
    }
}
