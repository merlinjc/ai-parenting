import SwiftUI
import AVFoundation

/// 语音录制组件
///
/// 集成 AVAudioRecorder 实现录音→本地保存→创建语音记录。
/// voice_url 暂用本地路径，后续接入 OSS 文件上传。
public struct VoiceRecordView: View {

    @Environment(APIClient.self) private var apiClient
    public let childId: UUID
    public let viewModel: RecordViewModel
    public let onDismiss: () -> Void
    public var sourcePlanId: UUID?
    public var sourceSessionId: UUID?

    @State private var isRecording = false
    @State private var recordingDuration: TimeInterval = 0
    @State private var audioRecorder: AVAudioRecorder?
    @State private var recordingURL: URL?
    @State private var hasRecording = false
    @State private var permissionDenied = false
    @State private var isUploading = false
    @State private var audioSessionError: String?

    public init(
        childId: UUID,
        viewModel: RecordViewModel,
        onDismiss: @escaping () -> Void,
        sourcePlanId: UUID? = nil,
        sourceSessionId: UUID? = nil
    ) {
        self.childId = childId
        self.viewModel = viewModel
        self.onDismiss = onDismiss
        self.sourcePlanId = sourcePlanId
        self.sourceSessionId = sourceSessionId
    }

    public var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                // 录音状态指示
                ZStack {
                    Circle()
                        .fill(isRecording ? .red.opacity(0.1) : .blue.opacity(0.05))
                        .frame(width: 160, height: 160)

                    if isRecording {
                        Circle()
                            .fill(.red.opacity(0.05))
                            .frame(width: 200, height: 200)
                            .scaleEffect(isRecording ? 1.1 : 1.0)
                            .animation(.easeInOut(duration: 1).repeatForever(), value: isRecording)
                    }

                    Image(systemName: isRecording ? "waveform" : "mic.fill")
                        .font(.system(size: 48))
                        .foregroundStyle(isRecording ? .red : .blue)
                }

                // 时长显示
                Text(formatDuration(recordingDuration))
                    .font(.system(size: 48, weight: .light, design: .monospaced))
                    .foregroundStyle(isRecording ? .red : .primary)

                // 状态文本
                Text(statusText)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                if permissionDenied {
                    Text("请在系统设置中允许麦克风权限")
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                if let audioSessionError {
                    Text(audioSessionError)
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                Spacer()

                // 操作按钮
                HStack(spacing: 40) {
                    if hasRecording && !isRecording {
                        // 重录
                        Button {
                            resetRecording()
                        } label: {
                            VStack(spacing: 4) {
                                Image(systemName: "arrow.counterclockwise")
                                    .font(.title2)
                                Text("重录")
                                    .font(.caption)
                            }
                            .foregroundStyle(.secondary)
                        }
                    }

                    // 录音/停止按钮
                    Button {
                        if isRecording {
                            stopRecording()
                        } else {
                            startRecording()
                        }
                    } label: {
                        Circle()
                            .fill(isRecording ? .red : .blue)
                            .frame(width: 72, height: 72)
                            .overlay {
                                if isRecording {
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(.white)
                                        .frame(width: 24, height: 24)
                                } else {
                                    Circle()
                                        .fill(.white)
                                        .frame(width: 28, height: 28)
                                }
                            }
                    }

                    if hasRecording && !isRecording {
                        // 保存
                        Button {
                            Task { await saveVoiceRecord() }
                        } label: {
                            VStack(spacing: 4) {
                                if viewModel.isCreating || isUploading {
                                    ProgressView()
                                        .font(.title2)
                                } else {
                                    Image(systemName: "checkmark.circle.fill")
                                        .font(.title2)
                                }
                                Text(isUploading ? "上传中" : "保存")
                                    .font(.caption)
                            }
                            .foregroundStyle(.green)
                        }
                        .disabled(viewModel.isCreating || isUploading)
                    }
                }

                Spacer()
                    .frame(height: 40)
            }
            .padding()
            .navigationTitle("语音记录")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") {
                        stopRecording()
                        cleanupTempFile()
                        onDismiss()
                    }
                }
            }
            .task(id: isRecording) {
                guard isRecording else { return }
                while !Task.isCancelled && isRecording {
                    try? await Task.sleep(nanoseconds: 100_000_000) // 0.1s
                    if isRecording {
                        recordingDuration += 0.1
                    }
                }
            }
        }
    }

    // MARK: - Recording

    private func startRecording() {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .default)
            try session.setActive(true)
        } catch {
            audioSessionError = "无法启动录音：\(error.localizedDescription)"
            return
        }
        audioSessionError = nil

        // 检查权限
        switch AVAudioApplication.shared.recordPermission {
        case .granted:
            beginRecording()
        case .denied:
            permissionDenied = true
        case .undetermined:
            AVAudioApplication.requestRecordPermission { granted in
                DispatchQueue.main.async {
                    if granted {
                        beginRecording()
                    } else {
                        permissionDenied = true
                    }
                }
            }
        @unknown default:
            break
        }
    }

    private func beginRecording() {
        let fileName = "voice_\(UUID().uuidString).m4a"
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(fileName)
        recordingURL = url

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]

        do {
            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
            audioRecorder?.record()
            isRecording = true
            recordingDuration = 0
        } catch {
            audioSessionError = "录音启动失败：\(error.localizedDescription)"
        }
    }

    private func stopRecording() {
        audioRecorder?.stop()
        audioRecorder = nil
        isRecording = false
        if recordingDuration > 0.5 {
            hasRecording = true
        }
    }

    private func resetRecording() {
        cleanupTempFile()
        hasRecording = false
        recordingDuration = 0
        recordingURL = nil
    }

    /// 清理临时录音文件，避免临时目录积累
    private func cleanupTempFile() {
        guard let url = recordingURL else { return }
        try? FileManager.default.removeItem(at: url)
    }

    private func saveVoiceRecord() async {
        // 先上传音频文件获取 server URL
        guard let localURL = recordingURL, let fileData = try? Data(contentsOf: localURL) else {
            audioSessionError = "无法读取录音文件"
            return
        }

        isUploading = true
        let voiceUrl: String
        do {
            let uploadResponse = try await apiClient.uploadFile(
                data: fileData,
                filename: localURL.lastPathComponent,
                mimeType: "audio/mp4"
            )
            voiceUrl = uploadResponse.url
        } catch {
            // 上传失败时提示用户，不使用本地 file:// 路径保存（其他设备无法访问且临时文件会被清理）
            isUploading = false
            audioSessionError = "音频上传失败，请检查网络后重试"
            return
        }
        isUploading = false

        let create = RecordCreate(
            childId: childId,
            type: RecordType.voice.rawValue,
            content: "语音记录（\(formatDuration(recordingDuration))）",
            voiceUrl: voiceUrl,
            sourcePlanId: sourcePlanId,
            sourceSessionId: sourceSessionId
        )
        let success = await viewModel.createRecord(create)
        if success {
            onDismiss()
        }
    }

    // MARK: - Helpers

    private var statusText: String {
        if isRecording { return "正在录音..." }
        if hasRecording { return "录音完成，可以保存或重录" }
        return "点击下方按钮开始录音"
    }

    private func formatDuration(_ duration: TimeInterval) -> String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        let tenths = Int((duration * 10).truncatingRemainder(dividingBy: 10))
        return String(format: "%02d:%02d.%d", minutes, seconds, tenths)
    }
}
