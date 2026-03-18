"""测试：内容质量护栏。"""

from ai_parenting.content.quality_guardrail import (
    QualityCheckResult,
    QualityFlag,
    check_plan_content_quality,
)
from ai_parenting.models.enums import ChildStage


def _make_day_tasks(count: int = 7, script_len: int = 40) -> list[dict]:
    """生成测试用日任务列表。"""
    return [
        {
            "day_number": i + 1,
            "demo_script": "x" * script_len,
        }
        for i in range(count)
    ]


def _make_observation_candidates(
    theme: str, count: int = 5, cross_theme_count: int = 0,
) -> list[dict]:
    """生成测试用观察候选项。"""
    candidates = []
    for i in range(count - cross_theme_count):
        candidates.append({"id": f"oc_{i:02d}", "theme": theme})
    for i in range(cross_theme_count):
        candidates.append({"id": f"oc_x{i:02d}", "theme": "other_theme"})
    return candidates


class TestQualityCheckResult:
    """QualityCheckResult 基础行为。"""

    def test_default_passed(self):
        result = QualityCheckResult()
        assert result.passed is True
        assert result.flags == []

    def test_add_warning_keeps_passed(self):
        result = QualityCheckResult()
        result.add_warning("test", "warning message")
        assert result.passed is True
        assert len(result.flags) == 1
        assert result.flags[0].severity == "warning"

    def test_add_error_sets_not_passed(self):
        result = QualityCheckResult()
        result.add_error("test", "error message")
        assert result.passed is False
        assert len(result.flags) == 1
        assert result.flags[0].severity == "error"

    def test_mixed_flags(self):
        result = QualityCheckResult()
        result.add_warning("w1", "warn")
        result.add_error("e1", "err")
        result.add_warning("w2", "warn2")
        assert result.passed is False
        assert len(result.flags) == 3


class TestDayTaskCount:
    """日任务数量校验。"""

    def test_seven_tasks_passes(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="language",
            primary_goal="在日常场景中增加选择表达机会",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=["点心时间", "选玩具"],
        )
        assert result.passed is True

    def test_wrong_task_count_errors(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="language",
            primary_goal="在日常场景中增加选择表达机会",
            day_tasks=_make_day_tasks(5),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=["点心时间", "选玩具"],
        )
        assert result.passed is False
        assert any(f.category == "day_task_count" for f in result.flags)


class TestScriptLength:
    """话术长度与阶段适配。"""

    def test_18_24m_short_script_passes(self):
        result = check_plan_content_quality(
            stage=ChildStage.M18_24,
            focus_theme_value="language",
            primary_goal="增加互动启动机会",
            day_tasks=_make_day_tasks(7, script_len=45),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=["吃饭", "洗澡"],
        )
        # 45 < 50, 应通过
        assert not any(f.category == "script_too_long" for f in result.flags)

    def test_18_24m_long_script_warns(self):
        result = check_plan_content_quality(
            stage=ChildStage.M18_24,
            focus_theme_value="language",
            primary_goal="增加互动启动机会",
            day_tasks=_make_day_tasks(7, script_len=60),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=["吃饭", "洗澡"],
        )
        # 60 > 50, 应告警
        script_warnings = [f for f in result.flags if f.category == "script_too_long"]
        assert len(script_warnings) == 7  # 全部 7 天都超了

    def test_36_48m_longer_script_passes(self):
        result = check_plan_content_quality(
            stage=ChildStage.M36_48,
            focus_theme_value="social",
            primary_goal="增加社交预演机会",
            day_tasks=_make_day_tasks(7, script_len=100),
            observation_candidates=_make_observation_candidates("social"),
            priority_scenes=["公园", "家中"],
        )
        # 100 < 120, 应通过
        assert not any(f.category == "script_too_long" for f in result.flags)


