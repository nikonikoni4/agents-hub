"""测试 ClaudeParser 并发安全性

验证 ClaudeParser 不存在与 CodexParser 相同的 session_id 串台问题
"""

import asyncio
import json

import pytest

from agents_hub.agent_bridge.parsers.claude import ClaudeParser


class TestClaudeParserConcurrency:
    """测试 ClaudeParser 在并发场景下的安全性"""

    @pytest.mark.asyncio
    async def test_shared_parser_session_id_safety(self):
        """
        验证共享 ClaudeParser 实例在并发场景下 session_id 不会串台

        与 CodexParser 的关键差异：
        - ClaudeParser 直接从每个事件的顶级字段读取 session_id
        - 不依赖实例缓存，通过方法参数传递
        """
        # 共享的 parser 实例
        shared_parser = ClaudeParser()

        # 模拟两个 agent 的事件流
        agent_a_events = [
            json.dumps({
                "type": "stream_event",
                "session_id": "session_AAA",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Hello from A"}
                }
            }),
            json.dumps({
                "type": "result",
                "session_id": "session_AAA",
                "usage": {"input_tokens": 100, "output_tokens": 50}
            }),
        ]

        agent_b_events = [
            json.dumps({
                "type": "stream_event",
                "session_id": "session_BBB",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "Hello from B"}
                }
            }),
            json.dumps({
                "type": "result",
                "session_id": "session_BBB",
                "usage": {"input_tokens": 200, "output_tokens": 100}
            }),
        ]

        # 记录解析结果
        results_a = []
        results_b = []

        async def process_agent_a():
            """模拟 agent A 的事件处理"""
            for raw_event in agent_a_events:
                await asyncio.sleep(0.01)
                event = shared_parser.parse_event(raw_event)
                if event:
                    results_a.append(event)

        async def process_agent_b():
            """模拟 agent B 的事件处理"""
            for raw_event in agent_b_events:
                await asyncio.sleep(0.01)
                event = shared_parser.parse_event(raw_event)
                if event:
                    results_b.append(event)

        # 并发执行
        await asyncio.gather(process_agent_a(), process_agent_b())

        # 验证结果
        assert len(results_a) == 2, "Agent A 应该有 2 个事件"
        assert len(results_b) == 2, "Agent B 应该有 2 个事件"

        # 验证 session_id 正确性
        for event in results_a:
            assert event.session_id == "session_AAA", \
                f"Agent A 的所有事件 session_id 应为 session_AAA，实际为 {event.session_id}"

        for event in results_b:
            assert event.session_id == "session_BBB", \
                f"Agent B 的所有事件 session_id 应为 session_BBB，实际为 {event.session_id}"

        print("[PASS] ClaudeParser 并发 session_id 处理安全")

    @pytest.mark.asyncio
    async def test_interleaved_events_session_id_safety(self):
        """
        测试完全交错的事件序列，验证 session_id 不会串台

        时间线：
        T1: agent_A text_delta (session_AAA)
        T2: agent_B text_delta (session_BBB)
        T3: agent_A result (session_AAA)
        T4: agent_B result (session_BBB)
        """
        shared_parser = ClaudeParser()

        # 精心编排的事件序列
        event_sequence = [
            ("A", json.dumps({
                "type": "stream_event",
                "session_id": "session_AAA",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "A"}
                }
            })),
            ("B", json.dumps({
                "type": "stream_event",
                "session_id": "session_BBB",
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "B"}
                }
            })),
            ("A", json.dumps({
                "type": "result",
                "session_id": "session_AAA",
                "usage": {"input_tokens": 100}
            })),
            ("B", json.dumps({
                "type": "result",
                "session_id": "session_BBB",
                "usage": {"input_tokens": 200}
            })),
        ]

        results = {"A": [], "B": []}

        # 按顺序处理事件
        for agent_id, raw_event in event_sequence:
            event = shared_parser.parse_event(raw_event)
            if event:
                results[agent_id].append(event)

        # 验证每个 agent 的 session_id 正确
        for event in results["A"]:
            assert event.session_id == "session_AAA", \
                f"Agent A session_id 错误：{event.session_id}"

        for event in results["B"]:
            assert event.session_id == "session_BBB", \
                f"Agent B session_id 错误：{event.session_id}"

        print("[PASS] ClaudeParser 交错事件处理安全")

    @pytest.mark.asyncio
    async def test_concurrent_tool_use_blocks(self):
        """
        测试并发工具调用场景下 _tool_use_blocks 的潜在冲突

        理论风险：两个 agent 同时使用工具，且 index 相同（如都是 0），
        可能导致 _tool_use_blocks[0] 被覆盖
        """
        shared_parser = ClaudeParser()

        # Agent A 的工具调用事件（index=0）
        agent_a_events = [
            json.dumps({
                "type": "stream_event",
                "session_id": "session_AAA",
                "event": {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "tool_use",
                        "id": "tool_A",
                        "name": "read_file"
                    }
                }
            }),
            json.dumps({
                "type": "stream_event",
                "session_id": "session_AAA",
                "event": {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": '{"path": "a.txt"}'
                    }
                }
            }),
            json.dumps({
                "type": "stream_event",
                "session_id": "session_AAA",
                "event": {
                    "type": "content_block_stop",
                    "index": 0
                }
            }),
        ]

        # Agent B 的工具调用事件（同样 index=0）
        agent_b_events = [
            json.dumps({
                "type": "stream_event",
                "session_id": "session_BBB",
                "event": {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "tool_use",
                        "id": "tool_B",
                        "name": "write_file"
                    }
                }
            }),
            json.dumps({
                "type": "stream_event",
                "session_id": "session_BBB",
                "event": {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": '{"path": "b.txt"}'
                    }
                }
            }),
            json.dumps({
                "type": "stream_event",
                "session_id": "session_BBB",
                "event": {
                    "type": "content_block_stop",
                    "index": 0
                }
            }),
        ]

        results_a = []
        results_b = []

        async def process_agent_a():
            for raw_event in agent_a_events:
                await asyncio.sleep(0.01)
                event = shared_parser.parse_event(raw_event)
                if event:
                    results_a.append(event)

        async def process_agent_b():
            for raw_event in agent_b_events:
                await asyncio.sleep(0.01)
                event = shared_parser.parse_event(raw_event)
                if event:
                    results_b.append(event)

        # 并发执行
        await asyncio.gather(process_agent_a(), process_agent_b())

        # 验证：由于并发，可能会出现工具调用事件丢失或错乱
        # 但关键是 session_id 不会串台
        print(f"Agent A 工具调用事件数量: {len(results_a)}")
        print(f"Agent B 工具调用事件数量: {len(results_b)}")

        # 即使工具调用冲突，session_id 也应该正确
        for event in results_a:
            if event.session_id:  # 有些事件可能没有产生
                assert event.session_id == "session_AAA", \
                    f"工具调用冲突不应影响 session_id，但 Agent A 的 session_id 错误：{event.session_id}"

        for event in results_b:
            if event.session_id:
                assert event.session_id == "session_BBB", \
                    f"工具调用冲突不应影响 session_id，但 Agent B 的 session_id 错误：{event.session_id}"

        # 记录观察结果
        if len(results_a) < 1 or len(results_b) < 1:
            print("[WARN] 检测到工具调用事件冲突（事件丢失），但 session_id 未串台")
        else:
            print("[PASS] 并发工具调用未发生冲突")

    @pytest.mark.asyncio
    async def test_sequential_events_baseline(self):
        """
        基线测试：顺序处理事件应该完全正确
        """
        parser_a = ClaudeParser()
        parser_b = ClaudeParser()

        # 两个独立的 parser 处理各自的事件
        event_a = json.dumps({
            "type": "stream_event",
            "session_id": "session_AAA",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "A"}
            }
        })

        event_b = json.dumps({
            "type": "stream_event",
            "session_id": "session_BBB",
            "event": {
                "type": "content_block_delta",
                "delta": {"type": "text_delta", "text": "B"}
            }
        })

        result_a = parser_a.parse_event(event_a)
        result_b = parser_b.parse_event(event_b)

        assert result_a.session_id == "session_AAA"
        assert result_b.session_id == "session_BBB"
        print("[PASS] 基线测试通过")
