# Milestone 1 剩余任务实现计划

## 当前状态

| 任务 | 状态 |
|---|---|
| 即时求助 Prompt 模板代码 | ✅ 已完成（107 tests pass） |
| 计划生成 Prompt 模板代码 | ⬜ 待实现 |
| 周反馈 Prompt 模板代码 | ⬜ 待实现 |
| 统一编排调度器 | ⬜ 待实现 |
| 模型供应商适配层 | ⬜ 待实现 |

---

## 实现计划（5 个阶段，按依赖顺序）

### 阶段 1：Pydantic 数据模型扩展

**修改文件**：`src/ai_parenting/models/schemas.py`、`src/ai_parenting/models/__init__.py`

新增以下模型（遵循与 InstantHelpResult 相同的 Field(max_length=...) + field_validator 模式）：

**PlanGenerationResult 相关**：
- `DayTaskContent`：day_number(1-7), main_exercise_title(25), main_exercise_description(300), natural_embed_title(25), natural_embed_description(300), demo_script(150), observation_point(150)
- `ObservationCandidateContent`：id(str), text(30), theme(FocusTheme), default_selected(bool)
- `PlanGenerationResult`：title(30), primary_goal(100), focus_theme(FocusTheme), priority_scenes(list, 2-3 个每个 15), day_tasks(list[DayTaskContent] 恰好 7), observation_candidates(list, 5-8 个), weekend_review_prompt(200), conservative_note(200)
  - @field_validator 确保 day_tasks 恰好 7 个且 day_number 为 1-7
  - @field_validator 确保 observation_candidates 5-8 个且至少 2 个 default_selected
  - @field_validator 确保 priority_scenes 2-3 个

**WeeklyFeedbackResult 相关**：
- `FeedbackItemContent`：title(25), description(200), supporting_evidence(100, 可选——opportunities 中不含)
- `DecisionOptionContent`：id(str), text(30), value(DecisionValue), rationale(100)
- `WeeklyFeedbackResult`：positive_changes(1-3 个 FeedbackItemContent，supporting_evidence 必填), opportunities(1-3 个 FeedbackItemContent，supporting_evidence 可选), summary_text(300), decision_options(恰好 3 个 DecisionOptionContent), conservative_path_note(200), referenced_record_ids(list[str]), referenced_plan_id(str)
  - @field_validator 确保 positive_changes 1-3 个且 supporting_evidence 非空
  - @field_validator 确保 decision_options 恰好 3 个且 value 各不同

**测试**：扩展 `tests/test_schemas.py` 覆盖全部新模型的约束校验。

---

### 阶段 2：BoundaryChecker 泛化

**修改文件**：`src/ai_parenting/engine/boundary_checker.py`

当前问题：`_extract_text_fields()` 硬编码了 InstantHelpResult 的 step_one/two/three 路径，`BoundaryCheckOutput.cleaned_result` 类型为 `InstantHelpResult | None`。

改造方案：
1. `BoundaryCheckOutput.cleaned_result` 类型改为 `BaseModel | None`
2. 新增 `_extract_text_fields_from_model(result: BaseModel) -> dict[str, str]` 通用方法，递归提取所有 str 字段
3. 新增 `_get_field_length_limits(result_type)` 方法，根据 Result 类型返回对应的字段长度限制字典
4. `check()` 方法签名改为 `check(result: BaseModel) -> BoundaryCheckOutput`，内部根据类型分派
5. 为 PlanGenerationResult 和 WeeklyFeedbackResult 各定义 `_FIELD_LENGTH_LIMITS` 字典

**测试**：扩展 `tests/test_boundary_checker.py`，新增针对 PlanGenerationResult 和 WeeklyFeedbackResult 的检查测试。

---

### 阶段 3：计划生成 Prompt 模板代码

**新建文件**：
- `src/ai_parenting/templates/plan_generation.py` — 模板常量
- `src/ai_parenting/templates/degraded.py` — 新增 DEGRADED_PLAN_GENERATION_RESULT（追加）
- `src/ai_parenting/renderer_plan_generation.py` — 计划生成渲染器
- `tests/test_plan_generation_renderer.py` — 渲染器测试

**模板常量**（plan_generation.py）：
逐字复制 prompt_templates_v1.md 第 6.2 节的完整模板文本，拆分为 10 段独立常量：
- TEMPLATE_ID = "tpl_plan_generation_v1"
- TEMPLATE_VERSION = "1.0.0"
- SYSTEM_ROLE（系统角色段）
- BOUNDARY_PLACEHOLDER（同即时求助）
- OUTPUT_FORMAT（JSON schema + 字段规则）
- WEEKLY_RHYTHM（统一七日节奏段）
- CHILD_CONTEXT（上下文注入段——比即时求助少 user_scenario/user_input_text，多无额外专属占位符）
- STAGE_ADAPTATION（3 段条件分支，内容针对计划生成——时长/回合/成功信号等）
- RISK_ADAPTATION（3 段条件分支，内容针对计划强度——语气/conservative_note）
- PARENT_LANGUAGE_STYLE（家长语言风格指令段）
- GENERATION_INSTRUCTION（生成指令段）
- FULL_TEMPLATE = "\n\n".join(全部段)

**降级结果**（追加到 degraded.py）：
预构建 `DEGRADED_PLAN_GENERATION_RESULT`，内容为安全通用的 7 天计划（每天用最基础的"与孩子创造一个小互动机会"类安全内容）。

**渲染器**（renderer_plan_generation.py）：
- `render_plan_generation_prompt(context, child_nickname, recent_records_summary) -> str`
- `parse_plan_generation_result(raw_json) -> PlanGenerationResult`
- `check_plan_boundary(result) -> BoundaryCheckOutput`
- `get_degraded_plan_result() -> PlanGenerationResult`
- `get_plan_template_version() -> str`

