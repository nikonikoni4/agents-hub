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
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hello"}],
            },
        },
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:01Z",
            "payload": {
                "id": "msg-2",
                "type": "message",
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


@pytest.fixture
def codex_session_with_tool_calls(tmp_path):
    """创建包含工具调用的 Codex session 文件"""
    data = [
        # user 消息
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {
                "id": "msg-1",
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "List files"}],
            },
        },
        # assistant 消息
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:01Z",
            "payload": {
                "id": "msg-2",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "I'll list the files."}],
            },
        },
        # function_call (工具调用)
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:02Z",
            "payload": {
                "type": "function_call",
                "call_id": "call-1",
                "name": "bash",
                "arguments": '{"command": "ls -la"}',
            },
        },
        # function_call_output (工具结果)
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:03Z",
            "payload": {
                "type": "function_call_output",
                "call_id": "call-1",
                "output": "file1.txt\nfile2.txt",
            },
        },
        # 另一个 function_call
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:04Z",
            "payload": {
                "type": "function_call",
                "call_id": "call-2",
                "name": "read_file",
                "arguments": '{"path": "file1.txt"}',
            },
        },
        # 另一个 function_call_output
        {
            "type": "response_item",
            "timestamp": "2026-01-01T00:00:05Z",
            "payload": {
                "type": "function_call_output",
                "call_id": "call-2",
                "output": "file content",
            },
        },
    ]
    file_path = tmp_path / "test_session_with_tools.jsonl"
    with open(file_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return file_path


def test_parse_codex_session_with_tool_calls(codex_session_with_tool_calls):
    """契约：parse_codex_session 正确解析 function_call 类型的工具调用

    验证方式：
    1. 解析包含 function_call 的 session 文件
    2. 验证 assistant 消息包含 tool_calls
    3. 验证 tool_calls 的 id、name、input 字段正确
    """
    messages = parse_session_file(codex_session_with_tool_calls, AgentPlatform.CODEX)

    # 应该有 2 条消息：user 和 assistant
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "List files"
    assert messages[0].tool_calls is None

    assert messages[1].role == "assistant"
    assert messages[1].content == "I'll list the files."

    # assistant 消息应该有 2 个 tool_calls
    assert messages[1].tool_calls is not None
    assert len(messages[1].tool_calls) == 2

    # 验证第一个 tool_call
    tc1 = messages[1].tool_calls[0]
    assert tc1.id == "call-1"
    assert tc1.name == "bash"
    assert tc1.input == {"command": "ls -la"}

    # 验证第二个 tool_call
    tc2 = messages[1].tool_calls[1]
    assert tc2.id == "call-2"
    assert tc2.name == "read_file"
    assert tc2.input == {"path": "file1.txt"}
