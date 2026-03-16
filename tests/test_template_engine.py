"""模板引擎测试。

覆盖：
- 条件分支裁剪（匹配 / 不匹配 / 多个同变量分支）
- 占位符替换（正常 / 缺失变量 / 特殊字符）
- render 组合流程
"""

from ai_parenting.engine.template_engine import (
    render,
    replace_placeholders,
    resolve_conditionals,
)


# ---------------------------------------------------------------------------
# resolve_conditionals Tests
# ---------------------------------------------------------------------------


class TestResolveConditionals:
    def test_matching_branch_kept(self):
        template = '{{#if stage == "18_24m"}}保留内容{{/if}}'
        result = resolve_conditionals(template, {"stage": "18_24m"})
        assert "保留内容" in result
        assert "{{#if" not in result

    def test_non_matching_branch_removed(self):
        template = '{{#if stage == "18_24m"}}不应出现{{/if}}'
        result = resolve_conditionals(template, {"stage": "24_36m"})
        assert "不应出现" not in result

    def test_multiple_branches_same_variable(self):
        template = (
            '{{#if stage == "18_24m"}}A{{/if}}'
            '{{#if stage == "24_36m"}}B{{/if}}'
            '{{#if stage == "36_48m"}}C{{/if}}'
        )
        result = resolve_conditionals(template, {"stage": "24_36m"})
        assert "A" not in result
        assert "B" in result
        assert "C" not in result

    def test_multiline_content(self):
        template = (
            '{{#if risk == "consult"}}\n'
            "第一行\n"
            "第二行\n"
            "{{/if}}"
        )
        result = resolve_conditionals(template, {"risk": "consult"})
        assert "第一行" in result
        assert "第二行" in result

    def test_missing_variable_removes_block(self):
        template = '{{#if unknown == "value"}}不应出现{{/if}}'
        result = resolve_conditionals(template, {})
        assert "不应出现" not in result

    def test_no_conditionals(self):
        template = "普通文本不变"
        result = resolve_conditionals(template, {"a": "b"})
        assert result == "普通文本不变"

    def test_consecutive_empty_lines_cleaned(self):
        template = (
            "前文\n\n\n"
            '{{#if x == "nope"}}remove{{/if}}'
            "\n\n\n后文"
        )
        result = resolve_conditionals(template, {"x": "yes"})
        # 不应有 3 个以上连续换行
        assert "\n\n\n" not in result


# ---------------------------------------------------------------------------
# replace_placeholders Tests
# ---------------------------------------------------------------------------


class TestReplacePlaceholders:
    def test_basic_replacement(self):
        template = "你好，{{name}}！"
        result = replace_placeholders(template, {"name": "小明"})
        assert result == "你好，小明！"

    def test_multiple_placeholders(self):
        template = "{{name}}今年{{age}}岁"
        result = replace_placeholders(template, {"name": "小明", "age": "3"})
        assert result == "小明今年3岁"

    def test_missing_variable_kept(self):
        template = "{{name}}的{{missing}}"
        result = replace_placeholders(template, {"name": "小明"})
        assert result == "小明的{{missing}}"

    def test_conditional_markers_not_touched(self):
        template = '{{#if x == "y"}}keep{{/if}}'
        result = replace_placeholders(template, {"x": "value"})
        # 条件标记不应被当作占位符处理
        assert "{{#if" in result

    def test_special_characters_in_value(self):
        template = "描述：{{desc}}"
        result = replace_placeholders(template, {"desc": "包含\"引号\"和\n换行"})
        assert '包含"引号"' in result


# ---------------------------------------------------------------------------
# render (combined) Tests
# ---------------------------------------------------------------------------


class TestRender:
    def test_full_render(self):
        template = (
            '{{#if stage == "18_24m"}}阶段A{{/if}}'
            '{{#if stage == "24_36m"}}阶段B{{/if}}'
            "\n你好{{name}}！"
        )
        result = render(
            template,
            context={"stage": "24_36m"},
            variables={"name": "小明"},
        )
        assert "阶段A" not in result
        assert "阶段B" in result
        assert "小明" in result

    def test_empty_template(self):
        result = render("", {}, {})
        assert result == ""
