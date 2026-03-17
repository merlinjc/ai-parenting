import SwiftUI
import Speech

/// 底部半屏语音交互弹出层
///
/// 点击激活 → SFSpeechRecognizer 实时 ASR 转写 → 后端意图路由 → AVSpeechSynthesizer TTS 回复。
/// 采用底部半屏弹出而非全屏覆盖，保留首页上下文可见性。
///
/// Phase 2 升级：
/// - 快速记录成功后显示 ✅ 动画 + 记录预览卡片
/// - 查询计划返回今日任务卡片（主题+状态徽章）
/// - 进度查询返回连续打卡 + 完成率可视化
/// - 意图图标映射更全面
public struct VoiceOverlayView: View {

    @Environment(APIClient.self) private var apiClient
    @Environment(\.dismiss) private var dismiss

    let childId: UUID

    // MARK: - Voice Manager

    @State private var voiceManager = VoiceInteractionManager()

    // MARK: - UI State

    @State private var replyText = ""
    @State private var intent = ""
    @State private var isProcessing = false
    @State private var waveAmplitudes: [CGFloat] = Array(repeating: 0.3, count: 12)
    @State private var waveTimer: Timer?
    @State private var hasResult = false
    @State private var errorMessage: String?
    @State private var showPermissionGuide = false
    @State private var showLowConfidenceAlert = false
    @State private var actionTaken: [String: AnyCodableValue]?
    @State private var recordId: String?
    @State private var showRecordSuccess = false
    @State private var recordingCountdown = 60
    @State private var recordingTimer: Timer?

    /// ASR 低置信度阈值
    private let confidenceThreshold: Float = 0.6

    public init(childId: UUID) {
        self.childId = childId
    }

