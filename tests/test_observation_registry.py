"""测试：观察项注册表。"""

from ai_parenting.content.observation_registry import (
    ALL_ITEMS,
    STAGE_PRIORITY_THEMES,
    get_active_items,
    get_daily_items,
    get_item,
    get_items_by_focus,
    get_items_by_stage,
    get_items_by_theme,
)
from ai_parenting.models.enums import ChildStage, DevTheme, InterventionFocus


class TestRegistryBasics:
    """注册表基础验证。"""

    def test_total_items(self):
        """72 条观察项（V1 54 + V2.0 新增 18）。"""
        assert len(ALL_ITEMS) == 72

    def test_items_per_stage(self):
        """每阶段 24 条（6 原主题 × 3 + 2 新主题 × 3）。"""
        for stage in ChildStage:
            items = get_items_by_stage(stage)
            assert len(items) == 24, f"{stage.value} 应有 24 条，实际 {len(items)} 条"

    def test_items_per_theme_per_stage(self):
        """每阶段每主题 3 条。"""
        for stage in ChildStage:
            for theme in DevTheme:
                items = get_items_by_theme(theme, stage)
                assert len(items) == 3, (
                    f"{stage.value}/{theme.value} 应有 3 条，实际 {len(items)} 条"
                )

    def test_unique_ids(self):
        """所有 ID 唯一。"""
        ids = [item.item_id for item in ALL_ITEMS]
        assert len(ids) == len(set(ids))

    def test_id_format(self):
        """ID 格式：{阶段前缀}{主题字母}-{序号}。"""
        for item in ALL_ITEMS:
            assert "-" in item.item_id
            prefix, suffix = item.item_id.split("-")
            assert len(prefix) == 3  # e.g., "18A", "24B", "36F", "18G", "24H"
            assert suffix.isdigit()


class TestGetItem:
    """按 ID 查找。"""

    def test_existing_item(self):
        item = get_item("18A-01")
        assert item is not None
        assert item.stage == ChildStage.M18_24
        assert item.theme == DevTheme.JOINT_ATTENTION
        assert "叫名字" in item.description

    def test_nonexistent_item(self):
        assert get_item("99Z-99") is None


class TestGetItemsByFocus:
    """按干预焦点查找。"""

    def test_wait_respond_items(self):
        items = get_items_by_focus(InterventionFocus.WAIT_RESPOND)
        assert len(items) >= 6  # 每阶段至少 2 条

    def test_wait_respond_by_stage(self):
        items = get_items_by_focus(InterventionFocus.WAIT_RESPOND, ChildStage.M18_24)
        assert all(item.stage == ChildStage.M18_24 for item in items)


class TestActiveItems:
    """活跃观察项。"""

    def test_active_items_sorted_by_priority(self):
        items = get_active_items(ChildStage.M18_24)
        # high 在前面
        high_count = sum(1 for i in items if i.priority == "high")
        assert high_count > 0
        # 前 N 个应都是 high
        for item in items[:high_count]:
            assert item.priority == "high"

    def test_active_items_max_count(self):
        items = get_active_items(ChildStage.M24_36, max_count=10)
        assert len(items) <= 10


class TestDailyItems:
    """每日推荐。"""

    def test_daily_count(self):
        items = get_daily_items(ChildStage.M18_24, count=3)
        assert len(items) <= 3

    def test_daily_with_theme_filter(self):
        items = get_daily_items(ChildStage.M24_36, theme=DevTheme.EXPRESSION_NEED, count=4)
        # 优先当前主题的 high 级别
        if items:
            assert items[0].theme == DevTheme.EXPRESSION_NEED


class TestStagePriorityThemes:
    """阶段优先主题。"""

    def test_all_stages_have_priorities(self):
        for stage in ChildStage:
            assert stage in STAGE_PRIORITY_THEMES
            assert len(STAGE_PRIORITY_THEMES[stage]) >= 3

    def test_18_24_priorities(self):
        themes = STAGE_PRIORITY_THEMES[ChildStage.M18_24]
        assert DevTheme.JOINT_ATTENTION in themes
        assert DevTheme.EXPRESSION_NEED in themes

    def test_36_48_priorities(self):
        themes = STAGE_PRIORITY_THEMES[ChildStage.M36_48]
        assert DevTheme.PLAY_NARRATIVE in themes
        assert DevTheme.SOCIAL_APPROACH in themes


