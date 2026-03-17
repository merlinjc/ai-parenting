import Foundation
import Speech
import AVFoundation

/// 统一语音交互管理器
///
/// 封装 iOS 原生 ASR（SFSpeechRecognizer 流式转写）和 TTS（AVSpeechSynthesizer 本地播报）。
/// 遵循 iOS 原生优先策略：语音数据不出设备，后端仅接收文本。
///
/// 核心方法：
/// - `startListening()` — 启动音频采集 + 流式 ASR，实时更新 `transcript`
/// - `stopListening()` — 停止 ASR，返回最终转写结果和置信度
/// - `speak(_:)` — 本地 TTS 播报文本
///
/// UI 绑定状态：
/// - `transcript` — 当前识别文本（流式更新）
/// - `isListening` — 是否正在录音
/// - `isSpeaking` — 是否正在 TTS 播报
/// - `confidence` — ASR 置信度 (0.0~1.0)
/// - `permissionStatus` — 权限状态
@Observable
public final class VoiceInteractionManager: NSObject {

    // MARK: - UI Binding State

    /// 当前 ASR 转写文本（流式实时更新）
    public private(set) var transcript: String = ""

    /// 是否正在录音/ASR
    public private(set) var isListening: Bool = false

    /// 是否正在 TTS 播报
    public private(set) var isSpeaking: Bool = false

    /// ASR 最终置信度 (0.0~1.0)
    public private(set) var confidence: Float = 0.0

    /// 权限状态
    public private(set) var permissionStatus: PermissionStatus = .notDetermined

    /// 错误信息
    public private(set) var errorMessage: String?

    // MARK: - Permission Types

    public enum PermissionStatus: Equatable {
        case notDetermined
        case authorized
        case denied
        case restricted
        case speechOnly    // 仅语音权限，缺少麦克风
        case microphoneOnly // 仅麦克风权限，缺少语音
    }

    // MARK: - Private Properties

    /// ASR：SFSpeechRecognizer（中文简体）
    private let speechRecognizer: SFSpeechRecognizer?

    /// ASR 识别请求
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?

    /// ASR 识别任务
    private var recognitionTask: SFSpeechRecognitionTask?

    /// 音频引擎（采集麦克风音频输入）
    private let audioEngine = AVAudioEngine()

    /// TTS 合成器
    private let synthesizer = AVSpeechSynthesizer()

    /// TTS 中文语音
    private let chineseVoice = AVSpeechSynthesisVoice(language: "zh-CN")

    /// TTS 语速：0.52（育儿场景稍慢于默认速率）
    private let speechRate: Float = 0.52

    /// TTS 播报完成回调
    private var speakCompletion: (() -> Void)?

    /// ASR 是否支持设备端识别（iOS 13+ 离线模式）
    public var supportsOnDeviceRecognition: Bool {
        speechRecognizer?.supportsOnDeviceRecognition ?? false
    }

    // MARK: - Init

