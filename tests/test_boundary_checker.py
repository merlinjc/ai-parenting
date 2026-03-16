"""边界检查测试。

覆盖：
- 各类黑名单命中 / 未命中
- 替换正确性
- 字段完整性检查
- 字符长度检查
- 清洁结果构建
"""

import pytest

from ai_parenting.engine.boundary_checker import BoundaryChecker, BoundaryCheckOutput
from ai_parenting.models.enums import DecisionValue, FocusTheme
from ai_parenting.models.schemas import (
    DayTaskContent,
    DecisionOptionContent,
    FeedbackItemContent,
    InstantHelpResult,
    ObservationCandidateContent,
    PlanGenerationResult,
    StepContent,
    WeeklyFeedbackResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_clean_result(**overrides) -> InstantHelpResult:
    """构造一个干净的、不触发任何黑名单的结果。"""
    base = {
        "step_one": StepContent(title="先稳住自己", body="深呼吸，感受当下。你的在场本身就是支持。"),
        "step_two": StepContent(title="做一个小动作", body="给孩子一个简单选择。"),
        "step_three": StepContent(title="留一个退路", body="如果没接住，等一等再试。"),
        "scenario_summary": "测试场景",
        "suggest_record": True,
        "suggest_add_focus": False,
        "suggest_consult_prep": False,
        "consult_prep_reason": None,
        "boundary_note": "以上为支持性建议。",
    }
    base.update(overrides)
    return InstantHelpResult.model_validate(
        {k: v.model_dump() if isinstance(v, StepContent) else v for k, v in base.items()}
    )


checker = BoundaryChecker()


# ---------------------------------------------------------------------------
# Clean Result Tests
# ---------------------------------------------------------------------------


class TestCleanResult:
    def test_clean_result_passes(self):
        result = _make_clean_result()
        output = checker.check(result)
        assert output.passed is True
        assert output.flags == []
        assert output.cleaned_result is None


# ---------------------------------------------------------------------------
# Diagnosis Label Tests
# ---------------------------------------------------------------------------


class TestDiagnosisLabels:
    @pytest.mark.parametrize("label", [
        "自闭", "自闭症", "多动", "多动症", "发育迟缓",
        "语言障碍", "感统失调", "注意力缺陷", "孤独症谱系", "智力障碍",
    ])
    def test_diagnosis_label_detected(self, label: str):
        result = _make_clean_result(
            step_one=StepContent(title="先稳住自己", body=f"这不像是{label}的表现。")
        )
        output = checker.check(result)
        assert output.passed is False
        assert any(f.category == "diagnosis_label" for f in output.flags)

    def test_diagnosis_label_replaced_in_cleaned(self):
        result = _make_clean_result(
            step_one=StepContent(title="先稳住自己", body="这不像是自闭的表现。")
        )
        output = checker.check(result)
        assert output.cleaned_result is not None
        assert "自闭" not in output.cleaned_result.step_one.body
        assert "专业人士" in output.cleaned_result.step_one.body


# ---------------------------------------------------------------------------
# Treatment Promise Tests
# ---------------------------------------------------------------------------


class TestTreatmentPromises:
    @pytest.mark.parametrize("word,replacement", [
        ("治愈", "帮助"),
        ("矫正", "支持"),
        ("根治", "帮助"),
        ("训练好", "给更多机会"),
        ("康复", "支持"),
        ("纠正", "帮助"),
    ])
    def test_treatment_promise_replaced(self, word: str, replacement: str):
        result = _make_clean_result(
            step_two=StepContent(title="做一个小动作", body=f"可以通过练习{word}。")
        )
        output = checker.check(result)
        assert output.passed is False
        assert output.cleaned_result is not None
        assert word not in output.cleaned_result.step_two.body
        assert replacement in output.cleaned_result.step_two.body


# ---------------------------------------------------------------------------
# Absolute Judgment Tests
# ---------------------------------------------------------------------------


class TestAbsoluteJudgments:
    @pytest.mark.parametrize("word", ["一定", "肯定", "必须", "绝对", "百分之百"])
    def test_absolute_judgment_detected(self, word: str):
        result = _make_clean_result(
            step_three=StepContent(title="留一个退路", body=f"你{word}要这样做。")
        )
        output = checker.check(result)
        assert output.passed is False
        assert any(f.category == "absolute_judgment" for f in output.flags)


# ---------------------------------------------------------------------------
# Overquantify Tests
# ---------------------------------------------------------------------------


class TestOverquantify:
    @pytest.mark.parametrize("phrase", [
        "每天必须3次",
        "每天必须 5 次",
        "必须坚持7天",
        "必须坚持 14 天",
        "达到30分钟",
        "达到 15 分钟",
    ])
    def test_overquantify_detected(self, phrase: str):
        result = _make_clean_result(
            step_two=StepContent(title="做一个小动作", body=f"建议{phrase}练习。")
        )
        output = checker.check(result)
        assert output.passed is False
        assert any(f.category == "overquantify" for f in output.flags)


# ---------------------------------------------------------------------------
# Blame Parent Tests
# ---------------------------------------------------------------------------


class TestBlameParent:
    @pytest.mark.parametrize("phrase", [
        "你应该早点注意到",
        "如果你之前就",
        "你做错了",
    ])
    def test_blame_parent_detected(self, phrase: str):
        result = _make_clean_result(
            step_one=StepContent(title="先稳住自己", body=f"{phrase}这个情况。")
        )
        output = checker.check(result)
        assert output.passed is False
        assert any(f.category == "blame_parent" for f in output.flags)


# ---------------------------------------------------------------------------
# Negate Child Tests
# ---------------------------------------------------------------------------


class TestNegateChild:
    @pytest.mark.parametrize("phrase", [
        "做不到", "学不会", "不正常", "有问题", "落后",
    ])
    def test_negate_child_detected(self, phrase: str):
        result = _make_clean_result(
            step_three=StepContent(title="留一个退路", body=f"孩子{phrase}是因为阶段。")
        )
        output = checker.check(result)
        assert output.passed is False
        assert any(f.category == "negate_child" for f in output.flags)


# ---------------------------------------------------------------------------
# Field Length Tests
# ---------------------------------------------------------------------------


class TestFieldLength:
    def test_step_one_body_over_200(self):
        """step_one.body 超过 200 应被标记。使用 model_construct 绕过 Pydantic validator。"""
        result = InstantHelpResult.model_construct(
            step_one=StepContent.model_construct(title="标题", body="a" * 201, example_script=None),
            step_two=StepContent(title="标题", body="正文"),
            step_three=StepContent(title="标题", body="正文"),
            scenario_summary="测试场景",
            suggest_record=True,
            suggest_add_focus=False,
            suggest_consult_prep=False,
            consult_prep_reason=None,
            boundary_note="边界说明",
        )
        output = checker.check(result)
        assert output.passed is False
        assert any(
            f.category == "field_length" and f.field_path == "step_one.body"
            for f in output.flags
        )

    def test_scenario_summary_over_80(self):
        # 需要用 model_construct 绕过 Pydantic 校验来测试 checker 的长度检查
        result = InstantHelpResult.model_construct(
            step_one=StepContent(title="标题", body="正文"),
            step_two=StepContent(title="标题", body="正文"),
            step_three=StepContent(title="标题", body="正文"),
            scenario_summary="a" * 81,
            suggest_record=True,
            suggest_add_focus=False,
            suggest_consult_prep=False,
            consult_prep_reason=None,
            boundary_note="边界说明",
        )
        output = checker.check(result)
        assert any(
            f.category == "field_length" and f.field_path == "scenario_summary"
            for f in output.flags
        )


# ---------------------------------------------------------------------------
# Multiple Violations Tests
# ---------------------------------------------------------------------------


class TestMultipleViolations:
    def test_multiple_categories_detected(self):
        result = _make_clean_result(
            step_one=StepContent(title="先稳住自己", body="这像自闭的表现，你一定要注意。"),
        )
        output = checker.check(result)
        assert output.passed is False
        categories = {f.category for f in output.flags}
        assert "diagnosis_label" in categories
        assert "absolute_judgment" in categories


# ---------------------------------------------------------------------------
# PlanGenerationResult Boundary Tests
# ---------------------------------------------------------------------------


def _make_clean_plan_result() -> PlanGenerationResult:
    """构造一个干净的、不触发任何黑名单的 PlanGenerationResult。"""
    def _task(day: int) -> DayTaskContent:
        return DayTaskContent(
            day_number=day,
            main_exercise_title=f"Day {day} 练习",
            main_exercise_description=f"Day {day} 的练习内容描述。",
            natural_embed_title=f"Day {day} 嵌入",
            natural_embed_description=f"Day {day} 的嵌入描述。",
            demo_script="我们一起来试试看。",
            observation_point="观察孩子是否愿意参与。",
        )

    return PlanGenerationResult(
        title="这周练习表达选择",
        primary_goal="在日常场景中练习表达",
        focus_theme=FocusTheme.LANGUAGE,
        priority_scenes=["点心时间", "选玩具"],
        day_tasks=[_task(i) for i in range(1, 8)],
        observation_candidates=[
            ObservationCandidateContent(id=f"oc_0{i}", text=f"候选项{i}", theme=FocusTheme.LANGUAGE, default_selected=i <= 2)
            for i in range(1, 6)
        ],
        weekend_review_prompt="回想这周哪个场景最容易出现互动。",
        conservative_note="如果吃力，先只保留一个场景。",
    )


class TestPlanGenerationBoundary:
    def test_clean_plan_passes(self):
        result = _make_clean_plan_result()
        output = checker.check(result)
        assert output.passed is True
        assert output.flags == []

    def test_diagnosis_label_in_day_task(self):
        result = _make_clean_plan_result()
        data = result.model_dump()
        data["day_tasks"][0]["main_exercise_description"] = "这不像自闭的表现，多做练习。"
        result2 = PlanGenerationResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "diagnosis_label" for f in output.flags)
        assert any("day_tasks[0]" in f.field_path for f in output.flags)

    def test_treatment_promise_in_primary_goal(self):
        result = _make_clean_plan_result()
        data = result.model_dump()
        data["primary_goal"] = "通过训练好来解决问题"
        result2 = PlanGenerationResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "treatment_promise" for f in output.flags)

    def test_absolute_judgment_in_demo_script(self):
        result = _make_clean_plan_result()
        data = result.model_dump()
        data["day_tasks"][2]["demo_script"] = "你一定要这样做。"
        result2 = PlanGenerationResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "absolute_judgment" for f in output.flags)

    def test_negate_child_in_observation_point(self):
        result = _make_clean_plan_result()
        data = result.model_dump()
        data["day_tasks"][3]["observation_point"] = "观察孩子做不到的表现。"
        result2 = PlanGenerationResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "negate_child" for f in output.flags)

    def test_cleaned_result_replaces_violation(self):
        result = _make_clean_plan_result()
        data = result.model_dump()
        data["day_tasks"][0]["main_exercise_description"] = "这不像是自闭的表现。"
        result2 = PlanGenerationResult.model_validate(data)
        output = checker.check(result2)
        assert output.cleaned_result is not None
        assert isinstance(output.cleaned_result, PlanGenerationResult)
        assert "自闭" not in output.cleaned_result.day_tasks[0].main_exercise_description

    def test_field_length_in_day_task(self):
        """day_task 字段超长应被标记。"""
        result = _make_clean_plan_result()
        # Use model_construct on inner task to bypass Pydantic validation
        tasks = list(result.day_tasks)
        tasks[0] = DayTaskContent.model_construct(
            day_number=1,
            main_exercise_title="练习",
            main_exercise_description="a" * 301,
            natural_embed_title="嵌入",
            natural_embed_description="嵌入描述",
            demo_script="试试。",
            observation_point="观察。",
        )
        result2 = PlanGenerationResult.model_construct(
            title=result.title,
            primary_goal=result.primary_goal,
            focus_theme=result.focus_theme,
            priority_scenes=result.priority_scenes,
            day_tasks=tasks,
            observation_candidates=result.observation_candidates,
            weekend_review_prompt=result.weekend_review_prompt,
            conservative_note=result.conservative_note,
        )
        output = checker.check(result2)
        assert output.passed is False
        assert any(
            f.category == "field_length" and "day_tasks[0].main_exercise_description" in f.field_path
            for f in output.flags
        )

    def test_priority_scene_length_checked(self):
        """priority_scenes 单项超长应被标记。"""
        result = _make_clean_plan_result()
        # Use model_construct to bypass Pydantic validator for priority_scenes
        result2 = PlanGenerationResult.model_construct(
            title=result.title,
            primary_goal=result.primary_goal,
            focus_theme=result.focus_theme,
            priority_scenes=["a" * 16, "正常场景"],
            day_tasks=result.day_tasks,
            observation_candidates=result.observation_candidates,
            weekend_review_prompt=result.weekend_review_prompt,
            conservative_note=result.conservative_note,
        )
        output = checker.check(result2)
        assert any(
            f.category == "field_length" and "priority_scenes[0]" in f.field_path
            for f in output.flags
        )


