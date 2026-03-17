"""Skill 抽象基类定义。

Phase 3 升级：
- 保留原有 3 个核心方法（metadata/execute/get_boundary_rules）
- 新增 5 个 Orchestrator 集成方法（render_prompt/parse_result/check_boundary/
  get_degraded_result/get_template_version），全部有默认实现
- 新增 session_type 属性，用于 Orchestrator 按 SessionType 路由
- SkillAdapter 桥接层实现这些方法以对接现有 Renderer
- 原生 Skill 可选择只实现 execute()（简单模式）或全部方法（Orchestrator 模式）

两种使用模式：
1. 简单模式（VoicePipeline 等）：只调用 execute()
2. Orchestrator 模式（AI 会话等）：通过 render_prompt → 调用模型 → parse_result → check_boundary
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


@dataclass
class SkillMetadata:
    """技能元信息。"""

    name: str  # 技能唯一标识，如 "instant_help"
    display_name: str  # 用户可见名称，如 "即时求助"
    description: str  # 一句话描述
    version: str  # 语义化版本号
    icon: str = ""  # Emoji 图标
    input_schema: type[BaseModel] | None = None  # 输入参数 Schema
    output_schema: type[BaseModel] | None = None  # 输出结果 Schema
    tags: list[str] = field(default_factory=list)  # 分类标签
    is_enabled: bool = True  # 是否启用
    # Phase 3: Orchestrator 路由所需
    session_type: str | None = None  # 对应 SessionType.value，如 "instant_help"


@dataclass
class SkillResult:
    """技能执行结果。"""

    response_text: str  # 人类可读的回复文本
    structured_data: BaseModel | None = None  # 结构化结果数据
    boundary_passed: bool = True  # 是否通过安全边界检查
    metadata: dict[str, Any] = field(default_factory=dict)  # 附加元数据
    is_degraded: bool = False  # 是否为降级结果


@dataclass
class BoundaryRule:
    """安全边界规则描述。

    用于 SkillRegistry 汇总所有技能的边界规则，
    供 BoundaryChecker 统一执行检查。
    """

    category: str  # 规则类别，如 "diagnosis_label", "treatment_promise"
    description: str  # 规则描述
    severity: str = "error"  # 严重级别: error / warning / info


class Skill(ABC):
    """技能抽象基类。

    所有技能（包括现有 Renderer 的适配器和未来新增技能）
    均需继承此类并实现以下 3 个核心抽象方法。

    Phase 3 升级 — 两种使用模式：

    1. **简单模式**（VoicePipeline 等调用者）：
       只实现 metadata / execute / get_boundary_rules

    2. **Orchestrator 模式**（AI 会话调用者）：
       额外实现 render_prompt / parse_result / check_boundary /
       get_degraded_result / get_template_version

    SkillAdapter 桥接模式演进：
    Phase 1 — 将现有 3 个 Renderer 包装为 Skill 接口适配器
    Phase 2 — VoicePipeline 通过 SkillRegistry 路由到 Skill
    Phase 3 — Orchestrator 通过 SkillRegistry 动态路由（本次）
    Phase 4 — 逐个替换适配器为原生 Skill 实现
    """

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """返回技能元信息。"""
        ...

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: Any) -> SkillResult:
        """执行技能。

        Args:
            params: 技能参数字典，key 取决于具体技能。
            context: ContextSnapshot 或等效的上下文对象。

        Returns:
            技能执行结果，包含回复文本和结构化数据。

        Notes:
            - 实现中应处理异常并返回降级结果（is_degraded=True）
            - 安全边界检查应在 execute 内部完成
        """
        ...

    @abstractmethod
    def get_boundary_rules(self) -> list[BoundaryRule]:
        """返回此技能关注的安全边界规则列表。

        供 SkillRegistry 汇总后交给 BoundaryChecker 执行。
        """
        ...

    # ------------------------------------------------------------------
    # Phase 3: Orchestrator 集成方法（可选实现，有默认值）
    # ------------------------------------------------------------------

    @property
    def supports_orchestrate(self) -> bool:
        """是否支持 Orchestrator 模式（render → call → parse → check）。

        默认 False。SkillAdapter 和原生 Orchestrator 技能应返回 True。
        """
        return False

    def render_prompt(self, context: Any, **kwargs: Any) -> str:
        """渲染 Prompt 文本。

        Orchestrator 模式下调用，用于生成发送给 AI 模型的 Prompt。
        不支持 Orchestrator 模式的技能可不实现此方法。

        Args:
            context: ContextSnapshot 实例。
            **kwargs: 技能专属参数。

        Returns:
            完整的 Prompt 文本。
        """
        raise NotImplementedError(
            f"Skill '{self.metadata.name}' does not support render_prompt. "
            "Set supports_orchestrate=True and implement this method."
        )

    def parse_result(self, raw_json: str) -> BaseModel:
        """解析模型返回的 JSON 为结构化结果。

        Args:
            raw_json: 模型返回的 JSON 字符串。

        Returns:
            Pydantic 模型实例。
        """
        raise NotImplementedError(
            f"Skill '{self.metadata.name}' does not support parse_result."
        )

    def check_boundary(self, result: BaseModel) -> Any:
        """对结果执行安全边界检查。

        Args:
            result: 待检查的结构化结果。

        Returns:
            BoundaryCheckOutput 实例。
        """
        raise NotImplementedError(
            f"Skill '{self.metadata.name}' does not support check_boundary."
        )

    def get_degraded_result(self) -> BaseModel:
        """获取降级结果。

        当 AI 调用超时/失败时使用。

        Returns:
            预构建的降级结果实例。
        """
        raise NotImplementedError(
            f"Skill '{self.metadata.name}' does not support get_degraded_result."
        )

    def get_template_version(self) -> str:
        """获取当前 Prompt 模板版本号。

        Returns:
            版本字符串，如 "tpl_instant_help_v1/1.0.0"。
        """
        return f"skill_{self.metadata.name}_v{self.metadata.version}"

    def get_timeout_config(self) -> tuple[float, float]:
        """获取超时配置（首次超时, 最终超时）。

        Returns:
            (initial_timeout_seconds, final_timeout_seconds)
        """
        return (10.0, 15.0)