**测试**：
- 基本渲染 + 指令块注入
- 9 种 stage × risk 组合验证（参数化）
- 降级结果有效性 + 边界检查通过
- JSON 解析测试（合法/非法/缺字段）

---

### 阶段 4：周反馈 Prompt 模板代码

**新建文件**：
- `src/ai_parenting/templates/weekly_feedback.py` — 模板常量
- `src/ai_parenting/templates/degraded.py` — 新增 DEGRADED_WEEKLY_FEEDBACK_RESULT
- `src/ai_parenting/renderer_weekly_feedback.py` — 周反馈渲染器
- `tests/test_weekly_feedback_renderer.py` — 渲染器测试

**特殊处理**：周反馈模板中有 `{{#if record_count_this_week < 2}}` 条件分支，使用了 `<` 而非 `==`。处理方案：在渲染器层将 `record_count_this_week < 2` 预计算为布尔值 `record_insufficient`，用 `{{#if record_insufficient == "true"}}` 替换原模板中的条件，保持引擎不变。

**模板常量**（weekly_feedback.py）：
逐字复制第 7.2 节模板文本，拆分为段：
- TEMPLATE_ID = "tpl_weekly_feedback_v1"
- TEMPLATE_VERSION = "1.0.0"
- SYSTEM_ROLE、OUTPUT_FORMAT、WEEKLY_CONTEXT、DAY_TASKS_SUMMARY、WEEKLY_RECORDS_DETAIL、STAGE_ADAPTATION、RISK_ADAPTATION、RECORD_INSUFFICIENT_HANDLING、GENERATION_INSTRUCTION
- FULL_TEMPLATE

**降级结果**：预构建 `DEGRADED_WEEKLY_FEEDBACK_RESULT`，包含通用积极变化 1 条、通用机会 1 条、三个标准决策选项和保守路径。

**渲染器**（renderer_weekly_feedback.py）：
- `render_weekly_feedback_prompt(context, child_nickname, active_plan_title, active_plan_focus_theme, plan_completion_rate, record_count_this_week, day_tasks_summary, weekly_records_detail, active_plan_id) -> str`
- `parse_weekly_feedback_result(raw_json) -> WeeklyFeedbackResult`
- `check_feedback_boundary(result) -> BoundaryCheckOutput`
- `get_degraded_feedback_result() -> WeeklyFeedbackResult`
- `get_feedback_template_version() -> str`

---

### 阶段 5：统一编排调度器 + 模型供应商适配层

**新建文件**：
- `src/ai_parenting/providers/__init__.py`
- `src/ai_parenting/providers/base.py` — 抽象 ModelProvider 接口
- `src/ai_parenting/providers/mock_provider.py` — Mock 实现
- `src/ai_parenting/orchestrator.py` — 统一编排调度器
- `tests/test_orchestrator.py` — 调度器测试
- `tests/test_providers.py` — Provider 测试

**ModelProvider 抽象接口**（base.py）：
```python
class ModelProvider(ABC):
    async def generate(self, prompt: str, timeout_seconds: float) -> str: ...
    def provider_name(self) -> str: ...
    def model_version(self) -> str: ...
```

**MockProvider**（mock_provider.py）：
返回预构建的合法 JSON 响应，支持配置超时、返回非法 JSON、返回边界违规内容等测试场景。

**Orchestrator**（orchestrator.py）：
```python
class Orchestrator:
    def __init__(self, provider: ModelProvider): ...
    async def orchestrate(self, session_type: SessionType, context: ContextSnapshot, **kwargs) -> OrchestrateResult: ...
```

OrchestrateResult 包含：result(BaseModel), metadata(OutputMetadata), status(SessionStatus)

orchestrate 流程：
1. 根据 session_type 选择渲染器，渲染 Prompt
2. 调用 ModelProvider.generate()，含超时控制
3. 解析 JSON → 对应 Result 模型
4. 字段约束校验（Pydantic 自动完成）
5. 边界检查（BoundaryChecker.check()）
6. 异常处理：超时 → 降级；解析失败 → 重试1次 → 降级；边界不通过 → 替换后返回
7. 构建 OutputMetadata，返回 OrchestrateResult

**超时配置**：
- instant_help: 8s (最终 12s)
- plan_generation: 30s (最终 45s)
- weekly_feedback: 20s (最终 35s)

**测试**：
- 正常流程（三种 session_type）
- 超时降级
- 结构不合格降级（解析失败 → 重试 → 降级）
- 边界违规 → 替换后返回
- 重试逻辑验证

---

## 文件变更总览

| 操作 | 文件路径 |
|---|---|
| 修改 | src/ai_parenting/models/schemas.py |
| 修改 | src/ai_parenting/models/__init__.py |
| 修改 | src/ai_parenting/engine/boundary_checker.py |
| 修改 | src/ai_parenting/templates/degraded.py |
| 新建 | src/ai_parenting/templates/plan_generation.py |
| 新建 | src/ai_parenting/templates/weekly_feedback.py |
| 新建 | src/ai_parenting/renderer_plan_generation.py |
| 新建 | src/ai_parenting/renderer_weekly_feedback.py |
| 新建 | src/ai_parenting/providers/__init__.py |
| 新建 | src/ai_parenting/providers/base.py |
| 新建 | src/ai_parenting/providers/mock_provider.py |
| 新建 | src/ai_parenting/orchestrator.py |
| 修改 | tests/test_schemas.py |
| 修改 | tests/test_boundary_checker.py |
| 新建 | tests/test_plan_generation_renderer.py |
| 新建 | tests/test_weekly_feedback_renderer.py |
| 新建 | tests/test_orchestrator.py |
| 新建 | tests/test_providers.py |