# ---------------------------------------------------------------------------
# V2.0 新增：感觉处理与依恋安全观察项测试
# ---------------------------------------------------------------------------


class TestSensoryProcessingItems:
    """V2.0 感觉处理观察项验证。"""

    def test_sensory_items_exist_per_stage(self):
        """每阶段 3 条感觉处理观察项。"""
        for stage in ChildStage:
            items = get_items_by_theme(DevTheme.SENSORY_PROCESSING, stage)
            assert len(items) == 3, f"{stage.value} 感觉处理应有 3 条"

    def test_sensory_items_total(self):
        """感觉处理共 9 条。"""
        items = get_items_by_theme(DevTheme.SENSORY_PROCESSING)
        assert len(items) == 9

    def test_sensory_focus(self):
        """所有感觉处理项的焦点为 SENSORY_MODULATE。"""
        items = get_items_by_focus(InterventionFocus.SENSORY_MODULATE)
        assert len(items) == 9
        for item in items:
            assert item.theme == DevTheme.SENSORY_PROCESSING

    def test_sensory_18g01_content(self):
        """18G-01 描述包含质地相关内容。"""
        item = get_item("18G-01")
        assert item is not None
        assert item.theme == DevTheme.SENSORY_PROCESSING
        assert "质地" in item.description

    def test_sensory_no_banned_terms(self):
        """感觉处理观察项不使用被禁止的学科术语。"""
        banned = ["感统失调", "感觉统合", "感觉寻求", "感觉回避", "前庭觉", "本体觉", "触觉防御"]
        items = get_items_by_theme(DevTheme.SENSORY_PROCESSING)
        for item in items:
            for term in banned:
                assert term not in item.description, f"{item.item_id} 含禁用术语 '{term}'"
                assert term not in item.record_metric, f"{item.item_id} record_metric 含禁用术语 '{term}'"


class TestAttachmentSecurityItems:
    """V2.0 依恋安全观察项验证。"""

    def test_attachment_items_exist_per_stage(self):
        """每阶段 3 条依恋安全观察项。"""
        for stage in ChildStage:
            items = get_items_by_theme(DevTheme.ATTACHMENT_SECURITY, stage)
            assert len(items) == 3, f"{stage.value} 依恋安全应有 3 条"

    def test_attachment_items_total(self):
        """依恋安全共 9 条。"""
        items = get_items_by_theme(DevTheme.ATTACHMENT_SECURITY)
        assert len(items) == 9

    def test_attachment_focus(self):
        """所有依恋安全项的焦点为 SECURE_BASE。"""
        items = get_items_by_focus(InterventionFocus.SECURE_BASE)
        assert len(items) == 9
        for item in items:
            assert item.theme == DevTheme.ATTACHMENT_SECURITY

    def test_attachment_18h01_content(self):
        """18H-01 描述包含探索相关内容。"""
        item = get_item("18H-01")
        assert item is not None
        assert item.theme == DevTheme.ATTACHMENT_SECURITY
        assert "探索" in item.description

    def test_attachment_no_banned_terms(self):
        """依恋安全观察项不使用被禁止的诊断标签。"""
        banned = ["依恋障碍", "不安全依恋", "回避型", "焦虑型", "反应性依恋"]
        items = get_items_by_theme(DevTheme.ATTACHMENT_SECURITY)
        for item in items:
            for term in banned:
                assert term not in item.description, f"{item.item_id} 含禁用标签 '{term}'"
                assert term not in item.record_metric, f"{item.item_id} record_metric 含禁用标签 '{term}'"


class TestV2PriorityThemes:
    """V2.0 阶段优先主题更新。"""

    def test_18_24_has_attachment(self):
        """18-24m 优先主题包含依恋安全。"""
        themes = STAGE_PRIORITY_THEMES[ChildStage.M18_24]
        assert DevTheme.ATTACHMENT_SECURITY in themes

    def test_36_48_has_sensory(self):
        """36-48m 优先主题包含感觉处理。"""
        themes = STAGE_PRIORITY_THEMES[ChildStage.M36_48]
        assert DevTheme.SENSORY_PROCESSING in themes


