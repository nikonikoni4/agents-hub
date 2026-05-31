"""
文件标记内容替换工具

在 Markdown/XML 文件中按标记定位并替换指定区域的内容。
用于运行时动态注入 Agent 状态到 CLAUDE.md / AGENTS.md 等文件。
"""

import re
from pathlib import Path


def _build_pattern(marker: str) -> re.Pattern[str]:
    """构建标记匹配正则。

    Args:
        marker: 标记名称（如 "AGENT_RUNTIME"）
    """
    escaped_start = re.escape(f"<{marker}_START/>")
    escaped_end = re.escape(f"<{marker}_END/>")
    return re.compile(
        f"{escaped_start}\\n(.*?)\\n{escaped_end}",
        re.DOTALL,
    )


def replace_marked_section(
    file_path: Path,
    marker: str,
    content: str,
) -> bool:
    """替换文件中被标记包裹的内容块。

    在文件中查找 <{marker}_START/> 和 <{marker}_END/> 标记，
    替换两者之间的内容。如果标记不存在，追加到文件末尾。

    Args:
        file_path: 目标文件路径
        marker: 标记名称（如 "AGENT_RUNTIME"）
        content: 要写入的新内容（不含标记本身）

    Returns:
        True 表示替换成功，False 表示标记不存在（已追加）
    """
    text = file_path.read_text(encoding="utf-8")
    pattern = _build_pattern(marker)

    new_block = f"<{marker}_START/>\n{content}\n<{marker}_END/>"

    match = pattern.search(text)
    if match:
        text = text[: match.start()] + new_block + text[match.end() :]
        file_path.write_text(text, encoding="utf-8")
        return True

    # 标记不存在，追加到文件末尾
    if text and not text.endswith("\n"):
        text += "\n"
    text += f"\n{new_block}\n"
    file_path.write_text(text, encoding="utf-8")
    return False
