"""混合意图分类器。

策略：规则匹配优先（关键词+正则，延迟 < 5ms），
未命中时降级到 LLM 分类（延迟约 200-500ms）。

规则匹配预期命中率 70-80%，覆盖高频语音指令：
- "记录" 类：快速语音记录
- "计划/任务" 类：查询今日任务
- "求助/怎么办" 类：即时求助
- "反馈/总结" 类：查看周反馈
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ai_parenting.backend.voice.pipeline import IntentClassifierStage, IntentResult

logger = logging.getLogger(__name__)


@dataclass
class IntentRule:
    """意图匹配规则。"""

    intent: str
    keywords: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)  # 正则表达式
    priority: int = 0  # 优先级，越高越优先
    extract_params: bool = False  # 是否从文本中提取参数


# ---------------------------------------------------------------------------
# 内置规则库
# ---------------------------------------------------------------------------

INTENT_RULES: list[IntentRule] = [
    # 快速记录（最高频）
    IntentRule(
        intent="quick_record",
        keywords=["记录", "记一下", "记下来", "帮我记", "备注"],
        patterns=[
            r"^记录(.+)",
            r"^帮我记[一下录]?(.+)",
            r"^记[一下](.+)",
        ],
        priority=100,
        extract_params=True,
    ),
    # 查询今日计划
    IntentRule(
        intent="query_plan",
        keywords=["今天做什么", "今日任务", "今天的任务", "今日计划", "今天安排"],
        patterns=[
            r"今天.*(?:做什么|任务|计划|安排)",
            r"(?:查看|查|看看).*(?:今天|今日).*(?:任务|计划)",
        ],
        priority=90,
    ),
    # 进度查询（Phase 2 新增）
    IntentRule(
        intent="query_progress",
        keywords=["完成多少", "进度", "完成率", "打卡", "坚持多少天", "连续多少天"],
        patterns=[
            r".*(?:这周|本周).*(?:完成|进度|进展)",
            r".*(?:完成|做)了多少",
            r".*(?:打卡|坚持|连续).*(?:多少|几)天",
            r".*(?:进度|进展)(?:怎么样|如何|咋样)",
        ],
        priority=85,
    ),
    # 即时求助
    IntentRule(
        intent="instant_help",
        keywords=["怎么办", "求助", "帮帮我", "不知道怎么", "怎么处理"],
        patterns=[
            r".*怎么办",
            r".*(?:不肯|不愿|不想|哭闹|发脾气|打人|咬人)",
            r".*(?:该怎么|如何|咋办)",
        ],
        priority=80,
    ),
    # 查看周反馈
    IntentRule(
        intent="weekly_feedback",
        keywords=["周反馈", "本周反馈", "周总结", "本周总结", "成长报告"],
        patterns=[
            r".*(?:周|本周).*(?:反馈|总结|报告)",
            r".*(?:进展|成长).*(?:怎么样|如何)",
        ],
        priority=70,
    ),
    # 语音记录（长内容）
    IntentRule(
        intent="voice_record",
        keywords=["语音记录", "录音记录"],
        patterns=[
            r"^(?:开始)?语音记录",
        ],
        priority=60,
    ),
]


class HybridIntentClassifier(IntentClassifierStage):
    """混合意图分类器。

    两阶段策略：
    1. 规则匹配（关键词 + 正则），延迟 < 5ms，命中率 70-80%
    2. LLM 降级分类，延迟 200-500ms，命中率 95%+

    通过配置开关控制是否启用 LLM 降级。
    """

    def __init__(
        self,
        rules: list[IntentRule] | None = None,
        enable_llm_fallback: bool = True,
        llm_provider: Any = None,
    ) -> None:
        self._rules = sorted(
            rules or INTENT_RULES,
            key=lambda r: r.priority,
            reverse=True,
        )
        self._enable_llm_fallback = enable_llm_fallback
        self._llm_provider = llm_provider
        # 预编译正则表达式
        self._compiled_patterns: dict[str, list[re.Pattern]] = {}
        for rule in self._rules:
            self._compiled_patterns[rule.intent] = [
                re.compile(p, re.IGNORECASE) for p in rule.patterns
            ]

    @property
    def stage_name(self) -> str:
        return "hybrid_intent_classifier"

    async def process(self, input_data: str, context: dict[str, Any]) -> IntentResult:
        """分类意图。

        Args:
            input_data: ASR 转写文本。
            context: 上下文信息（如 child_id）。

        Returns:
            IntentResult，包含意图名称、置信度和匹配方式。
        """
        text = input_data.strip()
        if not text:
            return IntentResult(
                intent="unknown",
                confidence=0.0,
                matched_by="empty",
            )

        # Phase 1: 规则匹配
        result = self._match_by_rules(text)
        if result is not None:
            return result

        # Phase 2: LLM 降级
        if self._enable_llm_fallback and self._llm_provider:
            result = await self._classify_by_llm(text, context)
            if result is not None:
                return result

        # 兜底：未识别意图
        return IntentResult(
            intent="unknown",
            confidence=0.3,
            matched_by="fallback",
        )

    def _match_by_rules(self, text: str) -> IntentResult | None:
        """规则匹配阶段。"""
        for rule in self._rules:
            # 关键词匹配
            for keyword in rule.keywords:
                if keyword in text:
                    params = {}
                    if rule.extract_params:
                        params = self._extract_params(text, rule, keyword)
                    return IntentResult(
                        intent=rule.intent,
                        confidence=0.9,
                        matched_by="rule_keyword",
                        parameters=params,
                    )

            # 正则匹配
            for pattern in self._compiled_patterns.get(rule.intent, []):
                match = pattern.search(text)
                if match:
                    params = {}
                    if rule.extract_params and match.groups():
                        params["content"] = match.group(1).strip()
                    return IntentResult(
                        intent=rule.intent,
                        confidence=0.85,
                        matched_by="rule_pattern",
                        parameters=params,
                    )

        return None

    def _extract_params(self, text: str, rule: IntentRule, keyword: str) -> dict[str, Any]:
        """从文本中提取参数。"""
        params: dict[str, Any] = {}

        # 对于 quick_record，提取关键词后面的内容
        if rule.intent == "quick_record":
            idx = text.find(keyword)
            if idx >= 0:
                content = text[idx + len(keyword):].strip()
                # 去掉常见的连接词
                content = re.sub(r"^[一下了：:，,\s]+", "", content)
                if content:
                    params["content"] = content

        return params

    async def _classify_by_llm(
        self, text: str, context: dict[str, Any]
    ) -> IntentResult | None:
        """LLM 降级分类。

        使用 AI 模型对未命中规则的文本进行意图分类。
        """
        if self._llm_provider is None:
            return None

        prompt = (
            "你是一个育儿 App 的意图分类器。用户通过语音说了以下内容，"
            "请判断用户的意图并返回 JSON 格式结果。\n\n"
            "可选意图：\n"
            "- quick_record: 记录孩子的行为观察\n"
            "- query_plan: 查询今天的训练计划/任务\n"
            "- query_progress: 查询训练进度/完成率/连续打卡天数\n"
            "- instant_help: 遇到育儿问题求助\n"
            "- weekly_feedback: 查看本周反馈总结\n"
            "- unknown: 无法识别\n\n"
            f"用户说：「{text}」\n\n"
            '请返回 JSON：{{"intent": "...", "confidence": 0.0-1.0}}'
        )

        try:
            raw = await self._llm_provider.generate(prompt)
            # 解析 JSON 响应
            import json
            data = json.loads(raw)
            return IntentResult(
                intent=data.get("intent", "unknown"),
                confidence=data.get("confidence", 0.7),
                matched_by="llm",
            )
        except Exception as exc:
            logger.error("LLM intent classification failed: %s", exc)
            return None