class TestMilestoneEnrichment:
    """V2.0 里程碑数据注入验证。"""

    def test_sensory_items_have_milestones(self):
        """感觉处理观察项有里程碑参考。"""
        items = get_items_by_theme(DevTheme.SENSORY_PROCESSING)
        for item in items:
            assert item.milestone_reference, f"{item.item_id} 缺少 milestone_reference"
            assert item.strength_cue, f"{item.item_id} 缺少 strength_cue"
            assert item.sensitive_window, f"{item.item_id} 缺少 sensitive_window"

    def test_attachment_items_have_milestones(self):
        """依恋安全观察项有里程碑参考。"""
        items = get_items_by_theme(DevTheme.ATTACHMENT_SECURITY)
        for item in items:
            assert item.milestone_reference, f"{item.item_id} 缺少 milestone_reference"
            assert item.strength_cue, f"{item.item_id} 缺少 strength_cue"
            assert item.sensitive_window, f"{item.item_id} 缺少 sensitive_window"


# ---------------------------------------------------------------------------
# V2.1 力量取向记录框架验证
# ---------------------------------------------------------------------------


class TestStrengthBasedRecordMetric:
    """V2.1 力量取向——全部 record_metric 应为正向描述，不含缺陷导向二元判断。"""

    # "是否出现"/"是否…"/"需不需…" 等缺陷导向短语
    DEFICIT_PATTERNS = [
        "是否出现",
        "是否自发出现",
        "是否需",
        "需不需",
        "是否总靠",
        "是否仍",
        "是否频繁",
        "是否每次",
        "是否一受阻",
        "是否只在",
    ]

    def test_no_deficit_binary_patterns(self):
        """全部 72 条 record_metric 不含缺陷导向二元判断短语。"""
        for item in ALL_ITEMS:
            for pattern in self.DEFICIT_PATTERNS:
                assert pattern not in item.record_metric, (
                    f"{item.item_id} record_metric 含缺陷导向短语 '{pattern}'：{item.record_metric}"
                )

    def test_record_metric_contains_condition_or_context(self):
        """全部 record_metric 至少包含一个正向引导词（什么/哪/最/条件/方式/场景/举例）。"""
        positive_cues = ["什么", "哪", "最", "条件", "方式", "场景", "举例"]
        for item in ALL_ITEMS:
            has_cue = any(cue in item.record_metric for cue in positive_cues)
            assert has_cue, (
                f"{item.item_id} record_metric 缺少正向引导词：{item.record_metric}"
            )

    def test_record_metric_not_empty(self):
        """全部 record_metric 非空。"""
        for item in ALL_ITEMS:
            assert item.record_metric.strip(), f"{item.item_id} record_metric 为空"

    def test_record_metric_min_length(self):
        """全部 record_metric 至少 10 个字符（足够具体）。"""
        for item in ALL_ITEMS:
            assert len(item.record_metric) >= 10, (
                f"{item.item_id} record_metric 过短（{len(item.record_metric)} 字符）：{item.record_metric}"
            )

    def test_24_36_items_no_deficit_patterns(self):
        """24-36m 阶段的 record_metric 不含缺陷导向短语（此阶段之前最多）。"""
        items = get_items_by_stage(ChildStage.M24_36)
        assert len(items) == 24
        for item in items:
            for pattern in self.DEFICIT_PATTERNS:
                assert pattern not in item.record_metric, (
                    f"{item.item_id} record_metric 含缺陷导向短语 '{pattern}'"
                )

    def test_36_48_items_no_deficit_patterns(self):
        """36-48m 阶段的 record_metric 不含缺陷导向短语（此阶段之前较多）。"""
        items = get_items_by_stage(ChildStage.M36_48)
        assert len(items) == 24
        for item in items:
            for pattern in self.DEFICIT_PATTERNS:
                assert pattern not in item.record_metric, (
                    f"{item.item_id} record_metric 含缺陷导向短语 '{pattern}'"
                )