# ---------------------------------------------------------------------------
# WeeklyFeedbackResult Boundary Tests
# ---------------------------------------------------------------------------


def _make_clean_feedback_result() -> WeeklyFeedbackResult:
    """构造一个干净的、不触发任何黑名单的 WeeklyFeedbackResult。"""
    return WeeklyFeedbackResult(
        positive_changes=[
            FeedbackItemContent(
                title="转场更顺了",
                description="预告后孩子更快接受。",
                supporting_evidence="周三记录提到变化",
            ),
        ],
        opportunities=[
            FeedbackItemContent(
                title="睡前仍然比较难",
                description="睡前从客厅到卧室仍是高压场景。",
            ),
        ],
        summary_text="这一周在洗澡转场上出现了值得注意的变化。",
        decision_options=[
            DecisionOptionContent(id="opt_c", text="继续", value=DecisionValue.CONTINUE, rationale="巩固改善"),
            DecisionOptionContent(id="opt_l", text="放慢", value=DecisionValue.LOWER_DIFFICULTY, rationale="减少压力"),
            DecisionOptionContent(id="opt_f", text="换方向", value=DecisionValue.CHANGE_FOCUS, rationale="尝试新主题"),
        ],
        conservative_path_note="可以先暂停新的练习安排。",
        referenced_record_ids=["uuid-001"],
        referenced_plan_id="uuid-plan",
    )


