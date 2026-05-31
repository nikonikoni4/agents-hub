"""
markdown_injector 单元测试

契约：
1. replace_marked_section: 标记存在时替换内容，返回 True
2. replace_marked_section: 标记不存在时追加到末尾，返回 False
3. replace_marked_section: 多次替换保持稳定（幂等性）
4. replace_marked_section: 不影响标记外的其他内容
5. replace_marked_section: 支持多个不同标记共存
"""

import pytest

from agents_hub.core.utils.markdown_injector import replace_marked_section


@pytest.fixture
def md_file(tmp_path):
    """创建测试用的临时 Markdown 文件"""
    f = tmp_path / "test.md"
    f.write_text("# Test\n\nOriginal content.\n", encoding="utf-8")
    return f


class TestReplaceMarkedSection:
    """测试 replace_marked_section 的所有契约"""

    def test_replaces_existing_section(self, md_file):
        """契约：标记存在时替换内容，返回 True"""
        # 准备：先追加一个标记块
        replace_marked_section(md_file, "RUNTIME", "old content")
        # 执行
        result = replace_marked_section(md_file, "RUNTIME", "new content")
        # 验证
        assert result is True
        text = md_file.read_text(encoding="utf-8")
        assert "new content" in text
        assert "old content" not in text

    def test_appends_when_no_markers(self, md_file):
        """契约：标记不存在时追加到末尾，返回 False"""
        result = replace_marked_section(md_file, "RUNTIME", "injected")
        assert result is False
        text = md_file.read_text(encoding="utf-8")
        assert "<RUNTIME>" in text
        assert "injected" in text
        assert "</RUNTIME>" in text

    def test_preserves_other_content(self, md_file):
        """契约：不影响标记外的其他内容"""
        original = md_file.read_text(encoding="utf-8")
        replace_marked_section(md_file, "RUNTIME", "block A")
        text = md_file.read_text(encoding="utf-8")
        assert text.startswith(original.strip())

    def test_idempotent_on_repeated_replace(self, md_file):
        """契约：多次替换保持稳定（幂等性）"""
        replace_marked_section(md_file, "RUNTIME", "content v1")
        replace_marked_section(md_file, "RUNTIME", "content v2")
        replace_marked_section(md_file, "RUNTIME", "content v3")
        text = md_file.read_text(encoding="utf-8")
        # 只出现一对标记
        assert text.count("<RUNTIME>") == 1
        assert text.count("</RUNTIME>") == 1
        assert "content v3" in text
        assert "content v1" not in text
        assert "content v2" not in text

    def test_multiple_markers_coexist(self, md_file):
        """契约：支持多个不同标记共存"""
        replace_marked_section(md_file, "IDENTITY", "agent info")
        replace_marked_section(md_file, "WORKBOARD", "task list")
        text = md_file.read_text(encoding="utf-8")
        assert "<IDENTITY>" in text
        assert "<WORKBOARD>" in text
        assert "agent info" in text
        assert "task list" in text

    def test_replaces_only_target_marker(self, md_file):
        """契约：替换指定标记，不影响其他标记"""
        replace_marked_section(md_file, "IDENTITY", "old identity")
        replace_marked_section(md_file, "WORKBOARD", "old workboard")
        # 只替换 IDENTITY
        replace_marked_section(md_file, "IDENTITY", "new identity")
        text = md_file.read_text(encoding="utf-8")
        assert "new identity" in text
        assert "old identity" not in text
        assert "old workboard" in text

    def test_multiline_content(self, md_file):
        """契约：支持多行内容替换"""
        content = "<identity>\n你的名字：Manager\n群聊ID：gc_abc123\n</identity>"
        replace_marked_section(md_file, "RUNTIME", content)
        text = md_file.read_text(encoding="utf-8")
        assert "你的名字：Manager" in text
        assert "群聊ID：gc_abc123" in text
