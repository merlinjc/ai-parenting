"""非诊断化边界检查器。

实现硬规则层的边界检查，包含：
1. 诊断标签黑名单（V2.0 扩展：细分诊断 + 学科术语）
2. 治疗承诺黑名单（V2.0 扩展：医疗化动词）
3. 绝对判断黑名单
4. 过度量化正则（V2.0 扩展：更多变体匹配）
5. 责备家长表达黑名单（V2.0 扩展：隐性责备）
6. 否定儿童表达黑名单（V2.0 扩展：能力否定 + 性格标签）
7. 比较性语言黑名单（V2.0 新增：横向比较 + 常模对标 + 排名暗示）
8. 字段完整性检查
9. 字符长度检查

支持三种 Result 类型：
- InstantHelpResult
- PlanGenerationResult
- WeeklyFeedbackResult

黑名单词库来源：
- ai_parenting_ai_output_schema_v1.md 第 6.4 节硬规则表
- ai_parenting_prompt_templates_v1.md 第四章禁用词列表
- V2.0 内容专业化安全词库扩展（比较语言控制 + 诊断词库细化）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from ai_parenting.models.schemas import (
    DayTaskContent,
    FeedbackItemContent,
    InstantHelpResult,
    ObservationCandidateContent,
    PlanGenerationResult,
    StepContent,
    WeeklyFeedbackResult,
)


# ---------------------------------------------------------------------------
# 黑名单定义（预编译正则）
# ---------------------------------------------------------------------------

# 1. 诊断标签黑名单（V2.0 扩展：细分诊断 + 学科术语 + 英文缩写）
_DIAGNOSIS_LABELS: list[str] = [
    # --- V1 原有 ---
    "自闭",
    "自闭症",
    "多动",
    "多动症",
    "发育迟缓",
    "语言障碍",
    "感统失调",
    "注意力缺陷",
    "孤独症谱系",
    "智力障碍",
    # --- V2.0 新增：细分诊断名称 ---
    "阿斯伯格",
    "亚斯伯格",
    "唐氏综合征",
    "脑瘫",
    "癫痫",
    "抽动症",
    "对立违抗",
    "品行障碍",
    "分离焦虑障碍",
    "选择性缄默",
    "反应性依恋障碍",
    "言语失用",
    "构音障碍",
    "口吃",
    # --- V2.0 新增：学科术语（家长不应在日常指导中看到） ---
    "感觉统合失调",
    "感觉寻求",
    "感觉回避",
    "前庭觉",
    "本体觉",
    "触觉防御",
    "ASD",
    "ADHD",
    "SPD",
    "ODD",
]
_DIAGNOSIS_PATTERN: re.Pattern[str] = re.compile(
    "|".join(re.escape(w) for w in _DIAGNOSIS_LABELS)
)
_DIAGNOSIS_REPLACEMENT: str = "如果持续担心，建议咨询专业人士"

# 2. 治疗承诺黑名单（V2.0 扩展：医疗化动词 + 干预术语）
_TREATMENT_PROMISES: list[str] = [
    # --- V1 原有 ---
    "治愈",
    "矫正",
    "根治",
    "训练好",
    "康复",
    "纠正",
    # --- V2.0 新增：医疗化动词 ---
    "治疗",
    "干预",
    "矫治",
    "修复",
    "恢复正常",
    "变正常",
    "回到正轨",
    # --- V2.0 新增：训练导向表达 ---
    "强化训练",
    "密集训练",
    "系统训练",
    "脱敏训练",
    "行为矫正",
    "早期干预",
]
_TREATMENT_PATTERN: re.Pattern[str] = re.compile(
    "|".join(re.escape(w) for w in _TREATMENT_PROMISES)
)
_TREATMENT_REPLACEMENTS: dict[str, str] = {
    # --- V1 原有 ---
    "治愈": "帮助",
    "矫正": "支持",
    "根治": "帮助",
    "训练好": "给更多机会",
    "康复": "支持",
    "纠正": "帮助",
    # --- V2.0 新增 ---
    "治疗": "支持",
    "干预": "帮助",
    "矫治": "支持",
    "修复": "帮助",
    "恢复正常": "继续在日常中给机会",
    "变正常": "继续自然发展",
    "回到正轨": "按自己的节奏成长",
    "强化训练": "多一些自然练习机会",
    "密集训练": "在日常生活中多给机会",
    "系统训练": "在自然场景中持续支持",
    "脱敏训练": "逐步熟悉新体验",
    "行为矫正": "帮助建立新习惯",
    "早期干预": "早期支持",
}

# 3. 绝对判断黑名单
_ABSOLUTE_JUDGMENTS: list[str] = [
    "一定",
    "肯定",
    "必须",
    "不能不",
    "绝对",
    "百分之百",
]
_ABSOLUTE_PATTERN: re.Pattern[str] = re.compile(
    "|".join(re.escape(w) for w in _ABSOLUTE_JUDGMENTS)
)
_ABSOLUTE_REPLACEMENTS: dict[str, str] = {
    "一定": "可以试试",
    "肯定": "通常",
    "必须": "可以试试",
    "不能不": "可以试试",
    "绝对": "通常",
    "百分之百": "很多家庭发现",
}

# 4. 过度量化正则（V2.0 扩展：更多变体模式）
_OVERQUANTIFY_PATTERN: re.Pattern[str] = re.compile(
    r"每天必须\s*\d+\s*次"
    r"|必须坚持\s*\d+\s*天"
    r"|达到\s*\d+\s*分钟"
    r"|每天至少\s*\d+\s*次"
    r"|一天\s*\d+\s*次以上"
    r"|不少于\s*\d+\s*(?:次|分钟|小时)"
    r"|保证每天\s*\d+\s*(?:次|分钟)"
    r"|必须完成\s*\d+\s*(?:次|个|组)"
    r"|每日\s*\d+\s*次训练"
)
_OVERQUANTIFY_REPLACEMENT: str = "尝试在自然时机中融入"

# 5. 责备家长表达（V2.0 扩展：隐性责备 + 内疚归因）
_BLAME_PARENT_PATTERNS: list[str] = [
    # --- V1 原有 ---
    "你应该早点注意到",
    "如果你之前就",
    "你做错了",
    "你没有",
    # --- V2.0 新增：隐性责备 ---
    "你怎么到现在才",
    "你为什么不早点",
    "都怪你",
    "都是因为你",
    "你耽误了",
    "错过了最佳",
    "错过了关键期",
    "你忽视了",
    "你忽略了",
    # --- V2.0 新增：内疚归因 ---
    "如果你当时",
    "早知道你",
    "你要是能",
    "本来可以避免",
    "你造成了",
    "你导致了",
]
_BLAME_PARENT_PATTERN: re.Pattern[str] = re.compile(
    "|".join(re.escape(w) for w in _BLAME_PARENT_PATTERNS)
)
_BLAME_PARENT_REPLACEMENT: str = "你的关注本身就是支持"

# 6. 否定儿童表达（V2.0 扩展：能力否定 + 性格标签 + 消极预期）
_NEGATE_CHILD_PATTERNS: list[str] = [
    # --- V1 原有 ---
    "做不到",
    "学不会",
    "不正常",
    "有问题",
    "落后",
    # --- V2.0 新增：能力否定 ---
    "不行",
    "不会",
    "不能",
    "缺乏能力",
    "能力不足",
    "水平低",
    "太差",
    "太慢",
    # --- V2.0 新增：性格/特质标签 ---
    "太内向",
    "太胆小",
    "太黏人",
    "太倔",
    "太固执",
    "不听话",
    "不乖",
    "不懂事",
    "笨",
    "傻",
    "懒",
    # --- V2.0 新增：消极预期 ---
    "以后会有问题",
    "将来会",
    "长大了也",
    "一辈子",
]
_NEGATE_CHILD_PATTERN: re.Pattern[str] = re.compile(
    "|".join(re.escape(w) for w in _NEGATE_CHILD_PATTERNS)
)
_NEGATE_CHILD_REPLACEMENT: str = "还在发展中"

# 7. 比较性语言黑名单（V2.0 新增：横向比较 + 常模对标 + 排名暗示）
_COMPARE_CHILD_PHRASES: list[str] = [
    # --- 横向比较：与其他孩子直接对比 ---
    "别人家的孩子",
    "别的孩子",
    "其他孩子都",
    "同龄孩子都",
    "同龄的孩子已经",
    "人家孩子",
    "正常孩子",
    "正常的孩子",
    "一般孩子",
    "大部分孩子都能",
    "大多数孩子已经",
    "你看别人",
    "你看人家",
    "隔壁家",
    "邻居家的",
    # --- 常模对标：用统计标准衡量个体 ---
    "达标",
    "未达标",
    "不达标",
    "低于平均",
    "低于标准",
    "高于平均",
    "评分",
    "打分",
    "得分",
    "百分位",
    "百分等级",
    "标准分",
    # --- 排名暗示：隐含竞争和排序 ---
    "排名",
    "第几名",
    "倒数",
    "垫底",
    "领先",
    "超过",
    "落后于",
    "赶不上",
    "追不上",
    "跟不上",
    "比不上",
    "不如",
]
_COMPARE_CHILD_PATTERN: re.Pattern[str] = re.compile(
    "|".join(re.escape(w) for w in _COMPARE_CHILD_PHRASES)
)
_COMPARE_CHILD_REPLACEMENTS: dict[str, str] = {
    # 横向比较替换
    "别人家的孩子": "每个孩子",
    "别的孩子": "每个孩子",
    "其他孩子都": "很多家庭发现",
    "同龄孩子都": "这个年龄段的孩子各有自己的节奏",
    "同龄的孩子已经": "有些孩子在这方面发展得早一些",
    "人家孩子": "每个孩子",
    "正常孩子": "多数孩子",
    "正常的孩子": "多数孩子",
    "一般孩子": "很多孩子",
    "大部分孩子都能": "不少孩子在这个阶段开始",
    "大多数孩子已经": "有些孩子已经在尝试",
    "你看别人": "咱们来看看孩子自己的变化",
    "你看人家": "咱们来看看孩子自己的变化",
    "隔壁家": "咱们家孩子",
    "邻居家的": "咱们家孩子",
    # 常模对标替换
    "达标": "在发展中",
    "未达标": "还在发展中",
    "不达标": "还在发展中",
    "低于平均": "正在按自己的节奏发展",
    "低于标准": "正在按自己的节奏发展",
    "高于平均": "在这方面发展得不错",
    # 排名暗示替换
    "落后于": "和之前相比",
    "赶不上": "按自己的节奏在成长",
    "追不上": "按自己的节奏在成长",
    "跟不上": "按自己的节奏在成长",
    "比不上": "和之前的自己比",
    "不如": "和之前的自己比",
}
_COMPARE_CHILD_DEFAULT_REPLACEMENT: str = "跟自己的上周比"

# ---------------------------------------------------------------------------
# 字段长度约束（按 Result 类型分类）
# ---------------------------------------------------------------------------

_INSTANT_HELP_FIELD_LIMITS: dict[str, int] = {
    "step_one.title": 20,
    "step_one.body": 200,
    "step_one.example_script": 100,
    "step_two.title": 20,
    "step_two.body": 300,
    "step_two.example_script": 100,
    "step_three.title": 20,
    "step_three.body": 300,
    "step_three.example_script": 100,
    "scenario_summary": 80,
    "consult_prep_reason": 100,
    "boundary_note": 150,
}

_PLAN_GENERATION_FIELD_LIMITS: dict[str, int] = {
    "title": 30,
    "primary_goal": 100,
    "weekend_review_prompt": 200,
    "conservative_note": 200,
}

# DayTask 字段限制（按 day_tasks[n].field 的模式）
_DAY_TASK_FIELD_LIMITS: dict[str, int] = {
    "main_exercise_title": 25,
    "main_exercise_description": 300,
    "natural_embed_title": 25,
    "natural_embed_description": 300,
    "demo_script": 150,
    "observation_point": 150,
}

# ObservationCandidate 字段限制
_OBSERVATION_CANDIDATE_FIELD_LIMITS: dict[str, int] = {
    "text": 30,
}

_WEEKLY_FEEDBACK_FIELD_LIMITS: dict[str, int] = {
    "summary_text": 300,
    "conservative_path_note": 200,
}

# FeedbackItem 字段限制
_FEEDBACK_ITEM_FIELD_LIMITS: dict[str, int] = {
    "title": 25,
    "description": 200,
    "supporting_evidence": 100,
}

# DecisionOption 字段限制
_DECISION_OPTION_FIELD_LIMITS: dict[str, int] = {
    "text": 30,
    "rationale": 100,
}


# ---------------------------------------------------------------------------
# 检查结果数据类
# ---------------------------------------------------------------------------


@dataclass
class BoundaryFlag:
    """单条检查标记。"""

    category: str  # 检查类别（如 "diagnosis_label"）
    field_path: str  # 被标记的字段路径（如 "step_one.body"）
    original_text: str  # 原始文本片段
    replacement: str  # 替换后文本


@dataclass
class BoundaryCheckOutput:
    """边界检查完整输出。"""

    passed: bool = True
    flags: list[BoundaryFlag] = field(default_factory=list)
    cleaned_result: BaseModel | None = None


# ---------------------------------------------------------------------------
# 边界检查器
# ---------------------------------------------------------------------------


class BoundaryChecker:
    """非诊断化边界检查器。

    对 InstantHelpResult / PlanGenerationResult / WeeklyFeedbackResult
    的所有文本字段执行硬规则检查：
    - 诊断标签黑名单（V2.0 扩展）
    - 治疗承诺黑名单（V2.0 扩展）
    - 绝对判断黑名单
    - 过度量化正则（V2.0 扩展）
    - 责备家长表达（V2.0 扩展）
    - 否定儿童表达（V2.0 扩展）
    - 比较性语言（V2.0 新增）
    - 字段完整性
    - 字符长度

    用法::

        checker = BoundaryChecker()
        output = checker.check(result)
        if output.passed:
            # 全部通过
        else:
            # output.flags 中包含被标记的项
            # output.cleaned_result 为替换后的结果
    """

    def check(self, result: BaseModel) -> BoundaryCheckOutput:
        """对任意 Result 类型执行完整边界检查。

        Args:
            result: 待检查的 Result（InstantHelpResult / PlanGenerationResult / WeeklyFeedbackResult）。

        Returns:
            BoundaryCheckOutput，包含通过状态、标记列表和清洁结果。
        """
        flags: list[BoundaryFlag] = []

        # 收集所有需要检查的文本字段
        text_fields = self._extract_text_fields(result)

        # 执行七类黑名单检查
        for field_path, text in text_fields.items():
            if text is None:
                continue
            flags.extend(self._check_diagnosis_labels(field_path, text))
            flags.extend(self._check_treatment_promises(field_path, text))
            flags.extend(self._check_absolute_judgments(field_path, text))
            flags.extend(self._check_overquantify(field_path, text))
            flags.extend(self._check_blame_parent(field_path, text))
            flags.extend(self._check_negate_child(field_path, text))
            flags.extend(self._check_compare_child(field_path, text))

        # 字段完整性检查
        flags.extend(self._check_field_completeness(result))

        # 字符长度检查
        length_limits = self._get_field_length_limits(result)
        flags.extend(self._check_field_lengths(text_fields, length_limits))

        passed = len(flags) == 0
        cleaned_result = None
        if not passed:
            cleaned_result = self._build_cleaned_result(result, flags)

        return BoundaryCheckOutput(
            passed=passed,
            flags=flags,
            cleaned_result=cleaned_result,
        )

    # ------------------------------------------------------------------
    # 内部方法：提取文本字段（泛化）
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text_fields(result: BaseModel) -> dict[str, str | None]:
        """提取所有需要检查的文本字段。

        根据 result 的具体类型，提取相应的文本字段路径和值。
        """
        fields: dict[str, str | None] = {}

        if isinstance(result, InstantHelpResult):
            for step_name in ("step_one", "step_two", "step_three"):
                step: StepContent = getattr(result, step_name)
                fields[f"{step_name}.title"] = step.title
                fields[f"{step_name}.body"] = step.body
                fields[f"{step_name}.example_script"] = step.example_script
            fields["scenario_summary"] = result.scenario_summary
            fields["consult_prep_reason"] = result.consult_prep_reason
            fields["boundary_note"] = result.boundary_note

        elif isinstance(result, PlanGenerationResult):
            fields["title"] = result.title
            fields["primary_goal"] = result.primary_goal
            fields["weekend_review_prompt"] = result.weekend_review_prompt
            fields["conservative_note"] = result.conservative_note
            for i, scene in enumerate(result.priority_scenes):
                fields[f"priority_scenes[{i}]"] = scene
            for task in result.day_tasks:
                prefix = f"day_tasks[{task.day_number - 1}]"
                fields[f"{prefix}.main_exercise_title"] = task.main_exercise_title
                fields[f"{prefix}.main_exercise_description"] = task.main_exercise_description
                fields[f"{prefix}.natural_embed_title"] = task.natural_embed_title
                fields[f"{prefix}.natural_embed_description"] = task.natural_embed_description
                fields[f"{prefix}.demo_script"] = task.demo_script
                fields[f"{prefix}.observation_point"] = task.observation_point
            for i, oc in enumerate(result.observation_candidates):
                fields[f"observation_candidates[{i}].text"] = oc.text

        elif isinstance(result, WeeklyFeedbackResult):
            fields["summary_text"] = result.summary_text
            fields["conservative_path_note"] = result.conservative_path_note
            for i, item in enumerate(result.positive_changes):
                fields[f"positive_changes[{i}].title"] = item.title
                fields[f"positive_changes[{i}].description"] = item.description
                fields[f"positive_changes[{i}].supporting_evidence"] = item.supporting_evidence
            for i, item in enumerate(result.opportunities):
                fields[f"opportunities[{i}].title"] = item.title
                fields[f"opportunities[{i}].description"] = item.description
                if item.supporting_evidence:
                    fields[f"opportunities[{i}].supporting_evidence"] = item.supporting_evidence
            for i, opt in enumerate(result.decision_options):
                fields[f"decision_options[{i}].text"] = opt.text
                fields[f"decision_options[{i}].rationale"] = opt.rationale

        return fields

    # ------------------------------------------------------------------
    # 内部方法：获取字段长度限制（按类型分派）
    # ------------------------------------------------------------------

    @staticmethod
    def _get_field_length_limits(result: BaseModel) -> dict[str, int]:
        """根据 Result 类型返回对应的字段长度限制字典。"""
        limits: dict[str, int] = {}

        if isinstance(result, InstantHelpResult):
            limits.update(_INSTANT_HELP_FIELD_LIMITS)

        elif isinstance(result, PlanGenerationResult):
            limits.update(_PLAN_GENERATION_FIELD_LIMITS)
            for i in range(len(result.priority_scenes)):
                limits[f"priority_scenes[{i}]"] = 15
            for task in result.day_tasks:
                prefix = f"day_tasks[{task.day_number - 1}]"
                for field_name, limit in _DAY_TASK_FIELD_LIMITS.items():
                    limits[f"{prefix}.{field_name}"] = limit
            for i in range(len(result.observation_candidates)):
                for field_name, limit in _OBSERVATION_CANDIDATE_FIELD_LIMITS.items():
                    limits[f"observation_candidates[{i}].{field_name}"] = limit

        elif isinstance(result, WeeklyFeedbackResult):
            limits.update(_WEEKLY_FEEDBACK_FIELD_LIMITS)
            for i in range(len(result.positive_changes)):
                for field_name, limit in _FEEDBACK_ITEM_FIELD_LIMITS.items():
                    limits[f"positive_changes[{i}].{field_name}"] = limit
            for i in range(len(result.opportunities)):
                for field_name, limit in _FEEDBACK_ITEM_FIELD_LIMITS.items():
                    limits[f"opportunities[{i}].{field_name}"] = limit
            for i in range(len(result.decision_options)):
                for field_name, limit in _DECISION_OPTION_FIELD_LIMITS.items():
                    limits[f"decision_options[{i}].{field_name}"] = limit

        return limits

    # ------------------------------------------------------------------
    # 内部方法：各类黑名单检查
    # ------------------------------------------------------------------

    @staticmethod
    def _check_diagnosis_labels(
        field_path: str, text: str
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []
        for match in _DIAGNOSIS_PATTERN.finditer(text):
            flags.append(
                BoundaryFlag(
                    category="diagnosis_label",
                    field_path=field_path,
                    original_text=match.group(),
                    replacement=_DIAGNOSIS_REPLACEMENT,
                )
            )
        return flags

    @staticmethod
    def _check_treatment_promises(
        field_path: str, text: str
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []
        for match in _TREATMENT_PATTERN.finditer(text):
            word = match.group()
            flags.append(
                BoundaryFlag(
                    category="treatment_promise",
                    field_path=field_path,
                    original_text=word,
                    replacement=_TREATMENT_REPLACEMENTS.get(word, "支持"),
                )
            )
        return flags

    @staticmethod
    def _check_absolute_judgments(
        field_path: str, text: str
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []
        for match in _ABSOLUTE_PATTERN.finditer(text):
            word = match.group()
            flags.append(
                BoundaryFlag(
                    category="absolute_judgment",
                    field_path=field_path,
                    original_text=word,
                    replacement=_ABSOLUTE_REPLACEMENTS.get(word, "可以试试"),
                )
            )
        return flags

    @staticmethod
    def _check_overquantify(
        field_path: str, text: str
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []
        for match in _OVERQUANTIFY_PATTERN.finditer(text):
            flags.append(
                BoundaryFlag(
                    category="overquantify",
                    field_path=field_path,
                    original_text=match.group(),
                    replacement=_OVERQUANTIFY_REPLACEMENT,
                )
            )
        return flags

    @staticmethod
    def _check_blame_parent(
        field_path: str, text: str
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []
        for match in _BLAME_PARENT_PATTERN.finditer(text):
            flags.append(
                BoundaryFlag(
                    category="blame_parent",
                    field_path=field_path,
                    original_text=match.group(),
                    replacement=_BLAME_PARENT_REPLACEMENT,
                )
            )
        return flags

    @staticmethod
    def _check_negate_child(
        field_path: str, text: str
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []
        for match in _NEGATE_CHILD_PATTERN.finditer(text):
            flags.append(
                BoundaryFlag(
                    category="negate_child",
                    field_path=field_path,
                    original_text=match.group(),
                    replacement=_NEGATE_CHILD_REPLACEMENT,
                )
            )
        return flags

    @staticmethod
    def _check_compare_child(
        field_path: str, text: str
    ) -> list[BoundaryFlag]:
        """V2.0 新增：检查比较性语言（横向比较、常模对标、排名暗示）。"""
        flags: list[BoundaryFlag] = []
        for match in _COMPARE_CHILD_PATTERN.finditer(text):
            word = match.group()
            flags.append(
                BoundaryFlag(
                    category="compare_child",
                    field_path=field_path,
                    original_text=word,
                    replacement=_COMPARE_CHILD_REPLACEMENTS.get(
                        word, _COMPARE_CHILD_DEFAULT_REPLACEMENT
                    ),
                )
            )
        return flags

    # ------------------------------------------------------------------
    # 内部方法：字段完整性检查（泛化）
    # ------------------------------------------------------------------

    @staticmethod
    def _check_field_completeness(
        result: BaseModel,
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []

        if isinstance(result, InstantHelpResult):
            for step_name in ("step_one", "step_two", "step_three"):
                step: StepContent = getattr(result, step_name)
                if not step.title or not step.title.strip():
                    flags.append(
                        BoundaryFlag(
                            category="field_completeness",
                            field_path=f"{step_name}.title",
                            original_text="(empty)",
                            replacement="(需要填写)",
                        )
                    )
                if not step.body or not step.body.strip():
                    flags.append(
                        BoundaryFlag(
                            category="field_completeness",
                            field_path=f"{step_name}.body",
                            original_text="(empty)",
                            replacement="(需要填写)",
                        )
                    )

        elif isinstance(result, PlanGenerationResult):
            if not result.title or not result.title.strip():
                flags.append(
                    BoundaryFlag(
                        category="field_completeness",
                        field_path="title",
                        original_text="(empty)",
                        replacement="(需要填写)",
                    )
                )
            for task in result.day_tasks:
                prefix = f"day_tasks[{task.day_number - 1}]"
                for field_name in ("main_exercise_title", "main_exercise_description", "demo_script"):
                    val = getattr(task, field_name)
                    if not val or not val.strip():
                        flags.append(
                            BoundaryFlag(
                                category="field_completeness",
                                field_path=f"{prefix}.{field_name}",
                                original_text="(empty)",
                                replacement="(需要填写)",
                            )
                        )

        elif isinstance(result, WeeklyFeedbackResult):
            if not result.summary_text or not result.summary_text.strip():
                flags.append(
                    BoundaryFlag(
                        category="field_completeness",
                        field_path="summary_text",
                        original_text="(empty)",
                        replacement="(需要填写)",
                    )
                )

        return flags

    # ------------------------------------------------------------------
    # 内部方法：字符长度检查
    # ------------------------------------------------------------------

    @staticmethod
    def _check_field_lengths(
        text_fields: dict[str, str | None],
        length_limits: dict[str, int],
    ) -> list[BoundaryFlag]:
        flags: list[BoundaryFlag] = []
        for field_path, text in text_fields.items():
            if text is None:
                continue
            limit = length_limits.get(field_path)
            if limit is not None and len(text) > limit:
                flags.append(
                    BoundaryFlag(
                        category="field_length",
                        field_path=field_path,
                        original_text=f"长度 {len(text)} 超过限制 {limit}",
                        replacement=text[:limit],
                    )
                )
        return flags

    # ------------------------------------------------------------------
    # 内部方法：构建清洁结果（泛化）
    # ------------------------------------------------------------------

    def _build_cleaned_result(
        self,
        result: BaseModel,
        flags: list[BoundaryFlag],
    ) -> BaseModel:
        """基于原始结果和检查标记，构建替换后的清洁结果。"""
        # 将原始结果序列化为 dict
        data = result.model_dump()

        # 按字段路径收集需要替换的内容
        for flag in flags:
            if flag.category == "field_completeness":
                continue  # 完整性问题无法通过替换修复
            if flag.category == "field_length":
                # 截断处理
                self._set_nested(data, flag.field_path, flag.replacement)
                continue
            # 文本替换
            current = self._get_nested(data, flag.field_path)
            if current is not None and isinstance(current, str):
                new_text = current.replace(
                    flag.original_text, flag.replacement
                )
                self._set_nested(data, flag.field_path, new_text)

        return type(result).model_validate(data)

    @staticmethod
    def _get_nested(data: dict, path: str) -> str | None:
        """获取嵌套字典中的值。

        支持以下路径格式：
        - 'step_one.body' → data['step_one']['body']
        - 'day_tasks[0].demo_script' → data['day_tasks'][0]['demo_script']
        - 'priority_scenes[0]' → data['priority_scenes'][0]
        """
        current: Any = data
        for part in _parse_path(path):
            if isinstance(part, int):
                if isinstance(current, list) and 0 <= part < len(current):
                    current = current[part]
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            if current is None:
                return None
        return current  # type: ignore[return-value]

    @staticmethod
    def _set_nested(data: dict, path: str, value: str) -> None:
        """设置嵌套字典中的值。"""
        parts = _parse_path(path)
        current: Any = data
        for part in parts[:-1]:
            if isinstance(part, int):
                current = current[part]
            else:
                current = current[part]
        last = parts[-1]
        if isinstance(last, int):
            current[last] = value
        else:
            current[last] = value


# ---------------------------------------------------------------------------
# 路径解析工具
# ---------------------------------------------------------------------------

import re as _re

_PATH_SEGMENT_RE = _re.compile(r"(\w+)(?:\[(\d+)\])?")


def _parse_path(path: str) -> list[str | int]:
    """将路径字符串解析为键/索引序列。

    Examples:
        'step_one.body' → ['step_one', 'body']
        'day_tasks[0].demo_script' → ['day_tasks', 0, 'demo_script']
        'priority_scenes[0]' → ['priority_scenes', 0]
    """
    parts: list[str | int] = []
    for segment in path.split("."):
        m = _PATH_SEGMENT_RE.fullmatch(segment)
        if m:
            parts.append(m.group(1))
            if m.group(2) is not None:
                parts.append(int(m.group(2)))
        else:
            parts.append(segment)
    return parts
