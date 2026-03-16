import SwiftUI

/// 登录/注册页面
///
/// 提供邮箱+密码的登录和注册功能，登录成功后保存 JWT Token
/// 并触发 AppState 初始化。
struct LoginView: View {

    @State private var email = ""
    @State private var password = ""
    @State private var displayName = ""
    @State private var isRegistering = false
    @State private var isLoading = false
    @State private var errorMessage: String?

    let apiClient: APIClientProtocol
    let authProvider: JWTAuthProvider
    let onLoginSuccess: () -> Void

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

                    TextField("邮箱", text: $email)
                        .textFieldStyle(.roundedBorder)
                        .textContentType(.emailAddress)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)

                    SecureField("密码", text: $password)
                        .textFieldStyle(.roundedBorder)
                        .textContentType(isRegistering ? .newPassword : .password)
                }
                .padding(.horizontal, 32)

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
                    .disabled(isLoading || email.isEmpty || password.isEmpty)
                    .padding(.horizontal, 32)

                    Button {
                        withAnimation {
                            isRegistering.toggle()
                            errorMessage = nil
                        }
                    } label: {
                        Text(isRegistering ? "已有账号？去登录" : "没有账号？去注册")
                            .font(.subheadline)
                    }
                }

                Spacer()

                // Skip Login (Dev Mode)
                Button {
                    onLoginSuccess()
                } label: {
                    Text("跳过登录（开发模式）")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 20)
            }
            .navigationBarHidden(true)
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
