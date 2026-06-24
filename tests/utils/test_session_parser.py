"""Session 解析器测试"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from agents_hub.config.types import AgentPlatform
from agents_hub.utils.session_parser import (
    get_group_chat_messages,
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


# ==================== get_group_chat_messages 测试 ====================


def _write_jsonl(file_path, records: list[dict]):
    """辅助：写入 JSONL 文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _build_message(msg_id: int, agent_name: str, content: str, timestamp: str, **extra) -> dict:
    """辅助：构建符合 GroupChatSession 格式的消息"""
    msg = {
        "id": msg_id,
        "agent_name": agent_name,
        "content": content,
        "timestamp": timestamp,
        "platform": "claude",
    }
    msg.update(extra)
    return msg


@pytest.fixture
def group_chat_messages_file(tmp_path):
    """创建模拟群聊消息 JSONL 文件，包含 meta_data + 3 条消息"""
    project_dir = tmp_path / "teams" / "test-project" / "gc-001"
    project_dir.mkdir(parents=True)
    file_path = project_dir / "gc-001.jsonl"

    records = [
        # meta_data 记录，应被跳过
        {
            "_type": "meta_data",
            "last_compact_loc": 0,
            "next_message_id": 4,
            "created_at": "2026-06-24T10:00:00",
            "updated_at": "2026-06-24T10:30:00",
            "name": "test_session",
        },
        # 正式消息
        _build_message(1, "leader", "开始讨论前端重构方案", "2026-06-24T10:00:00"),
        _build_message(2, "frontend", "建议用 React 18 + Vite", "2026-06-24T10:05:00"),
        _build_message(
            3,
            "backend",
            "同意，API 层保持不变",
            "2026-06-24T10:10:00",
            modified_files=["api/routes.py"],
            git_diff_range="HEAD~1..HEAD",
        ),
    ]
    _write_jsonl(file_path, records)
    return file_path


@pytest.fixture
def patch_messages_path(group_chat_messages_file):
    """patch _find_messages_file 返回测试文件路径"""

    def fake_find(group_chat_id, teams_dir):
        return group_chat_messages_file

    with patch(
        "agents_hub.utils.session_parser._find_messages_file",
        side_effect=fake_find,
    ):
        yield


class TestGetGroupChatMessages:
    """get_group_chat_messages 的契约测试"""

    def test_returns_all_messages_when_no_after_time(self, patch_messages_path):
        """契约：after_time 为 None 时返回全部消息"""
        result = get_group_chat_messages("gc-001")

        assert "<group_chat_session" in result
        assert "leader: 开始讨论前端重构方案" in result
        assert "frontend: 建议用 React 18 + Vite" in result
        assert "backend: 同意，API 层保持不变" in result

    def test_filters_messages_after_time(self, patch_messages_path):
        """契约：只返回 after_time 之后的消息（严格大于）"""
        after = datetime.fromisoformat("2026-06-24T10:00:00")
        result = get_group_chat_messages("gc-001", after_time=after)

        # 10:00:00 的消息应被排除（<= 关系）
        assert "leader: 开始讨论前端重构方案" not in result
        assert "frontend: 建议用 React 18 + Vite" in result
        assert "backend: 同意，API 层保持不变" in result

    def test_excludes_meta_data_record(self, patch_messages_path):
        """契约：跳过 _type=meta_data 的行，不输出到结果中"""
        result = get_group_chat_messages("gc-001")

        assert "meta_data" not in result
        assert "last_compact_loc" not in result

    def test_excludes_attachment_fields(self, patch_messages_path):
        """契约：只输出 timestamp/speaker/content，不包含 modified_files 等附件字段"""
        result = get_group_chat_messages("gc-001")

        assert "modified_files" not in result
        assert "git_diff_range" not in result
        assert "api/routes.py" not in result

    def test_time_range_in_header(self, patch_messages_path):
        """契约：time_range 属性包含首条和末条消息的时间"""
        result = get_group_chat_messages("gc-001")

        assert 'time_range="2026-06-24T10:00:00 ~ 2026-06-24T10:10:00"' in result

    def test_multiline_content_collapsed(self, tmp_path):
        """契约：多行 content 压缩为单行"""
        project_dir = tmp_path / "teams" / "test-project" / "gc-002"
        project_dir.mkdir(parents=True)
        file_path = project_dir / "gc-002.jsonl"
        _write_jsonl(file_path, [
            _build_message(1, "agent", "第一行\n第二行\n第三行", "2026-06-24T10:00:00"),
        ])

        with patch(
            "agents_hub.utils.session_parser._find_messages_file",
            return_value=file_path,
        ):
            result = get_group_chat_messages("gc-002")

        assert "第一行 第二行 第三行" in result
        # 确保没有真正的换行分隔（只在标签对之间有换行）
        lines = result.strip().split("\n")
        assert len(lines) == 3  # <open>, message, </close>

    def test_empty_file_returns_empty_session(self, tmp_path):
        """契约：空文件返回空的 session 标签"""
        project_dir = tmp_path / "teams" / "test-project" / "gc-empty"
        project_dir.mkdir(parents=True)
        file_path = project_dir / "gc-empty.jsonl"
        file_path.touch()

        with patch(
            "agents_hub.utils.session_parser._find_messages_file",
            return_value=file_path,
        ):
            result = get_group_chat_messages("gc-empty")

        assert 'time_range="none"' in result
        assert "leader" not in result

    def test_nonexistent_file_returns_none_session(self):
        """契约：文件不存在时返回 time_range=none 的空 session"""
        with patch(
            "agents_hub.utils.session_parser._find_messages_file",
            return_value=None,
        ):
            result = get_group_chat_messages("gc-404")

        assert 'time_range="none"' in result

    def test_after_time_filters_out_all(self, patch_messages_path):
        """契约：after_time 晚于所有消息时返回空 session"""
        after = datetime.fromisoformat("2026-06-24T23:59:59")
        result = get_group_chat_messages("gc-001", after_time=after)

        assert 'time_range="after' in result
        # 内容区只有 open/close 标签
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_message_order_preserved(self, patch_messages_path):
        """契约：消息按文件中的原始顺序输出"""
        result = get_group_chat_messages("gc-001")
        lines = result.strip().split("\n")

        # 第一行是 open tag，最后是 close tag，中间是消息
        assert lines[0].startswith("<group_chat_session")
        assert lines[-1] == "</group_chat_session>"
        assert "leader" in lines[1]
        assert "frontend" in lines[2]
        assert "backend" in lines[3]