class TestObservationThemeConsistency:
    """观察候选项主题一致性。"""

    def test_consistent_themes_passes(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="emotion",
            primary_goal="在过渡场景中增加情绪命名",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("emotion", 5, 0),
            priority_scenes=["洗澡前", "睡前"],
        )
        assert not any(f.category == "observation_theme_mismatch" for f in result.flags)

    def test_majority_cross_theme_warns(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="emotion",
            primary_goal="在过渡场景中增加情绪命名",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("emotion", 5, 4),
            priority_scenes=["洗澡前", "睡前"],
        )
        # 4/5 = 80% 跨主题，超过 60% 阈值
        assert any(f.category == "observation_theme_mismatch" for f in result.flags)

    def test_minority_cross_theme_passes(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="emotion",
            primary_goal="在过渡场景中增加情绪命名",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("emotion", 6, 2),
            priority_scenes=["洗澡前", "睡前"],
        )
        # 2/6 ≈ 33% < 60%, 不告警
        assert not any(f.category == "observation_theme_mismatch" for f in result.flags)


class TestDiagnosticGoalDetection:
    """诊断性词汇检测。"""

    def test_clean_goal_passes(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="language",
            primary_goal="在日常场景中增加选择表达机会",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=["点心时间", "选玩具"],
        )
        assert not any(f.category == "diagnostic_goal" for f in result.flags)

    def test_diagnostic_term_errors(self):
        diagnostic_goals = [
            "治愈孩子的语言障碍",
            "矫正孩子的社交问题",
            "康复训练计划",
            "改善发育迟缓",
            "感统失调的训练好方案",
        ]
        for goal in diagnostic_goals:
            result = check_plan_content_quality(
                stage=ChildStage.M24_36,
                focus_theme_value="language",
                primary_goal=goal,
                day_tasks=_make_day_tasks(7),
                observation_candidates=_make_observation_candidates("language"),
                priority_scenes=["点心时间", "选玩具"],
            )
            assert result.passed is False, f"Goal '{goal}' should fail"
            assert any(f.category == "diagnostic_goal" for f in result.flags), (
                f"Goal '{goal}' should have diagnostic_goal flag"
            )


class TestSceneCount:
    """场景数量校验。"""

    def test_two_scenes_passes(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="language",
            primary_goal="在日常场景中增加选择表达机会",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=["点心时间", "选玩具"],
        )
        assert not any(f.category == "too_few_scenes" for f in result.flags)

    def test_single_scene_warns(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="language",
            primary_goal="在日常场景中增加选择表达机会",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=["点心时间"],
        )
        assert any(f.category == "too_few_scenes" for f in result.flags)

    def test_empty_scenes_warns(self):
        result = check_plan_content_quality(
            stage=ChildStage.M24_36,
            focus_theme_value="language",
            primary_goal="在日常场景中增加选择表达机会",
            day_tasks=_make_day_tasks(7),
            observation_candidates=_make_observation_candidates("language"),
            priority_scenes=[],
        )
        assert any(f.category == "too_few_scenes" for f in result.flags)


class TestStageAdaptation:
    """阶段适配完整性。"""

    def test_all_stages_have_params(self):
        """所有三个阶段都应有质量参数。"""
        for stage in ChildStage:
            result = check_plan_content_quality(
                stage=stage,
                focus_theme_value="language",
                primary_goal="在日常场景中增加互动机会",
                day_tasks=_make_day_tasks(7, script_len=30),
                observation_candidates=_make_observation_candidates("language"),
                priority_scenes=["场景A", "场景B"],
            )
            # 不应该有 stage_unknown 警告
            assert not any(f.category == "stage_unknown" for f in result.flags)

    def test_script_limits_increase_with_age(self):
        """话术长度上限应随年龄阶段递增。"""
        from ai_parenting.content.quality_guardrail import _STAGE_QUALITY_PARAMS

        params = _STAGE_QUALITY_PARAMS
        assert params[ChildStage.M18_24]["max_script_chars"] < params[ChildStage.M24_36]["max_script_chars"]
        assert params[ChildStage.M24_36]["max_script_chars"] < params[ChildStage.M36_48]["max_script_chars"]
