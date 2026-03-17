import Foundation

// MARK: - Voice Converse

/// 语音对话请求
public struct VoiceConverseRequest: Codable, Sendable {
    public let transcript: String
    public let childId: UUID
    public let confidence: Double?

    public init(transcript: String, childId: UUID, confidence: Double? = nil) {
        self.transcript = transcript
        self.childId = childId
        self.confidence = confidence
    }
}

/// 语音对话响应
public struct VoiceConverseResponse: Codable, Sendable {
    public let replyText: String
    public let intent: String
    public let actionTaken: [String: AnyCodableValue]?
    public let shouldFallbackToCloudAsr: Bool
    /// Phase 2: 快速记录创建后的 record ID（可用于跳转记录详情）
    public let recordId: String?

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        replyText = try container.decode(String.self, forKey: .replyText)
        intent = try container.decode(String.self, forKey: .intent)
        actionTaken = try container.decodeIfPresent([String: AnyCodableValue].self, forKey: .actionTaken)
        shouldFallbackToCloudAsr = try container.decodeIfPresent(Bool.self, forKey: .shouldFallbackToCloudAsr) ?? false
        recordId = try container.decodeIfPresent(String.self, forKey: .recordId)
    }

    private enum CodingKeys: String, CodingKey {
        case replyText, intent, actionTaken, shouldFallbackToCloudAsr, recordId
    }
}

// MARK: - Voice Transcribe (Cloud ASR Fallback)

/// 云端 ASR 请求
public struct VoiceTranscribeRequest: Codable, Sendable {
    public let audioUrl: String
    public let language: String

    public init(audioUrl: String, language: String = "zh-CN") {
        self.audioUrl = audioUrl
        self.language = language
    }
}

/// 云端 ASR 响应
public struct VoiceTranscribeResponse: Codable, Sendable {
    public let transcript: String
    public let confidence: Double
    public let durationMs: Int?
}

// MARK: - Voice Synthesize (Cloud TTS Fallback)

/// 云端 TTS 请求
public struct VoiceSynthesizeRequest: Codable, Sendable {
    public let text: String
    public let voice: String

    public init(text: String, voice: String = "zh-CN") {
        self.text = text
        self.voice = voice
    }
}

/// 云端 TTS 响应
public struct VoiceSynthesizeResponse: Codable, Sendable {
    public let audioUrl: String?
    public let durationMs: Int?
    public let provider: String
}
