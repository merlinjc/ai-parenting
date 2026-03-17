"""语音管线模块。

iOS 原生优先策略：ASR/TTS 在 iOS 端通过 Speech.framework 和
AVSpeechSynthesizer 完成，后端仅处理 ASR 转写后的文本。

后端职责：
- 意图分类（规则优先 + LLM 降级）
- Skill 路由（通过 SkillRegistry）
- 返回纯文本回复（由 iOS 端 TTS 播报）

可选 Fallback：
- 云端 ASR（iOS ASR 置信度低时）
- 云端 TTS（需要高品质拟人语音时）
"""
