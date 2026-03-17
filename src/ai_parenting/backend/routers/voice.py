"""语音 API 路由。

iOS 原生优先策略：ASR/TTS 在 iOS 端完成，后端仅处理意图分类和 Skill 路由。

端点列表：
- POST /voice/converse    — 核心端点：接收 ASR 文本 → 意图分类 → Skill → 返回文本
- POST /voice/transcribe  — [Optional] 云端 ASR Fallback
- POST /voice/synthesize  — [Optional] 云端 TTS Fallback

Phase 2 升级：
- /voice/converse 注入 db 和 user_id，支持快速记录入库和计划查询
- /voice/synthesize 端点实现
- 响应增加 record_id 字段
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.auth import get_current_user_id
from ai_parenting.backend.database import get_db
from ai_parenting.backend.schemas import (
    VoiceConverseRequest,
    VoiceConverseResponse,
    VoiceTranscribeRequest,
    VoiceTranscribeResponse,
)
from ai_parenting.backend.services import voice_service

router = APIRouter(prefix="/voice", tags=["voice"])


# ---------------------------------------------------------------------------
# 额外的请求/响应模型
# ---------------------------------------------------------------------------


class VoiceSynthesizeRequest(BaseModel):
    """云端 TTS 请求。"""

    text: str = Field(..., min_length=1, max_length=5000, description="要合成的文本")
    voice: str = Field(default="zh-CN", description="语音语言")


class VoiceSynthesizeResponse(BaseModel):
    """云端 TTS 响应。"""

    audio_url: str | None = None
    duration_ms: int | None = None
    provider: str = "unknown"


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------


@router.post("/converse", response_model=VoiceConverseResponse)
async def voice_converse(
    body: VoiceConverseRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> VoiceConverseResponse:
    """语音对话核心端点。

    接收 iOS 端 Speech.framework 转写后的文本，
    执行意图分类和 Skill 路由，返回纯文本回复。
    iOS 端使用 AVSpeechSynthesizer 本地 TTS 播报。

    Phase 2 升级：
    - 注入 db session，quick_record 真实写入 Record 表
    - 注入 user_id，query_plan 查询当前用户的活跃计划
    - 响应增加 record_id 字段

    流程：
    1. iOS: 用户说话 → SFSpeechRecognizer 流式 ASR → 获得 transcript
    2. iOS → 后端: POST /voice/converse {transcript, child_id, confidence}
    3. 后端: IntentClassifier(规则→LLM) → SkillRouter → 生成文本回复
    4. 后端 → iOS: {reply_text, intent, action_taken, record_id}
    5. iOS: AVSpeechSynthesizer 播报 reply_text

    端到端延迟：< 500ms（规则命中） / < 1.5s（LLM 意图）
    """
    result = await voice_service.process_voice_converse(
        transcript=body.transcript,
        child_id=body.child_id,
        confidence=body.confidence,
        db=db,
        user_id=user_id,
    )

    return VoiceConverseResponse(
        reply_text=result.reply_text,
        intent=result.intent,
        action_taken=result.action_taken,
        should_fallback_to_cloud_asr=result.should_fallback_to_cloud_asr,
        record_id=result.record_id,
    )


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def voice_transcribe(
    body: VoiceTranscribeRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> VoiceTranscribeResponse:
    """[Optional] 云端 ASR Fallback。

    当 iOS 端 ASR 置信度低于阈值（默认 0.6）时，
    iOS 端可将音频上传到此端点进行云端 ASR 增强。
    """
    result = await voice_service.transcribe_audio_fallback(
        audio_url=body.audio_url,
        language=body.language,
    )
    return VoiceTranscribeResponse(**result)


@router.post("/synthesize", response_model=VoiceSynthesizeResponse)
async def voice_synthesize(
    body: VoiceSynthesizeRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> VoiceSynthesizeResponse:
    """[Optional] 云端 TTS Fallback。

    iOS 端默认使用 AVSpeechSynthesizer 本地 TTS。
    当需要高品质拟人语音时（如周反馈播报），
    可调用此端点获取云端合成的音频 URL。
    """
    result = await voice_service.synthesize_text_fallback(
        text=body.text,
        voice=body.voice,
    )
    return VoiceSynthesizeResponse(**result)
