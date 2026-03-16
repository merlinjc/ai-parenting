"""降级结果常量。

降级版 InstantHelpResult 的文本逐字复制自 ai_parenting_ai_output_schema_v1.md 第 3.5 节。
PlanGenerationResult 和 WeeklyFeedbackResult 的降级版根据设计文档降级策略原则设计。
当模型超时、结构不合格或边界检查多次不通过时，编排层返回这些预构建实例。
"""

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
# 即时求助降级结果
# ---------------------------------------------------------------------------

DEGRADED_INSTANT_HELP_RESULT: InstantHelpResult = InstantHelpResult(
    step_one=StepContent(
        title="先稳住自己",
        body="深呼吸，提醒自己这个阶段的孩子出现这类反应是常见的。你的在场本身就是支持。",
        example_script=None,
    ),
    step_two=StepContent(
        title="简短回应",
        body="用简单、平静的话回应孩子当前的状态，不需要马上解决问题。",
        example_script="我看到你了，我在这里。",
    ),
    step_three=StepContent(
        title="给双方空间",
        body="如果当下没有缓解，可以先退一步，等情绪过去后再回来。这不是放弃，是给双方恢复的时间。",
        example_script=None,
    ),
    scenario_summary="当前场景需要的是稳定和耐心",
    suggest_record=True,
    suggest_add_focus=False,
    suggest_consult_prep=False,
    consult_prep_reason=None,
    boundary_note="以上为通用支持建议。如果类似情况反复出现且让你持续担心，建议预约一次专业咨询。",
)

# ---------------------------------------------------------------------------
# 微计划生成降级结果
# ---------------------------------------------------------------------------


def _make_degraded_day_task(day: int, title: str, desc: str, embed_title: str, embed_desc: str) -> DayTaskContent:
    """构造降级版日任务。"""
    return DayTaskContent(
        day_number=day,
        main_exercise_title=title,
        main_exercise_description=desc,
        natural_embed_title=embed_title,
        natural_embed_description=embed_desc,
        demo_script="我们一起来试试看。",
        observation_point="观察孩子是否愿意参与，不需要做到完美。",
    )


DEGRADED_PLAN_GENERATION_RESULT: PlanGenerationResult = PlanGenerationResult(
    title="这周和孩子创造温暖互动",
    primary_goal="在日常生活中，每天找到一个自然的互动机会，不加压力地和孩子一起度过",
    focus_theme=FocusTheme.LANGUAGE,
    priority_scenes=["吃饭时间", "睡前时光"],
    day_tasks=[
        _make_degraded_day_task(
            1, "观察今天的互动节奏",
            "今天不做特别安排，只在一个日常场景里留意一下孩子的反应方式。",
            "睡前多看一会儿",
            "睡前选一本简单的书，不要求互动，只是一起看。",
        ),
        _make_degraded_day_task(
            2, "重复昨天的节奏",
            "和昨天一样，在同一个场景里保持同样的节奏和话术。",
            "出门前说一句再见",
            "出门前用一句简单的话和孩子告别。",
        ),
        _make_degraded_day_task(
            3, "换一个场景试试",
            "把昨天的互动方式迁移到另一个日常场景中。",
            "洗手时唱一首小歌",
            "洗手的时候哼一段简单旋律，看看孩子的反应。",
        ),
        _make_degraded_day_task(
            4, "留一个空位给孩子",
            "今天在互动中留一个小停顿，等一等孩子是否主动回应。",
            "吃饭时等孩子表达",
            "递食物前停一下，看孩子是否会用任何方式表达想要。",
        ),
        _make_degraded_day_task(
            5, "加一个小小的选择",
            "在一个日常场景中给孩子一个二选一的小机会。",
            "穿衣服时选一件",
            "拿两件衣服让孩子指一指或看一看想穿哪件。",
        ),
        _make_degraded_day_task(
            6, "换一个人来试",
            "如果条件允许，让另一位照护者用同样的方式和孩子互动。",
            "换个时间段再试",
            "在和平时不同的时间段重复一次之前的互动。",
        ),
        _make_degraded_day_task(
            7, "回顾这一周",
            "回想这周哪个时刻最轻松、哪个时刻最卡。不需要做总结，只是回想。",
            "给自己一份认可",
            "这一周你的关注和陪伴本身就是对孩子最好的支持。",
        ),
    ],
    observation_candidates=[
        ObservationCandidateContent(id="oc_01", text="今天有一个小互动时刻", theme=FocusTheme.LANGUAGE, default_selected=True),
        ObservationCandidateContent(id="oc_02", text="孩子有回应或表达尝试", theme=FocusTheme.LANGUAGE, default_selected=True),
        ObservationCandidateContent(id="oc_03", text="今天互动比较困难", theme=FocusTheme.LANGUAGE, default_selected=False),
        ObservationCandidateContent(id="oc_04", text="家长自己状态不太好", theme=FocusTheme.EMOTION, default_selected=False),
        ObservationCandidateContent(id="oc_05", text="换了场景效果不同", theme=FocusTheme.LANGUAGE, default_selected=False),
    ],
    weekend_review_prompt="回想这周：哪个时刻你觉得和孩子之间有一个小小的连接？不需要完美，有就好。",
    conservative_note="如果这周感觉整体节奏太紧，完全可以只保留最轻松的那一个场景。你的稳定和陪伴本身就是支持。",
)

# ---------------------------------------------------------------------------
# 周反馈降级结果
# ---------------------------------------------------------------------------

DEGRADED_WEEKLY_FEEDBACK_RESULT: WeeklyFeedbackResult = WeeklyFeedbackResult(
    positive_changes=[
        FeedbackItemContent(
            title="你一直在关注孩子",
            description="这一周你持续留意孩子的变化，这份关注本身就是在给孩子创造更好的互动环境。",
            supporting_evidence="本周有使用记录工具或完成了部分计划任务",
        ),
    ],
    opportunities=[
        FeedbackItemContent(
            title="可以尝试多记录一些",
            description="下周试着在日常互动中多记录几次观察，哪怕只是一句话的记录，也能帮助看到更多变化。",
            supporting_evidence=None,
        ),
    ],
    summary_text="这一周的记录还比较少，目前能看到的信息有限。不过你的关注和陪伴本身就是最重要的支持，下周继续。",
    decision_options=[
        DecisionOptionContent(
            id="opt_continue",
            text="继续当前方向",
            value=DecisionValue.CONTINUE,
            rationale="保持当前的关注方向，看看下一周会有什么变化",
        ),
        DecisionOptionContent(
            id="opt_lower",
            text="放慢一些节奏",
            value=DecisionValue.LOWER_DIFFICULTY,
            rationale="如果感到吃力，可以只保留一个最轻松的互动场景",
        ),
        DecisionOptionContent(
            id="opt_change",
            text="换一个关注方向",
            value=DecisionValue.CHANGE_FOCUS,
            rationale="如果觉得当前方向不太合适，可以换一个新的关注点",
        ),
    ],
    conservative_path_note="如果最近整体感到疲惫，可以先暂停计划安排，只保留日常中最自然的互动方式。稳定的亲子关系比完成任务更重要。",
    referenced_record_ids=[],
    referenced_plan_id="degraded",
)
