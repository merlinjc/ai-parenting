import Foundation
import UserNotifications
#if canImport(UIKit)
import UIKit
#endif
#if canImport(Observation)
import Observation
#endif

/// 推送通知管理器
///
/// 集中管理推送权限请求、APNs 注册和通知接收处理。
/// 通知点击时解析 userInfo 中的 target_page/message_id，驱动 AppState 深链导航。
@Observable
public final class PushNotificationManager: NSObject, @unchecked Sendable {

    /// 是否已获取通知权限
    public var isAuthorized = false

    /// 当前 device token（十六进制字符串）
    public var deviceToken: String?

    /// 权限被拒绝
    public var permissionDenied = false

    /// 导航回调（由 AppState 设置）
    public var onNotificationTapped: ((_ target: String, _ params: [String: String]) -> Void)?

    public override init() {
        super.init()
    }

    // MARK: - Permission

    /// 请求通知权限
    @MainActor
    public func requestPermission() async {
        let center = UNUserNotificationCenter.current()
        do {
            let granted = try await center.requestAuthorization(options: [.alert, .badge, .sound])
            isAuthorized = granted
            permissionDenied = !granted
            if granted {
                registerForRemoteNotifications()
            }
        } catch {
            permissionDenied = true
        }
    }

    /// 注册远程推送
    @MainActor
    public func registerForRemoteNotifications() {
        #if canImport(UIKit) && !targetEnvironment(simulator)
        UIApplication.shared.registerForRemoteNotifications()
        #endif
    }

    // MARK: - Token

    /// 处理 APNs 注册成功，将 Data 转换为十六进制 token 字符串
    public func handleDeviceToken(_ tokenData: Data) {
        let token = tokenData.map { String(format: "%02.2hhx", $0) }.joined()
        deviceToken = token
    }

    /// 处理 APNs 注册失败
    public func handleRegistrationError(_ error: Error) {
        // 静默记录错误，不影响正常使用
        print("[PushNotificationManager] Registration failed: \(error.localizedDescription)")
    }
}

// MARK: - UNUserNotificationCenterDelegate

extension PushNotificationManager: UNUserNotificationCenterDelegate {

    /// 前台通知展示策略：仍然显示 banner + sound + badge
    public func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification,
        withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
    ) {
        completionHandler([.banner, .sound, .badge])
    }

    /// 通知点击处理：解析 userInfo 中的 target_page 和参数，触发深链导航
    public func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse,
        withCompletionHandler completionHandler: @escaping () -> Void
    ) {
        let userInfo = response.notification.request.content.userInfo

        if let targetPage = userInfo["target_page"] as? String {
            var params: [String: String] = [:]
            if let messageId = userInfo["message_id"] as? String {
                params["message_id"] = messageId
            }
            if let planId = userInfo["plan_id"] as? String {
                params["plan_id"] = planId
            }
            if let feedbackId = userInfo["feedback_id"] as? String {
                params["feedback_id"] = feedbackId
            }

            DispatchQueue.main.async { [weak self] in
                self?.onNotificationTapped?(targetPage, params)
            }
        }

        completionHandler()
    }
}
