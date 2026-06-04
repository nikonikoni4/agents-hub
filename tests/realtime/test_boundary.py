"""Realtime module dependency boundary tests"""

from pathlib import Path


def test_realtime_module_does_not_import_api_or_mcp():
    realtime_dir = Path("agents_hub/realtime")
    files = list(realtime_dir.glob("*.py"))
    assert files, "realtime package should contain Python modules"

    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)

    assert "agents_hub.api" not in combined
    assert "agents_hub.mcp" not in combined


def test_core_module_does_not_import_realtime():
    core_dir = Path("agents_hub/core")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in core_dir.rglob("*.py"))

    assert "agents_hub.realtime" not in combined
