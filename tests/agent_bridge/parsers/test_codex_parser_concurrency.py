"""测试 CodexParser 并发竞态条件

复现 bug: docs/history-bugs/2026-06-15-parser-concurrency-race-condition.md
"""

import asyncio
import json

import pytest

from agents_hub.agent_bridge.parsers.codex import CodexParser


class TestCodexParserConcurrency:
    """测试 CodexParser 在并发场景下的竞态条件"""

    @pytest.mark.asyncio
    async def test_shared_parser_thread_id_race_condition(self):
        """
        复现场景：多个 agent 共享同一个 CodexParser 实例，并发处理事件时
        _thread_id 被互相覆盖，导致 session_id 错误
        """
        # 共享的 parser 实例（模拟 bridge.py 中的单例）
        shared_parser = CodexParser()

        # 模拟两个 agent 的事件流
        agent_a_events = [
            json.dumps({"type": "thread.started", "thread_id": "thread_AAA"}),
            json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Hello from A"},
                # 注意：item.completed 事件没有携带 thread_id
            }),
        ]

        agent_b_events = [
            json.dumps({"type": "thread.started", "thread_id": "thread_BBB"}),
            json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Hello from B"},
                # 注意：item.completed 事件没有携带 thread_id
            }),
        ]

        # 记录解析结果
        results_a = []
        results_b = []

        async def process_agent_a():
            """模拟 agent A 的事件处理"""
            for raw_event in agent_a_events:
                # 模拟事件之间有短暂延迟
                await asyncio.sleep(0.01)
                event = shared_parser.parse_event(raw_event)
                if event:
                    results_a.append(event)

        async def process_agent_b():
            """模拟 agent B 的事件处理"""
            for raw_event in agent_b_events:
                # 模拟事件之间有短暂延迟
                await asyncio.sleep(0.01)
                event = shared_parser.parse_event(raw_event)
                if event:
                    results_b.append(event)

        # 并发执行（模拟 asyncio.gather）
        await asyncio.gather(process_agent_a(), process_agent_b())

        # 验证结果
        # 注意：由于首句检测机制，item.completed + agent_message 会生成 2 个事件
        # （TEXT_DELTA + FIRST_RESPONSE），但由于并发竞态，实际事件数量可能不同
        assert len(results_a) >= 1, "Agent A 应该至少有 1 个事件"
        assert len(results_b) >= 1, "Agent B 应该至少有 1 个事件"

        # 关键断言：每个 agent 的 session_id 应该是自己的 thread_id
        # 但由于竞态条件，可能会出现错误
        # 注意：results_a[0] 可能是 INIT 事件，需要找到 TEXT_DELTA 事件
        text_delta_a = next((e for e in results_a if e.type.value == "text_delta"), results_a[0])
        text_delta_b = next((e for e in results_b if e.type.value == "text_delta"), results_b[0])
        session_id_a = text_delta_a.session_id
        session_id_b = text_delta_b.session_id

        print(f"Agent A session_id: {session_id_a} (expected: thread_AAA)")
        print(f"Agent B session_id: {session_id_b} (expected: thread_BBB)")

        # Bug 复现验证：由于并发执行，_thread_id 被覆盖
        # Agent A 的 session_id 应该是 thread_AAA，但实际拿到了 thread_BBB
        # 这证明了共享 parser 的 _thread_id 被后执行的 Agent B 覆盖
        assert session_id_a == "thread_BBB", f"Bug 已复现：Agent A 的 session_id 被覆盖为 {session_id_a}"
        assert session_id_b == "thread_BBB", f"Agent B 的 session_id 正确（{session_id_b}）"

    @pytest.mark.asyncio
    async def test_independent_parser_no_race_condition(self):
        """
        对比测试：每个 agent 使用独立的 parser 实例，不会出现竞态
        """
        # 每个 agent 有自己的 parser 实例
        parser_a = CodexParser()
        parser_b = CodexParser()

        # 模拟两个 agent 的事件流
        agent_a_events = [
            json.dumps({"type": "thread.started", "thread_id": "thread_AAA"}),
            json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Hello from A"},
            }),
        ]

        agent_b_events = [
            json.dumps({"type": "thread.started", "thread_id": "thread_BBB"}),
            json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Hello from B"},
            }),
        ]

        # 记录解析结果
        results_a = []
        results_b = []

        async def process_agent_a():
            """模拟 agent A 的事件处理"""
            for raw_event in agent_a_events:
                await asyncio.sleep(0.01)
                event = parser_a.parse_event(raw_event)
                if event:
                    results_a.append(event)

        async def process_agent_b():
            """模拟 agent B 的事件处理"""
            for raw_event in agent_b_events:
                await asyncio.sleep(0.01)
                event = parser_b.parse_event(raw_event)
                if event:
                    results_b.append(event)

        # 并发执行
        await asyncio.gather(process_agent_a(), process_agent_b())

        # 验证结果
        # 注意：由于首句检测机制，item.completed + agent_message 会生成 2 个事件
        assert len(results_a) >= 1
        assert len(results_b) >= 1

        # 找到 TEXT_DELTA 事件来验证 session_id
        text_delta_a = next((e for e in results_a if e.type.value == "text_delta"), results_a[0])
        text_delta_b = next((e for e in results_b if e.type.value == "text_delta"), results_b[0])
        session_id_a = text_delta_a.session_id
        session_id_b = text_delta_b.session_id

        # 使用独立 parser，session_id 应该是正确的
        assert session_id_a == "thread_AAA", "独立 parser：Agent A session_id 正确"
        assert session_id_b == "thread_BBB", "独立 parser：Agent B session_id 正确"

    @pytest.mark.asyncio
    async def test_interleaved_events_worst_case(self):
        """
        测试最坏情况：事件完全交错

        时间线：
        T1: agent_A thread.started -> parser._thread_id = "AAA"
        T2: agent_B thread.started -> parser._thread_id = "BBB" (覆盖)
        T3: agent_A item.completed -> session_id = "BBB" (错误！)
        T4: agent_B item.completed -> session_id = "BBB" (正确)
        """
        shared_parser = CodexParser()

        # 精心编排的事件序列，模拟最坏的交错情况
        event_sequence = [
            ("A", json.dumps({"type": "thread.started", "thread_id": "thread_AAA"})),
            ("B", json.dumps({"type": "thread.started", "thread_id": "thread_BBB"})),
            ("A", json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Hello from A"},
            })),
            ("B", json.dumps({
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "Hello from B"},
            })),
        ]

        results = {"A": [], "B": []}

        # 按顺序处理事件
        for agent_id, raw_event in event_sequence:
            event = shared_parser.parse_event(raw_event)
            if event:
                results[agent_id].append(event)

        # 验证 Bug：Agent A 的 session_id 应该是 AAA，但实际是 BBB
        # 注意：results["A"][0] 可能是 INIT 事件，需要找到 TEXT_DELTA 事件
        text_delta_a = next((e for e in results["A"] if e.type.value == "text_delta"), results["A"][0])
        text_delta_b = next((e for e in results["B"] if e.type.value == "text_delta"), results["B"][0])
        session_id_a = text_delta_a.session_id
        session_id_b = text_delta_b.session_id

        print(f"最坏情况 - Agent A session_id: {session_id_a} (expected: thread_AAA)")
        print(f"最坏情况 - Agent B session_id: {session_id_b} (expected: thread_BBB)")

        # Bug 验证
        assert session_id_a != "thread_AAA", "Bug 复现：Agent A 的 session_id 被覆盖"
        assert session_id_a == "thread_BBB", "Bug 复现：Agent A 拿到了 Agent B 的 thread_id"
        assert session_id_b == "thread_BBB", "Agent B 的 session_id 正确"
