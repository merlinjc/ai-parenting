"""语音业务服务。

封装 VoicePipeline 调用，提供语音对话和可选的 ASR/TTS 云端 Fallback。

Phase 2 升级：
- process_voice_converse 新增 db + user_id 参数
- VoicePipeline 内部的 quick_record/query_plan 通过 db 真实操作数据库
"""

from __future__ import annotations

import functools
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ai_parenting.backend.voice.intent_classifier import HybridIntentClassifier
from ai_parenting.backend.voice.pipeline import PipelineResult, VoicePipeline

logger = logging.getLogger(__name__)


# P2-7: 使用 functools.lru_cache 代替全局可变单例
@functools.lru_cache(maxsize=1)
def _get_pipeline() -> VoicePipeline:
    """获取 VoicePipeline 单例（懒加载，线程安全）。"""
    intent_classifier = HybridIntentClassifier(
        enable_llm_fallback=False,  # 初期禁用 LLM 降级，仅使用规则
    )

    # 尝试加载 SkillRegistry
    skill_registry = None
    try:
        from ai_parenting.skills import SkillRegistry
        from ai_parenting.skills.adapters.instant_help_adapter import InstantHelpAdapter
        from ai_parenting.skills.adapters.plan_generation_adapter import PlanGenerationAdapter
        from ai_parenting.skills.adapters.weekly_feedback_adapter import WeeklyFeedbackAdapter

        skill_registry = SkillRegistry()
        skill_registry.register(InstantHelpAdapter())
        skill_registry.register(PlanGenerationAdapter())
        skill_registry.register(WeeklyFeedbackAdapter())
        logger.info("VoicePipeline initialized with SkillRegistry (%d skills)", skill_registry.skill_count)
    except Exception as exc:
        logger.warning("SkillRegistry not available for VoicePipeline: %s", exc)

    return VoicePipeline(
        intent_classifier=intent_classifier,
        skill_registry=skill_registry,
    )


async def process_voice_converse(
    transcript: str,
    child_id: uuid.UUID,
    confidence: float | None = None,
    *,
    db: AsyncSession | None = None,
    user_id: uuid.UUID | None = None,
) -> PipelineResult:
    """处理语音对话请求。

    接收 iOS 端 ASR 转写文本，执行意图分类和 Skill 路由，
    返回纯文本回复供 iOS 端 TTS 播报。

    Args:
        transcript: iOS ASR 转写文本。
        child_id: 孩子 ID。
        confidence: iOS ASR 置信度（可选）。
        db: 数据库会话（Phase 2：用于 quick_record 入库和 query_plan 查询）。
        user_id: 当前用户 ID（Phase 2：用于记录关联）。

    Returns:
        PipelineResult 包含回复文本和意图信息。
    """
    pipeline = _get_pipeline()
    result = await pipeline.process_text(
        transcript=transcript,
        child_id=str(child_id),
        asr_confidence=confidence,
        db=db,
        user_id=str(user_id) if user_id else None,
    )
    logger.info(
        "Voice converse: intent=%s, latency=%dms, stages=%s, record_id=%s",
        result.intent, result.latency_ms, result.stages_timing, result.record_id,
    )
    return result


async def transcribe_audio_fallback(
    audio_url: str,
    language: str = "zh-CN",
) -> dict:
    """[Optional] 云端 ASR Fallback。

    当 iOS 端 ASR 置信度低时，调用云端 ASR 增强。
    """
    from ai_parenting.backend.config import settings

    if settings.voice_stt_provider == "tencent_cloud":
        from ai_parenting.backend.voice.stt_provider import TencentCloudSTTProvider
        provider = TencentCloudSTTProvider(
            app_id=settings.tencent_asr_app_id,
            secret_key=settings.tencent_asr_secret_key,
        )
    else:
        from ai_parenting.backend.voice.stt_provider import MockSTTProvider
        provider = MockSTTProvider()

    result = await provider.transcribe(audio_url, language)
    return {
        "transcript": result.transcript,
        "confidence": result.confidence,
        "duration_ms": result.duration_ms,
    }


async def synthesize_text_fallback(
    text: str,
    voice: str = "zh-CN",
) -> dict:
    """[Optional] 云端 TTS Fallback。

    需要高品质拟人语音时，调用云端 TTS。
    """
    from ai_parenting.backend.config import settings

    if settings.voice_tts_provider == "tencent_cloud":
        from ai_parenting.backend.voice.tts_provider import TencentCloudTTSProvider
        provider = TencentCloudTTSProvider(
            app_id=getattr(settings, "tencent_tts_app_id", ""),
            secret_key=getattr(settings, "tencent_tts_secret_key", ""),
        )
    else:
        from ai_parenting.backend.voice.tts_provider import MockTTSProvider
        provider = MockTTSProvider()

    result = await provider.synthesize(text, voice)
    return {
        "audio_url": result.audio_url,
        "duration_ms": result.duration_ms,
        "provider": result.provider,
    }