class TestWeeklyFeedbackBoundary:
    def test_clean_feedback_passes(self):
        result = _make_clean_feedback_result()
        output = checker.check(result)
        assert output.passed is True
        assert output.flags == []

    def test_diagnosis_label_in_positive_changes(self):
        result = _make_clean_feedback_result()
        data = result.model_dump()
        data["positive_changes"][0]["description"] = "这不像自闭的表现。"
        result2 = WeeklyFeedbackResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "diagnosis_label" for f in output.flags)
        assert any("positive_changes[0]" in f.field_path for f in output.flags)

    def test_negate_child_in_opportunities(self):
        result = _make_clean_feedback_result()
        data = result.model_dump()
        data["opportunities"][0]["description"] = "孩子做不到这个能力。"
        result2 = WeeklyFeedbackResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "negate_child" for f in output.flags)

    def test_blame_parent_in_summary(self):
        result = _make_clean_feedback_result()
        data = result.model_dump()
        data["summary_text"] = "你应该早点注意到这些变化。"
        result2 = WeeklyFeedbackResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "blame_parent" for f in output.flags)

    def test_treatment_promise_in_rationale(self):
        result = _make_clean_feedback_result()
        data = result.model_dump()
        data["decision_options"][0]["rationale"] = "可以通过训练好来改善"
        result2 = WeeklyFeedbackResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        assert any(f.category == "treatment_promise" for f in output.flags)

    def test_cleaned_result_replaces_violation(self):
        result = _make_clean_feedback_result()
        data = result.model_dump()
        data["opportunities"][0]["description"] = "孩子不正常的反应。"
        result2 = WeeklyFeedbackResult.model_validate(data)
        output = checker.check(result2)
        assert output.cleaned_result is not None
        assert isinstance(output.cleaned_result, WeeklyFeedbackResult)
        assert "不正常" not in output.cleaned_result.opportunities[0].description

    def test_field_length_in_summary_text(self):
        """summary_text 超长应被标记。"""
        result = _make_clean_feedback_result()
        # Use model_construct to bypass Pydantic max_length
        result2 = WeeklyFeedbackResult.model_construct(
            positive_changes=result.positive_changes,
            opportunities=result.opportunities,
            summary_text="a" * 301,
            decision_options=result.decision_options,
            conservative_path_note=result.conservative_path_note,
            referenced_record_ids=result.referenced_record_ids,
            referenced_plan_id=result.referenced_plan_id,
        )
        output = checker.check(result2)
        assert any(
            f.category == "field_length" and f.field_path == "summary_text"
            for f in output.flags
        )

    def test_completeness_check_empty_summary(self):
        """summary_text 为空应被标记为 field_completeness 违规。"""
        result = _make_clean_feedback_result()
        result2 = WeeklyFeedbackResult.model_construct(
            positive_changes=result.positive_changes,
            opportunities=result.opportunities,
            summary_text="",
            decision_options=result.decision_options,
            conservative_path_note=result.conservative_path_note,
            referenced_record_ids=result.referenced_record_ids,
            referenced_plan_id=result.referenced_plan_id,
        )
        # BoundaryChecker.check 内部 _build_cleaned_result 可能因 model_validate 拒绝空串而失败，
        # 所以直接测试 _check_field_completeness 方法
        flags = checker._check_field_completeness(result2)
        assert any(
            f.category == "field_completeness" and f.field_path == "summary_text"
            for f in flags
        )

    def test_multiple_violations_in_feedback(self):
        """同时触发多种违规。"""
        result = _make_clean_feedback_result()
        data = result.model_dump()
        data["positive_changes"][0]["description"] = "这像自闭的表现。"
        data["opportunities"][0]["description"] = "你做错了这个方向。"
        result2 = WeeklyFeedbackResult.model_validate(data)
        output = checker.check(result2)
        assert output.passed is False
        categories = {f.category for f in output.flags}
        assert "diagnosis_label" in categories
        assert "blame_parent" in categories
