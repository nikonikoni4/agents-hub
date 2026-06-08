"""Session 解析器测试"""

import json

import pytest

from agents_hub.config.types import AgentPlatform
from agents_hub.utils.session_parser import (
    parse_session_file,
)


@pytest.fixture
def claude_session_file(tmp_path):
    """创建测试用 Claude session 文件"""
    data = [
        {
            "type": "user",
            "uuid": "msg-1",
            "timestamp": "2026-01-01T00:00:00Z",
            "message": {"content": "Hello"},
        },
        {
            "type": "assistant",
            "uuid": "msg-2",
            "timestamp": "2026-01-01T00:00:01Z",
            "message": {
                "id": "resp-1",
                "content": [{"type": "text", "text": "Hi there!"}],
                "model": "claude-3",
            },
        },
    ]
    file_path = tmp_path / "test_session.jsonl"
    with open(file_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return file_path


@pytest.fixture
def codex_session_file(tmp_path):
    """创建测试用 Codex session 文件"""
    data = [
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {
                "id": "msg-1",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hello"}],
            },
        },
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:01Z",
            "payload": {
                "id": "msg-2",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Hi there!"}],
            },
        },
    ]
    file_path = tmp_path / "test_session.jsonl"
    with open(file_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return file_path


def test_parse_claude_session(claude_session_file):
    """测试解析 Claude session"""
    messages = parse_session_file(claude_session_file, AgentPlatform.CLAUDE)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there!"
    assert messages[1].model == "claude-3"


def test_parse_codex_session(codex_session_file):
    """测试解析 Codex session"""
    messages = parse_session_file(codex_session_file, AgentPlatform.CODEX)

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there!"