    public override init() {
        self.speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "zh-Hans"))
        super.init()
        self.synthesizer.delegate = self
    }

    // MARK: - Permission

    /// 请求语音识别 + 麦克风权限
    ///
    /// 在首次使用语音功能前调用。两项权限均授予后 `permissionStatus` 变为 `.authorized`。
    @MainActor
    public func requestPermissions() async {
        // 1. 请求语音识别权限
        let speechStatus = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { status in
                continuation.resume(returning: status)
            }
        }

        guard speechStatus == .authorized else {
            permissionStatus = speechStatus == .denied ? .denied : .restricted
            return
        }

        // 2. 请求麦克风权限
        let micGranted: Bool
        if #available(iOS 17.0, *) {
            micGranted = await AVAudioApplication.requestRecordPermission()
        } else {
            micGranted = await withCheckedContinuation { continuation in
                AVAudioSession.sharedInstance().requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        }

        if micGranted {
            permissionStatus = .authorized
        } else {
            permissionStatus = .speechOnly
        }
    }

    // MARK: - ASR (Speech-to-Text)

    /// 开始流式语音识别
    ///
    /// 启动 AVAudioEngine 采集麦克风音频，通过 SFSpeechRecognizer 实时转写。
    /// `transcript` 会随说话实时更新（partialResults）。
    ///
    /// - Throws: 权限不足或 SFSpeechRecognizer 不可用时抛出错误
    @MainActor
    public func startListening() {
        guard permissionStatus == .authorized else {
            errorMessage = "需要语音识别和麦克风权限"
            return
        }

        guard let speechRecognizer, speechRecognizer.isAvailable else {
            errorMessage = "语音识别当前不可用"
            return
        }

        // 如果正在识别，先停止
        if isListening {
            stopListening()
        }

        // 如果正在 TTS，先停止
        if isSpeaking {
            stopSpeaking()
        }

        // 重置状态
        transcript = ""
        confidence = 0.0
        errorMessage = nil

        do {
            try configureAudioSession(for: .record)
            try startAudioEngine()
        } catch {
            errorMessage = "音频引擎启动失败：\(error.localizedDescription)"
            return
        }

        // 创建识别请求
        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let recognitionRequest else {
            errorMessage = "无法创建语音识别请求"
            return
        }

        // 流式：边说边转
        recognitionRequest.shouldReportPartialResults = true

        // iOS 13+ 支持设备端识别（离线、隐私友好）
        if speechRecognizer.supportsOnDeviceRecognition {
            recognitionRequest.requiresOnDeviceRecognition = true
        }

        // 启动识别任务
        recognitionTask = speechRecognizer.recognitionTask(with: recognitionRequest) { [weak self] result, error in
            guard let self else { return }

            if let result {
                // 主线程更新 UI 状态
                Task { @MainActor in
                    self.transcript = result.bestTranscription.formattedString

                    // 计算置信度（取所有段的平均置信度）
                    let segments = result.bestTranscription.segments
                    if !segments.isEmpty {
                        let avgConfidence = segments.reduce(Float(0)) { $0 + $1.confidence } / Float(segments.count)
                        self.confidence = avgConfidence
                    }

                    // 如果是最终结果
                    if result.isFinal {
                        self.finishRecognition()
                    }
                }
            }

            if let error {
                Task { @MainActor in
                    // SFSpeechRecognizer 超时（约 1 分钟）也会触发 error
                    // 如果已经有转写内容，视为正常完成
                    if !self.transcript.isEmpty {
                        self.finishRecognition()
                    } else {
                        self.errorMessage = "识别错误：\(error.localizedDescription)"
                        self.finishRecognition()
                    }
                }
            }
        }

        isListening = true
    }

    /// 停止语音识别
    ///
    /// 手动结束录音，触发最终识别结果回调。
    @MainActor
    public func stopListening() {
        guard isListening else { return }

        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()

        isListening = false
    }

    // MARK: - TTS (Text-to-Speech)

    /// 本地 TTS 播报文本
    ///
    /// 使用 AVSpeechSynthesizer 零延迟播报，无需网络。
    /// 育儿场景使用稍慢语速 (rate = 0.52)，便于家长理解。
    ///
    /// - Parameters:
    ///   - text: 要播报的文本
    ///   - completion: 播报完成回调（可选）
    @MainActor
    public func speak(_ text: String, completion: (() -> Void)? = nil) {
        guard !text.isEmpty else {
            completion?()
            return
        }

        // 停止之前的 TTS
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }

        speakCompletion = completion

        do {
            try configureAudioSession(for: .playback)
        } catch {
            errorMessage = "音频会话配置失败"
            completion?()
            return
        }

        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = chineseVoice
        utterance.rate = speechRate
        utterance.pitchMultiplier = 1.0
        utterance.preUtteranceDelay = 0.1
        utterance.postUtteranceDelay = 0.2

        isSpeaking = true
        synthesizer.speak(utterance)
    }

    /// 停止 TTS 播报
    @MainActor
    public func stopSpeaking() {
        guard isSpeaking else { return }
        synthesizer.stopSpeaking(at: .immediate)
        isSpeaking = false
        speakCompletion = nil
    }

    // MARK: - Cleanup

    /// 释放所有语音资源
    @MainActor
    public func cleanup() {
        stopListening()
        stopSpeaking()
        recognitionTask?.cancel()
        recognitionTask = nil
        recognitionRequest = nil
    }

    // MARK: - Private Helpers

    /// 音频用途
    private enum AudioPurpose {
        case record
        case playback
    }

    /// 配置 AVAudioSession
    private func configureAudioSession(for purpose: AudioPurpose) throws {
        let session = AVAudioSession.sharedInstance()

        switch purpose {
        case .record:
            // 录播模式，支持同时录音和播放
            try session.setCategory(.playAndRecord, mode: .measurement, options: [.defaultToSpeaker, .allowBluetooth])
        case .playback:
            // 播放模式
            try session.setCategory(.playback, mode: .default, options: [.duckOthers])
        }

        try session.setActive(true, options: .notifyOthersOnDeactivation)
    }

    /// 启动音频引擎
    private func startAudioEngine() throws {
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)

        // 安装音频输入 tap，将采集的音频 buffer 送入识别请求
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
            self?.recognitionRequest?.append(buffer)
        }

        audioEngine.prepare()
        try audioEngine.start()
    }

    /// 完成识别后的清理（防重入，确保只执行一次）
    @MainActor
    private func finishRecognition() {
        // 防止 isFinal 和 error 双重触发
        guard isListening || recognitionTask != nil || recognitionRequest != nil else { return }

        isListening = false

        if audioEngine.isRunning {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
        }

        recognitionRequest?.endAudio()
        recognitionTask = nil
        recognitionRequest = nil
    }
}

// MARK: - AVSpeechSynthesizerDelegate

extension VoiceInteractionManager: AVSpeechSynthesizerDelegate {

    public func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in
            isSpeaking = false
            let completion = speakCompletion
            speakCompletion = nil
            completion?()
        }
    }

    public func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
        Task { @MainActor in
            isSpeaking = false
            speakCompletion = nil
        }
    }
}
