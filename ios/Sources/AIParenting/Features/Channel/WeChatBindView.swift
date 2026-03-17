import SwiftUI

/// 微信扫码绑定页
///
/// 展示 OAuth 二维码，用户微信扫码后自动关注并绑定。
/// 支持实时刷新绑定状态，成功后自动返回。
public struct WeChatBindView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(\.dismiss) private var dismiss

    @State private var qrCodeUrl: String?
    @State private var state: String = ""
    @State private var isLoading = true
    @State private var bindSuccess = false
    @State private var error: String?
    @State private var countdown = 300 // 5 分钟倒计时
    @State private var isPolling = false

    public init() {}

    public var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                if bindSuccess {
                    // 绑定成功
                    successView
                } else if isLoading {
                    ProgressView("正在生成二维码...")
                } else if let error {
                    errorView(error)
                } else {
                    qrCodeView
                }
            }
            .padding()
            .navigationTitle("绑定微信")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("关闭") { dismiss() }
                }
            }
            .task {
                await fetchQRCode()
            }
            .task(id: isPolling) {
                guard isPolling else { return }
                // 使用 structured concurrency 替代 Timer，自动随 View 销毁取消
                while !Task.isCancelled && countdown > 0 && !bindSuccess {
                    try? await Task.sleep(nanoseconds: 3_000_000_000) // 3 秒轮询
                    guard !Task.isCancelled else { break }
                    countdown -= 3
                    if countdown <= 0 { break }
                    await checkBindingStatus()
                }
            }
        }
    }

    // MARK: - QR Code View

    private var qrCodeView: some View {
        VStack(spacing: 20) {
            // 真实二维码图片
            if let qrCodeUrl, let url = URL(string: qrCodeUrl) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                            .frame(width: 200, height: 200)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    case .failure:
                        VStack(spacing: 8) {
                            Image(systemName: "qrcode")
                                .font(.system(size: 80))
                                .foregroundStyle(.secondary)
                            Text("二维码加载失败")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            Button("重新加载") {
                                Task { await fetchQRCode() }
                            }
                            .font(.caption)
                        }
                    case .empty:
                        ProgressView()
                            .frame(width: 200, height: 200)
                    @unknown default:
                        EmptyView()
                    }
                }
            } else {
                Image(systemName: "qrcode")
                    .font(.system(size: 120))
                    .foregroundStyle(.secondary)
            }

            Text("请使用微信扫描二维码")
                .font(.headline)

            Text("扫码后将自动关注服务号并完成绑定")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            // 倒计时
            HStack(spacing: 4) {
                Image(systemName: "clock")
                    .font(.caption)
                Text("二维码有效期：\(countdown / 60):\(String(format: "%02d", countdown % 60))")
                    .font(.caption)
            }
            .foregroundStyle(.tertiary)

            if countdown <= 0 {
                Button("重新生成") {
                    Task { await fetchQRCode() }
                }
                .buttonStyle(.borderedProminent)
            }
        }
    }

    // MARK: - Success View

    private var successView: some View {
        VStack(spacing: 20) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 60))
                .foregroundStyle(.green)

            Text("微信绑定成功！")
                .font(.title3)
                .fontWeight(.semibold)

            Text("您将通过微信服务号接收推送消息")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            Button("完成") {
                dismiss()
            }
            .buttonStyle(.borderedProminent)
            .padding(.top, 8)
        }
        .onAppear {
            // 3 秒后自动关闭
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                dismiss()
            }
        }
    }

    // MARK: - Error View

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.title)
                .foregroundStyle(.orange)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("重试") {
                Task { await fetchQRCode() }
            }
            .buttonStyle(.borderedProminent)
        }
    }

    // MARK: - Actions

    @MainActor
    private func fetchQRCode() async {
        isLoading = true
        error = nil
        countdown = 300
        isPolling = false
        do {
            let response: WeChatQRCodeResponse = try await apiClient.request(.wechatQRCode)
            qrCodeUrl = response.qrcodeUrl
            state = response.state
            countdown = response.expiresIn
            isLoading = false
            isPolling = true
        } catch {
            self.error = "获取二维码失败，请检查网络后重试"
            isLoading = false
        }
    }

    @MainActor
    private func checkBindingStatus() async {
        do {
            let response: ChannelBindingListResponse = try await apiClient.request(.listChannelBindings)
            if response.bindings.contains(where: { $0.channel == "wechat" && $0.isActive }) {
                isPolling = false
                withAnimation { bindSuccess = true }
            }
        } catch {
            // 静默失败，继续轮询
        }
    }
}