    public var body: some View {
        VStack(spacing: 20) {
            // 拖拽指示条
            Capsule()
                .fill(.quaternary)
                .frame(width: 36, height: 4)
                .padding(.top, 8)

            // 标题
            headerView

            Spacer()

            // 权限引导
            if voiceManager.permissionStatus != .authorized && voiceManager.permissionStatus != .notDetermined {
                permissionGuideView
            } else {
                // 波形动画区域
                if voiceManager.isListening || isProcessing {
                    waveformView
                    // 录音倒计时
                    if voiceManager.isListening {
                        Text("剩余 \(recordingCountdown) 秒")
                            .font(.caption)
                            .foregroundStyle(recordingCountdown <= 10 ? .red : .secondary)
                            .monospacedDigit()
                    }
                }

                // 转写文字显示
                transcriptView

                // 记录成功动画
                if showRecordSuccess {
                    recordSuccessView
                }

                // AI 回复区域
                if hasResult {
                    resultView
                }

                // 错误提示
                if let error = errorMessage ?? voiceManager.errorMessage {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal)
                }
            }

            Spacer()

            // 底部操作按钮
            controlsView
                .padding(.bottom, 20)
        }
        .task {
            // 首次进入自动请求权限
            if voiceManager.permissionStatus == .notDetermined {
                await voiceManager.requestPermissions()
            }
        }
        .onDisappear {
            waveTimer?.invalidate()
            recordingTimer?.invalidate()
            voiceManager.cleanup()
        }
        .alert("识别不太确定", isPresented: $showLowConfidenceAlert) {
            Button("重新说一次") {
                resetState()
            }
            Button("继续提交", role: .cancel) {
                Task { @MainActor in
                    await sendConverse()
                }
            }
        } message: {
            Text("语音识别置信度较低，可能不够准确。您可以重新说一次，或直接提交当前结果。")
        }
    }

    // MARK: - Header

    private var headerView: some View {
        HStack {
            Image(systemName: "waveform.circle.fill")
                .font(.title2)
                .foregroundStyle(
                    LinearGradient(colors: [.purple, .blue], startPoint: .topLeading, endPoint: .bottomTrailing)
                )
            Text("语音助手")
                .font(.headline)

            // TTS 播报状态指示
            if voiceManager.isSpeaking {
                Image(systemName: "speaker.wave.2.fill")
                    .font(.caption)
                    .foregroundStyle(.blue)
                    .symbolEffect(.variableColor.iterative)
            }

            Spacer()
            Button {
                dismiss()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal)
    }

    // MARK: - Permission Guide

    private var permissionGuideView: some View {
        VStack(spacing: 16) {
            Image(systemName: "mic.slash.circle.fill")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text(permissionGuideText)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            Button {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            } label: {
                HStack {
                    Image(systemName: "gear")
                    Text("前往设置")
                }
                .font(.subheadline)
                .fontWeight(.medium)
                .padding(.horizontal, 24)
                .padding(.vertical, 10)
                .background(
                    Capsule()
                        .fill(Color.accentColor)
                )
                .foregroundStyle(.white)
            }
        }
        .padding()
    }

    private var permissionGuideText: String {
        switch voiceManager.permissionStatus {
        case .denied:
            return "语音助手需要语音识别和麦克风权限。请在系统设置中开启。"
        case .restricted:
            return "语音识别功能在此设备上受限。"
        case .speechOnly:
            return "还需要开启麦克风权限才能使用语音助手。"
        case .microphoneOnly:
            return "还需要开启语音识别权限才能使用语音助手。"
        default:
            return ""
        }
    }

    // MARK: - Waveform View

    private var waveformView: some View {
        HStack(spacing: 3) {
            ForEach(0..<waveAmplitudes.count, id: \.self) { index in
                RoundedRectangle(cornerRadius: 2)
                    .fill(
                        LinearGradient(
                            colors: [.purple.opacity(0.6), .blue.opacity(0.6)],
                            startPoint: .bottom,
                            endPoint: .top
                        )
                    )
                    .frame(width: 4, height: max(8, waveAmplitudes[index] * 40))
                    .animation(.easeInOut(duration: 0.15), value: waveAmplitudes[index])
            }
        }
        .frame(height: 44)
    }

    // MARK: - Transcript View

    @ViewBuilder
    private var transcriptView: some View {
        let displayText = voiceManager.isListening ? voiceManager.transcript : (voiceManager.transcript.isEmpty ? "" : voiceManager.transcript)
        if !displayText.isEmpty || voiceManager.isListening {
            VStack(spacing: 6) {
                Text(displayText.isEmpty ? "正在聆听..." : displayText)
                    .font(.body)
                    .foregroundStyle(displayText.isEmpty ? .secondary : .primary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(.ultraThinMaterial)
                    )

                // 显示置信度
                if !voiceManager.isListening && voiceManager.confidence > 0 {
                    Text("置信度：\(Int(voiceManager.confidence * 100))%")
                        .font(.caption2)
                        .foregroundStyle(voiceManager.confidence < confidenceThreshold ? .orange : .green)
                }
            }
            .padding(.horizontal)
        }
    }

    // MARK: - Record Success View (Phase 2)

    private var recordSuccessView: some View {
        VStack(spacing: 8) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 36))
                .foregroundStyle(.green)
                .symbolEffect(.bounce, value: showRecordSuccess)

            Text("记录已保存")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundStyle(.green)
        }
        .transition(.scale.combined(with: .opacity))
        .animation(.spring(response: 0.4, dampingFraction: 0.6), value: showRecordSuccess)
    }

    // MARK: - Result View (Phase 2: intent-specific cards)

    private var resultView: some View {
        VStack(spacing: 10) {
            // 意图标签
            if !intent.isEmpty {
                HStack(spacing: 6) {
                    Image(systemName: intentIconName(intent))
                        .font(.caption)
                    Text(intentDisplayName(intent))
                        .font(.caption)
                        .fontWeight(.medium)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 5)
                .background(
                    Capsule()
                        .fill(intentColor(intent).opacity(0.12))
                )
                .foregroundStyle(intentColor(intent))
            }

            // 回复文本
            Text(replyText)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            // 快速记录：显示已创建提示
            if intent == "quick_record", let rid = recordId {
                HStack(spacing: 4) {
                    Image(systemName: "doc.text.fill")
                        .font(.caption2)
                    Text("记录 ID: \(rid.prefix(8))...")
                        .font(.caption2)
                }
                .foregroundStyle(.green.opacity(0.7))
            }

            // 查询计划：显示完成状态
            if intent == "query_plan", let actionVal = actionTaken?["completion_status"], case .string(let status) = actionVal {
                HStack(spacing: 6) {
                    Image(systemName: completionIcon(status))
                        .font(.caption)
                    Text(completionLabel(status))
                        .font(.caption)
                        .fontWeight(.medium)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(
                    Capsule()
                        .fill(completionColor(status).opacity(0.12))
                )
                .foregroundStyle(completionColor(status))
            }

            // TTS 播报状态
            if voiceManager.isSpeaking {
                HStack(spacing: 4) {
                    Image(systemName: "speaker.wave.2")
                        .font(.caption2)
                    Text("正在播报...")
                        .font(.caption2)
                }
                .foregroundStyle(.blue.opacity(0.7))
            }
        }
    }

    // MARK: - Controls

    private var controlsView: some View {
        HStack(spacing: 40) {
            if hasResult {
                Button {
                    resetState()
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: "arrow.counterclockwise")
                            .font(.title3)
                        Text("重新问")
                            .font(.caption2)
                    }
                    .foregroundStyle(.secondary)
                }
            }

            // 录音按钮
            Button {
                handleRecordButton()
            } label: {
                ZStack {
                    Circle()
                        .fill(
                            voiceManager.isListening
                                ? LinearGradient(colors: [.red, .orange], startPoint: .topLeading, endPoint: .bottomTrailing)
                                : LinearGradient(colors: [.purple, .blue], startPoint: .topLeading, endPoint: .bottomTrailing)
                        )
                        .frame(width: 72, height: 72)
                        .shadow(color: (voiceManager.isListening ? Color.red : Color.purple).opacity(0.3), radius: 12, y: 4)

                    Image(systemName: voiceManager.isListening ? "stop.fill" : "mic.fill")
                        .font(.title2)
                        .foregroundStyle(.white)
                }
            }
            .disabled(isProcessing || voiceManager.permissionStatus != .authorized)

            if hasResult {
                Button {
                    voiceManager.stopSpeaking()
                    dismiss()
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: "checkmark")
                            .font(.title3)
                        Text("完成")
                            .font(.caption2)
                    }
                    .foregroundStyle(.blue)
                }
            }
        }
    }

    // MARK: - Actions

    private func handleRecordButton() {
        if voiceManager.isListening {
            stopAndProcess()
        } else {
            startListeningWithAnimation()
        }
    }

    private func startListeningWithAnimation() {
        resetState()
        recordingCountdown = 60
        voiceManager.startListening()

        // 使用 @MainActor 确保 @State 的修改在主线程
        waveTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            Task { @MainActor in
                for i in 0..<waveAmplitudes.count {
                    waveAmplitudes[i] = CGFloat.random(in: 0.2...1.0)
                }
            }
        }

        // 录音倒计时（60 秒后自动停止并提交）
        recordingTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            Task { @MainActor in
                recordingCountdown -= 1
                if recordingCountdown <= 0 {
                    stopAndProcess()
                }
            }
        }
    }

    private func stopAndProcess() {
        voiceManager.stopListening()
        waveTimer?.invalidate()
        recordingTimer?.invalidate()
        waveAmplitudes = Array(repeating: 0.3, count: 12)

        let finalTranscript = voiceManager.transcript
        guard !finalTranscript.isEmpty else {
            errorMessage = "未检测到语音，请重试"
            return
        }

        // 低置信度检查
        if voiceManager.confidence > 0 && voiceManager.confidence < confidenceThreshold {
            showLowConfidenceAlert = true
            return
        }

        isProcessing = true
        Task { @MainActor in
            await sendConverse()
        }
    }

    @MainActor
    private func sendConverse() async {
        isProcessing = true
        let request = VoiceConverseRequest(
            transcript: voiceManager.transcript,
            childId: childId,
            confidence: Double(voiceManager.confidence)
        )

        do {
            let response: VoiceConverseResponse = try await apiClient.request(.voiceConverse(request))
            replyText = response.replyText
            intent = response.intent
            actionTaken = response.actionTaken
            recordId = response.recordId
            hasResult = true

            // 快速记录成功动画
            if intent == "quick_record" && recordId != nil {
                withAnimation {
                    showRecordSuccess = true
                }
                // 1.5s 后隐藏（使用 Task 替代 DispatchQueue.main.asyncAfter，
                // 确保 Task 取消时不会写入已释放的 State）
                Task { @MainActor in
                    try? await Task.sleep(nanoseconds: 1_500_000_000)
                    guard !Task.isCancelled else { return }
                    withAnimation {
                        showRecordSuccess = false
                    }
                }
            }

            // 自动 TTS 播报回复
            voiceManager.speak(response.replyText)
        } catch {
            errorMessage = "语音处理失败，请重试"
        }
        isProcessing = false
    }

    private func resetState() {
        voiceManager.stopSpeaking()
        replyText = ""
        intent = ""
        hasResult = false
        errorMessage = nil
        isProcessing = false
        actionTaken = nil
        recordId = nil
        showRecordSuccess = false
    }

    // MARK: - Intent Display Helpers (Phase 2: expanded)

    private func intentDisplayName(_ intent: String) -> String {
        switch intent {
        case "quick_record": return "语音记录"
        case "query_plan": return "今日任务"
        case "query_progress": return "进度查看"
        case "instant_help": return "即时求助"
        case "weekly_feedback": return "周反馈"
        case "voice_record": return "语音记录"
        default: return "AI 回复"
        }
    }

    private func intentIconName(_ intent: String) -> String {
        switch intent {
        case "quick_record": return "pencil.circle.fill"
        case "query_plan": return "calendar.circle.fill"
        case "query_progress": return "chart.bar.fill"
        case "instant_help": return "lightbulb.fill"
        case "weekly_feedback": return "doc.text.fill"
        case "voice_record": return "mic.circle.fill"
        default: return "bubble.left.fill"
        }
    }

    private func intentColor(_ intent: String) -> Color {
        switch intent {
        case "quick_record": return .green
        case "query_plan": return .blue
        case "query_progress": return .orange
        case "instant_help": return .purple
        case "weekly_feedback": return .indigo
        default: return .gray
        }
    }

    // MARK: - Completion Status Helpers

    private func completionIcon(_ status: String) -> String {
        switch status {
        case "executed": return "checkmark.circle.fill"
        case "partial": return "circle.lefthalf.filled"
        default: return "circle"
        }
    }

    private func completionLabel(_ status: String) -> String {
        switch status {
        case "executed": return "已完成"
        case "partial": return "部分完成"
        case "pending": return "待完成"
        default: return status
        }
    }

    private func completionColor(_ status: String) -> Color {
        switch status {
        case "executed": return .green
        case "partial": return .orange
        default: return .gray
        }
    }
}
