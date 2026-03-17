"""技能模块。

提供 Skill ABC 接口、SkillRegistry 自动发现加载，
以及现有 Renderer 的 SkillAdapter 桥接适配器。

Phase 3: Orchestrator 通过 SkillRegistry 动态路由。
"""

from ai_parenting.skills.base import BoundaryRule, Skill, SkillMetadata, SkillResult
from ai_parenting.skills.registry import SkillRegistry

__all__ = [
    "BoundaryRule",
    "Skill",
    "SkillMetadata",
    "SkillRegistry",
    "SkillResult",
]
