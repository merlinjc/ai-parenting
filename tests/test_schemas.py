"""Pydantic 模型校验测试。

覆盖：
- 字段约束（超长、必填缺失、枚举非法值）
- 序列化 / 反序列化
- 完整 JSON 示例解析
"""

import json

import pytest
from pydantic import ValidationError

from ai_parenting.models.enums import ChildStage, FocusTheme, RiskLevel
from ai_parenting.models.enums import DecisionValue
from ai_parenting.models.schemas import (
    BoundaryCheckResult,
    ContextSnapshot,
    DayTaskContent,
    DecisionOptionContent,
    FeedbackItemContent,
    InstantHelpResult,
    ObservationCandidateContent,
    OutputMetadata,
    PlanGenerationResult,
    StepContent,
    WeeklyFeedbackResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_step(title: str = "测试标题", body: str = "测试正文内容", script: str | None = None) -> dict:
    return {"title": title, "body": body, "example_script": script}


def _make_valid_result(**overrides) -> dict:
    """构造一个合法的 InstantHelpResult 字典。"""
    base = {
        "step_one": _make_step(body="先稳住自己，深呼吸。"),
        "step_two": _make_step(body="给一个小选择。"),
        "step_three": _make_step(body="留一个可以回来的路。"),
        "scenario_summary": "测试场景摘要",
        "suggest_record": True,
        "suggest_add_focus": False,
        "suggest_consult_prep": False,
        "consult_prep_reason": None,
        "boundary_note": "以上为支持性建议。如持续担心建议咨询。",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# StepContent Tests
# ---------------------------------------------------------------------------


class TestStepContent:
    def test_valid(self):
        step = StepContent(title="先稳住节奏", body="深呼吸一次。")
        assert step.title == "先稳住节奏"
        assert step.example_script is None

    def test_title_max_length(self):
        with pytest.raises(ValidationError):
            StepContent(title="a" * 21, body="正文")

    def test_title_empty(self):
        with pytest.raises(ValidationError):
            StepContent(title="", body="正文")

    def test_body_max_length_300(self):
        # StepContent 本身允许 300
        step = StepContent(title="标题", body="a" * 300)
        assert len(step.body) == 300

    def test_body_over_300(self):
        with pytest.raises(ValidationError):
            StepContent(title="标题", body="a" * 301)

    def test_example_script_max_length(self):
        with pytest.raises(ValidationError):
            StepContent(title="标题", body="正文", example_script="a" * 101)


# ---------------------------------------------------------------------------
# InstantHelpResult Tests
# ---------------------------------------------------------------------------


class TestInstantHelpResult:
    def test_valid_result(self):
        data = _make_valid_result()
        result = InstantHelpResult.model_validate(data)
        assert result.step_one.title == "测试标题"
        assert result.suggest_record is True

    def test_step_one_body_max_200(self):
        """step_one.body 限制为 200 字符。"""
        data = _make_valid_result(
            step_one=_make_step(body="a" * 201)
        )
        with pytest.raises(ValidationError, match="step_one.body"):
            InstantHelpResult.model_validate(data)

    def test_step_one_body_200_ok(self):
        """step_one.body 恰好 200 字符应通过。"""
        data = _make_valid_result(
            step_one=_make_step(body="a" * 200)
        )
        result = InstantHelpResult.model_validate(data)
        assert len(result.step_one.body) == 200

    def test_step_two_body_300_ok(self):
        """step_two.body 允许 300 字符。"""
        data = _make_valid_result(
            step_two=_make_step(body="a" * 300)
        )
        result = InstantHelpResult.model_validate(data)
        assert len(result.step_two.body) == 300

    def test_scenario_summary_max_80(self):
        data = _make_valid_result(scenario_summary="a" * 81)
        with pytest.raises(ValidationError):
            InstantHelpResult.model_validate(data)

    def test_boundary_note_max_150(self):
        data = _make_valid_result(boundary_note="a" * 151)
        with pytest.raises(ValidationError):
            InstantHelpResult.model_validate(data)

    def test_json_roundtrip(self):
        """JSON 序列化 → 反序列化往返一致性。"""
        data = _make_valid_result()
        result = InstantHelpResult.model_validate(data)
        json_str = result.model_dump_json()
        restored = InstantHelpResult.model_validate_json(json_str)
        assert restored == result

    def test_full_example_from_design_doc(self):
        """设计文档中的完整输出示例应能通过校验。"""
        example_json = json.dumps({
            "step_one": {
                "title": "先稳住节奏",
                "body": "深呼吸一次。这个阶段的孩子在吃饭时坐不住是很常见的，不需要马上让他坐好。你的平静本身就在帮助他。",
                "example_script": None,
            },
            "step_two": {
                "title": "给一个小选择",
                "body": "不催促坐下，而是给一个跟吃饭相关的小选择。选择能帮助孩子重新把注意力拉回餐桌。如果他站着吃了一口也没关系，这本身就是参与。",
                "example_script": "你要用勺子还是用叉子？",
            },
            "step_three": {
                "title": "留一个可以回来的路",
                "body": "如果他走开了，不追着喂。等一两分钟后，平静地再邀请一次。如果今天这一餐没坐下来，也不代表以后都不行。",
                "example_script": "饭还在这里，你想吃的时候可以回来。",
            },
            "scenario_summary": "吃饭时坐不住，家长在尝试让孩子回到餐桌",
            "suggest_record": True,
            "suggest_add_focus": False,
            "suggest_consult_prep": False,
            "consult_prep_reason": None,
            "boundary_note": "以上为基于当前场景的支持性建议，不构成专业评估。如果类似情况反复出现且让你持续担心，建议预约一次专业咨询。",
        }, ensure_ascii=False)
        result = InstantHelpResult.model_validate_json(example_json)
        assert result.step_one.title == "先稳住节奏"
        assert result.suggest_consult_prep is False


# ---------------------------------------------------------------------------
# ContextSnapshot Tests
# ---------------------------------------------------------------------------


class TestContextSnapshot:
    def test_valid(self):
        ctx = ContextSnapshot(
            child_age_months=26,
            child_stage=ChildStage.M24_36,
            child_focus_themes=[FocusTheme.LANGUAGE],
            child_risk_level=RiskLevel.NORMAL,
        )
        assert ctx.child_age_months == 26

    def test_age_range(self):
        with pytest.raises(ValidationError):
            ContextSnapshot(
                child_age_months=10,  # 低于 18
                child_stage=ChildStage.M18_24,
                child_risk_level=RiskLevel.NORMAL,
            )

    def test_plan_day_range(self):
        with pytest.raises(ValidationError):
            ContextSnapshot(
                child_age_months=20,
                child_stage=ChildStage.M18_24,
                child_risk_level=RiskLevel.NORMAL,
                active_plan_day=8,  # 超过 7
            )


# ---------------------------------------------------------------------------
# OutputMetadata Tests
# ---------------------------------------------------------------------------


class TestOutputMetadata:
    def test_valid(self):
        from datetime import datetime

        meta = OutputMetadata(
            prompt_template_version="tpl_instant_help_v1/1.0.0",
            model_provider="test",
            model_version="v1",
            boundary_check_passed=True,
            generation_timestamp=datetime.now(),
            latency_ms=500,
        )
        assert meta.boundary_check_flags == []
        assert meta.latency_ms == 500


# ---------------------------------------------------------------------------
# DayTaskContent Tests
# ---------------------------------------------------------------------------


def _make_day_task(**overrides) -> dict:
    """构造一个合法的 DayTaskContent 字典。"""
    base = {
        "day_number": 1,
        "main_exercise_title": "观察互动节奏",
        "main_exercise_description": "今天在一个场景里留意孩子的反应。",
        "natural_embed_title": "睡前看书",
        "natural_embed_description": "选一本简单的书，一起看。",
        "demo_script": "我们一起来试试看。",
        "observation_point": "观察孩子是否愿意参与。",
    }
    base.update(overrides)
    return base


class TestDayTaskContent:
    def test_valid(self):
        task = DayTaskContent.model_validate(_make_day_task())
        assert task.day_number == 1
        assert task.main_exercise_title == "观察互动节奏"

    def test_day_number_range(self):
        with pytest.raises(ValidationError):
            DayTaskContent.model_validate(_make_day_task(day_number=0))
        with pytest.raises(ValidationError):
            DayTaskContent.model_validate(_make_day_task(day_number=8))

    def test_main_exercise_title_max_length(self):
        with pytest.raises(ValidationError):
            DayTaskContent.model_validate(_make_day_task(main_exercise_title="a" * 26))

    def test_main_exercise_description_max_length(self):
        with pytest.raises(ValidationError):
            DayTaskContent.model_validate(_make_day_task(main_exercise_description="a" * 301))

    def test_demo_script_max_length(self):
        with pytest.raises(ValidationError):
            DayTaskContent.model_validate(_make_day_task(demo_script="a" * 151))

    def test_observation_point_max_length(self):
        with pytest.raises(ValidationError):
            DayTaskContent.model_validate(_make_day_task(observation_point="a" * 151))

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            DayTaskContent.model_validate(_make_day_task(main_exercise_title=""))


# ---------------------------------------------------------------------------
# ObservationCandidateContent Tests
# ---------------------------------------------------------------------------


class TestObservationCandidateContent:
    def test_valid(self):
        oc = ObservationCandidateContent(
            id="oc_01", text="今天有互动", theme=FocusTheme.LANGUAGE, default_selected=True
        )
        assert oc.id == "oc_01"
        assert oc.default_selected is True

    def test_text_max_length(self):
        with pytest.raises(ValidationError):
            ObservationCandidateContent(
                id="oc_01", text="a" * 31, theme=FocusTheme.LANGUAGE, default_selected=True
            )

    def test_empty_id_rejected(self):
        with pytest.raises(ValidationError):
            ObservationCandidateContent(
                id="", text="候选", theme=FocusTheme.LANGUAGE, default_selected=True
            )


# ---------------------------------------------------------------------------
# PlanGenerationResult Tests
# ---------------------------------------------------------------------------


def _make_valid_plan(**overrides) -> dict:
    """构造一个合法的 PlanGenerationResult 字典。"""
    base = {
        "title": "这周练习表达选择",
        "primary_goal": "在日常场景中练习表达",
        "focus_theme": "language",
        "priority_scenes": ["点心时间", "选玩具"],
        "day_tasks": [_make_day_task(day_number=i) for i in range(1, 8)],
        "observation_candidates": [
            {"id": f"oc_0{i}", "text": f"候选项{i}", "theme": "language", "default_selected": i <= 2}
            for i in range(1, 6)
        ],
        "weekend_review_prompt": "回想这周哪个场景最容易出现互动。",
        "conservative_note": "如果吃力，先只保留一个场景。",
    }
    base.update(overrides)
    return base


class TestPlanGenerationResult:
    def test_valid(self):
        result = PlanGenerationResult.model_validate(_make_valid_plan())
        assert result.title == "这周练习表达选择"
        assert len(result.day_tasks) == 7

    def test_title_max_length(self):
        with pytest.raises(ValidationError):
            PlanGenerationResult.model_validate(_make_valid_plan(title="a" * 31))

    def test_primary_goal_max_length(self):
        with pytest.raises(ValidationError):
            PlanGenerationResult.model_validate(_make_valid_plan(primary_goal="a" * 101))

    def test_priority_scenes_too_few(self):
        with pytest.raises(ValidationError, match="priority_scenes"):
            PlanGenerationResult.model_validate(_make_valid_plan(priority_scenes=["只有一个"]))

    def test_priority_scenes_too_many(self):
        with pytest.raises(ValidationError, match="priority_scenes"):
            PlanGenerationResult.model_validate(
                _make_valid_plan(priority_scenes=["一", "二", "三", "四"])
            )

    def test_priority_scene_too_long(self):
        with pytest.raises(ValidationError, match="priority_scenes"):
            PlanGenerationResult.model_validate(
                _make_valid_plan(priority_scenes=["a" * 16, "二"])
            )

    def test_day_tasks_not_seven(self):
        with pytest.raises(ValidationError, match="day_tasks"):
            PlanGenerationResult.model_validate(
                _make_valid_plan(day_tasks=[_make_day_task(day_number=i) for i in range(1, 5)])
            )

    def test_day_tasks_duplicate_day_number(self):
        tasks = [_make_day_task(day_number=1)] * 7
        with pytest.raises(ValidationError, match="day_number"):
            PlanGenerationResult.model_validate(_make_valid_plan(day_tasks=tasks))

    def test_observation_candidates_too_few(self):
        candidates = [
            {"id": f"oc_0{i}", "text": f"候选{i}", "theme": "language", "default_selected": True}
            for i in range(1, 4)  # 只有 3 个
        ]
        with pytest.raises(ValidationError, match="observation_candidates"):
            PlanGenerationResult.model_validate(_make_valid_plan(observation_candidates=candidates))

    def test_observation_candidates_too_many(self):
        candidates = [
            {"id": f"oc_{i:02d}", "text": f"候选{i}", "theme": "language", "default_selected": i <= 2}
            for i in range(1, 10)  # 9 个
        ]
        with pytest.raises(ValidationError, match="observation_candidates"):
            PlanGenerationResult.model_validate(_make_valid_plan(observation_candidates=candidates))

    def test_observation_candidates_insufficient_default_selected(self):
        candidates = [
            {"id": f"oc_0{i}", "text": f"候选{i}", "theme": "language", "default_selected": i == 1}
            for i in range(1, 6)  # 只有 1 个 default_selected
        ]
        with pytest.raises(ValidationError, match="default_selected"):
            PlanGenerationResult.model_validate(_make_valid_plan(observation_candidates=candidates))

    def test_observation_candidates_duplicate_ids(self):
        candidates = [
            {"id": "oc_01", "text": f"候选{i}", "theme": "language", "default_selected": i <= 2}
            for i in range(1, 6)  # 全部 id 相同
        ]
        with pytest.raises(ValidationError, match="唯一"):
            PlanGenerationResult.model_validate(_make_valid_plan(observation_candidates=candidates))

    def test_json_roundtrip(self):
        result = PlanGenerationResult.model_validate(_make_valid_plan())
        json_str = result.model_dump_json()
        restored = PlanGenerationResult.model_validate_json(json_str)
        assert restored == result

    def test_weekend_review_prompt_max_length(self):
        with pytest.raises(ValidationError):
            PlanGenerationResult.model_validate(
                _make_valid_plan(weekend_review_prompt="a" * 201)
            )

    def test_conservative_note_max_length(self):
        with pytest.raises(ValidationError):
            PlanGenerationResult.model_validate(
                _make_valid_plan(conservative_note="a" * 201)
            )


# ---------------------------------------------------------------------------
# FeedbackItemContent Tests
# ---------------------------------------------------------------------------


class TestFeedbackItemContent:
    def test_valid_with_evidence(self):
        item = FeedbackItemContent(
            title="转场更顺了",
            description="预告后孩子更快接受。",
            supporting_evidence="周三记录提到哭闹减少",
        )
        assert item.supporting_evidence is not None

    def test_valid_without_evidence(self):
        item = FeedbackItemContent(
            title="可以多记录",
            description="下周多记录几次。",
        )
        assert item.supporting_evidence is None

    def test_title_max_length(self):
        with pytest.raises(ValidationError):
            FeedbackItemContent(title="a" * 26, description="正文")

    def test_description_max_length(self):
        with pytest.raises(ValidationError):
            FeedbackItemContent(title="标题", description="a" * 201)

    def test_evidence_max_length(self):
        with pytest.raises(ValidationError):
            FeedbackItemContent(title="标题", description="正文", supporting_evidence="a" * 101)


# ---------------------------------------------------------------------------
# DecisionOptionContent Tests
# ---------------------------------------------------------------------------


class TestDecisionOptionContent:
    def test_valid(self):
        opt = DecisionOptionContent(
            id="opt_c", text="继续", value=DecisionValue.CONTINUE, rationale="巩固改善"
        )
        assert opt.value == DecisionValue.CONTINUE

    def test_text_max_length(self):
        with pytest.raises(ValidationError):
            DecisionOptionContent(
                id="opt_c", text="a" * 31, value=DecisionValue.CONTINUE, rationale="理由"
            )

    def test_rationale_max_length(self):
        with pytest.raises(ValidationError):
            DecisionOptionContent(
                id="opt_c", text="继续", value=DecisionValue.CONTINUE, rationale="a" * 101
            )

    def test_invalid_value(self):
        with pytest.raises(ValidationError):
            DecisionOptionContent(
                id="opt_c", text="继续", value="invalid_value", rationale="理由"
            )


# ---------------------------------------------------------------------------
# WeeklyFeedbackResult Tests
# ---------------------------------------------------------------------------


def _make_valid_feedback(**overrides) -> dict:
    """构造一个合法的 WeeklyFeedbackResult 字典。"""
    base = {
        "positive_changes": [
            {
                "title": "洗澡转场更顺了",
                "description": "预告后孩子更快接受。",
                "supporting_evidence": "周三记录提到哭闹减少",
            },
        ],
        "opportunities": [
            {"title": "睡前仍然比较难", "description": "睡前从客厅到卧室仍是高压场景。"},
        ],
        "summary_text": "这一周在洗澡转场上出现了值得注意的变化。",
        "decision_options": [
            {"id": "opt_c", "text": "继续", "value": "continue", "rationale": "巩固改善"},
            {"id": "opt_l", "text": "放慢", "value": "lower_difficulty", "rationale": "减少压力"},
            {"id": "opt_f", "text": "换方向", "value": "change_focus", "rationale": "尝试新主题"},
        ],
        "conservative_path_note": "可以先暂停新的练习安排。",
        "referenced_record_ids": ["uuid-001"],
        "referenced_plan_id": "uuid-plan",
    }
    base.update(overrides)
    return base


class TestWeeklyFeedbackResult:
    def test_valid(self):
        result = WeeklyFeedbackResult.model_validate(_make_valid_feedback())
        assert len(result.positive_changes) == 1
        assert len(result.decision_options) == 3

    def test_positive_changes_empty(self):
        with pytest.raises(ValidationError, match="positive_changes"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(positive_changes=[]))

    def test_positive_changes_too_many(self):
        changes = [
            {"title": f"变化{i}", "description": f"描述{i}", "supporting_evidence": f"证据{i}"}
            for i in range(4)
        ]
        with pytest.raises(ValidationError, match="positive_changes"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(positive_changes=changes))

    def test_positive_changes_missing_evidence(self):
        changes = [
            {"title": "变化", "description": "描述", "supporting_evidence": None},
        ]
        with pytest.raises(ValidationError, match="supporting_evidence"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(positive_changes=changes))

    def test_positive_changes_empty_evidence(self):
        changes = [
            {"title": "变化", "description": "描述", "supporting_evidence": "  "},
        ]
        with pytest.raises(ValidationError, match="supporting_evidence"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(positive_changes=changes))

    def test_opportunities_empty(self):
        with pytest.raises(ValidationError, match="opportunities"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(opportunities=[]))

    def test_opportunities_too_many(self):
        opps = [
            {"title": f"方向{i}", "description": f"描述{i}"}
            for i in range(4)
        ]
        with pytest.raises(ValidationError, match="opportunities"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(opportunities=opps))

    def test_decision_options_wrong_count(self):
        opts = _make_valid_feedback()["decision_options"][:2]
        with pytest.raises(ValidationError, match="decision_options"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(decision_options=opts))

    def test_decision_options_duplicate_values(self):
        opts = [
            {"id": "a", "text": "选项A", "value": "continue", "rationale": "r"},
            {"id": "b", "text": "选项B", "value": "continue", "rationale": "r"},
            {"id": "c", "text": "选项C", "value": "lower_difficulty", "rationale": "r"},
        ]
        with pytest.raises(ValidationError, match="decision_options"):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(decision_options=opts))

    def test_decision_options_missing_value(self):
        opts = [
            {"id": "a", "text": "A", "value": "continue", "rationale": "r"},
            {"id": "b", "text": "B", "value": "lower_difficulty", "rationale": "r"},
            {"id": "c", "text": "C", "value": "lower_difficulty", "rationale": "r"},
        ]
        with pytest.raises(ValidationError):
            WeeklyFeedbackResult.model_validate(_make_valid_feedback(decision_options=opts))

    def test_summary_text_max_length(self):
        with pytest.raises(ValidationError):
            WeeklyFeedbackResult.model_validate(
                _make_valid_feedback(summary_text="a" * 301)
            )

    def test_conservative_path_note_max_length(self):
        with pytest.raises(ValidationError):
            WeeklyFeedbackResult.model_validate(
                _make_valid_feedback(conservative_path_note="a" * 201)
            )

    def test_json_roundtrip(self):
        result = WeeklyFeedbackResult.model_validate(_make_valid_feedback())
        json_str = result.model_dump_json()
        restored = WeeklyFeedbackResult.model_validate_json(json_str)
        assert restored == result

    def test_referenced_plan_id_required(self):
        with pytest.raises(ValidationError):
            WeeklyFeedbackResult.model_validate(
                _make_valid_feedback(referenced_plan_id="")
            )
