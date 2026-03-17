"""技能注册表。

支持两种注册模式：
1. 手动注册：通过 register() 方法注册 Skill 实例
2. 自动发现：扫描指定目录下的 Python 模块，自动注册实现了 Skill 接口的类

设计要点：
- 单例模式，全局唯一
- 线程安全（asyncio 单线程模型下已满足）
- 支持热注册（运行时添加新技能）
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any

from ai_parenting.skills.base import Skill, SkillMetadata

logger = logging.getLogger(__name__)


class SkillRegistry:
    """技能注册表。

    使用示例:
        registry = SkillRegistry()
        registry.register(InstantHelpAdapter())
        registry.register(PlanGenerationAdapter())

        skill = registry.get("instant_help")
        result = await skill.execute(params, context)
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    @property
    def skill_names(self) -> list[str]:
        """返回所有已注册技能的名称列表。"""
        return list(self._skills.keys())

    @property
    def skill_count(self) -> int:
        """返回已注册技能数量。"""
        return len(self._skills)

    def register(self, skill: Skill) -> None:
        """手动注册一个技能实例。

        如果同名技能已存在，覆盖并记录警告。
        """
        name = skill.metadata.name
        if name in self._skills:
            logger.warning(
                "Overwriting existing skill '%s' (version %s → %s)",
                name,
                self._skills[name].metadata.version,
                skill.metadata.version,
            )
        self._skills[name] = skill
        logger.info(
            "Registered skill: %s v%s (%s)",
            name, skill.metadata.version, skill.metadata.display_name,
        )

    def unregister(self, name: str) -> bool:
        """注销一个技能。返回是否成功。"""
        if name in self._skills:
            del self._skills[name]
            logger.info("Unregistered skill: %s", name)
            return True
        return False

    def get(self, name: str) -> Skill | None:
        """按名称获取技能实例。"""
        return self._skills.get(name)

    def get_all(self) -> list[Skill]:
        """获取所有已注册的技能实例。"""
        return list(self._skills.values())

    def get_all_metadata(self) -> list[SkillMetadata]:
        """获取所有已注册技能的元信息。"""
        return [s.metadata for s in self._skills.values()]

    def get_enabled_skills(self) -> list[Skill]:
        """获取所有已启用的技能。"""
        return [s for s in self._skills.values() if s.metadata.is_enabled]

    def discover_and_register(self, package_path: str | Path) -> int:
        """自动扫描指定包路径，发现并注册 Skill 子类。

        Args:
            package_path: Python 包的文件系统路径。

        Returns:
            新注册的技能数量。
        """
        registered = 0
        path = Path(package_path)

        if not path.is_dir():
            logger.warning("Skill discovery path not found: %s", path)
            return 0

        for module_info in pkgutil.iter_modules([str(path)]):
            if module_info.name.startswith("_"):
                continue

            try:
                # 构造模块的导入路径
                module_name = f"ai_parenting.skills.adapters.{module_info.name}"
                module = importlib.import_module(module_name)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        inspect.isclass(attr)
                        and issubclass(attr, Skill)
                        and attr is not Skill
                        and not inspect.isabstract(attr)
                    ):
                        try:
                            instance = attr()
                            self.register(instance)
                            registered += 1
                        except Exception as exc:
                            logger.error(
                                "Failed to instantiate skill class %s.%s: %s",
                                module_name, attr_name, exc,
                            )
            except Exception as exc:
                logger.error(
                    "Failed to import skill module %s: %s",
                    module_info.name, exc,
                )

        logger.info("Skill discovery completed: %d new skills registered", registered)
        return registered

    def match_by_intent(self, intent: str) -> Skill | None:
        """根据意图名匹配技能。

        VoicePipeline 的 IntentClassifier 输出意图名后，
        通过此方法路由到对应的 Skill。

        匹配规则：
        1. 精确匹配技能名称
        2. 匹配技能 tags 中的值
        """
        # 精确匹配
        skill = self._skills.get(intent)
        if skill and skill.metadata.is_enabled:
            return skill

        # 标签匹配
        for skill in self._skills.values():
            if skill.metadata.is_enabled and intent in skill.metadata.tags:
                return skill

        return None
