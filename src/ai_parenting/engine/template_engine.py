"""模板渲染引擎。

实现两种核心操作：
1. resolve_conditionals: 解析 {{#if var == "val"}}...{{/if}} 条件块，根据上下文值裁剪
2. replace_placeholders: 执行 {{variable_name}} 占位符的字符串替换
3. render: 组合以上两步操作（先条件裁剪，后占位符替换）

设计决策：
- 使用预编译正则而非 Jinja2，因为条件语法已在设计文档中固定
- 条件分支仅支持 == 等值比较（设计文档中未使用其他运算符）
- 渲染顺序：先裁剪条件分支，再替换变量（避免分支内变量被提前替换）
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# 预编译正则
# ---------------------------------------------------------------------------

# 匹配条件块：{{#if variable == "value"}} ... {{/if}}
# 捕获组：(1) 变量名  (2) 比较值  (3) 块内内容
_CONDITIONAL_PATTERN: re.Pattern[str] = re.compile(
    r"\{\{#if\s+(\w+)\s*==\s*\"([^\"]*)\"\s*\}\}"  # {{#if var == "val"}}
    r"(.*?)"  # 块内内容（非贪婪）
    r"\{\{/if\}\}",  # {{/if}}
    re.DOTALL,
)

# 匹配占位符：{{variable_name}}
# 排除以 # 或 / 开头的标记（条件块标记）
_PLACEHOLDER_PATTERN: re.Pattern[str] = re.compile(
    r"\{\{(?!#|/)(\w+)\}\}"
)


# ---------------------------------------------------------------------------
# 公共接口
# ---------------------------------------------------------------------------


def resolve_conditionals(template: str, context: dict[str, str]) -> str:
    """解析条件块并根据上下文值裁剪。

    对于 ``{{#if variable == "value"}}content{{/if}}`` 形式的条件块：
    - 如果 context[variable] == value，保留 content（去除条件标记）
    - 否则，移除整个条件块（包括标记和 content）

    Args:
        template: 包含条件块的模板文本。
        context: 上下文变量字典，键为变量名，值为字符串。

    Returns:
        裁剪后的模板文本。
    """

    def _replace_conditional(match: re.Match[str]) -> str:
        var_name = match.group(1)
        expected_value = match.group(2)
        block_content = match.group(3)

        actual_value = context.get(var_name, "")
        if actual_value == expected_value:
            return block_content
        return ""

    # 反复解析直到没有条件块（支持同一变量的多个条件块）
    result = template
    prev = None
    while prev != result:
        prev = result
        result = _CONDITIONAL_PATTERN.sub(_replace_conditional, result)

    # 清理连续空行（条件块移除后可能留下多个空行）
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result


def replace_placeholders(template: str, variables: dict[str, str]) -> str:
    """执行占位符替换。

    将 ``{{variable_name}}`` 替换为 variables 中对应的值。
    如果变量不存在于 variables 中，保留原始占位符不变。

    Args:
        template: 包含占位符的模板文本。
        variables: 变量字典，键为变量名，值为替换字符串。

    Returns:
        替换后的模板文本。
    """

    def _replace_placeholder(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return _PLACEHOLDER_PATTERN.sub(_replace_placeholder, template)


def render(template: str, context: dict[str, str], variables: dict[str, str]) -> str:
    """完整渲染：先条件裁剪，后占位符替换。

    Args:
        template: 原始模板文本。
        context: 用于条件分支判断的上下文（如 child_stage, child_risk_level）。
        variables: 用于占位符替换的变量（如 child_nickname, child_age_months 等）。

    Returns:
        完整渲染后的 Prompt 文本。
    """
    step1 = resolve_conditionals(template, context)
    step2 = replace_placeholders(step1, variables)
    return step2
