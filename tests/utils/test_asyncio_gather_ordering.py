"""测试 asyncio.gather 的返回顺序

验证 gather 返回结果的顺序是否与输入顺序一致，而非完成顺序
"""

import asyncio

import pytest


class TestAsyncioGatherOrdering:
    """测试 asyncio.gather 的返回顺序保证"""

    @pytest.mark.asyncio
    async def test_gather_preserves_input_order(self):
        """
        验证 gather 返回结果按输入顺序排列，而非完成顺序

        场景：第二个任务先完成，第一个任务后完成
        预期：结果仍然是 [result1, result2]
        """

        async def task_slow():
            """慢任务：延迟 0.2 秒"""
            await asyncio.sleep(0.2)
            return "slow_result"

        async def task_fast():
            """快任务：延迟 0.1 秒"""
            await asyncio.sleep(0.1)
            return "fast_result"

        # 输入顺序：slow, fast
        results = await asyncio.gather(task_slow(), task_fast())

        # 验证：结果按输入顺序返回，而非完成顺序
        assert len(results) == 2
        assert results[0] == "slow_result", "第一个位置应该是 slow_result（虽然它后完成）"
        assert results[1] == "fast_result", "第二个位置应该是 fast_result（虽然它先完成）"

        print(f"结果顺序: {results}")
        print("[PASS] gather 保持输入顺序，不受完成顺序影响")

    @pytest.mark.asyncio
    async def test_gather_with_agent_simulation(self):
        """
        模拟 _initialize_new_members 场景

        场景：Agent B 比 Agent A 先完成初始化
        预期：results[0] 是 Agent A，results[1] 是 Agent B
        """

        class MockAgentResult:
            def __init__(self, agent_name, session_id, delay):
                self.agent_name = agent_name
                self.session_id = session_id
                self.delay = delay

            async def execute(self):
                await asyncio.sleep(self.delay)
                return self

        # Agent A 慢（0.2s），Agent B 快（0.1s）
        agent_a = MockAgentResult("agent_A", "session_AAA", delay=0.2)
        agent_b = MockAgentResult("agent_B", "session_BBB", delay=0.1)

        # 模拟 _initialize_new_members 的 gather 调用
        results = await asyncio.gather(
            agent_a.execute(),
            agent_b.execute()
        )

        # 验证：results[0] 对应 agent_a，results[1] 对应 agent_b
        assert results[0].agent_name == "agent_A"
        assert results[0].session_id == "session_AAA"
        assert results[1].agent_name == "agent_B"
        assert results[1].session_id == "session_BBB"

        print(f"Agent A (慢): {results[0].agent_name}, {results[0].session_id}")
        print(f"Agent B (快): {results[1].agent_name}, {results[1].session_id}")
        print("[PASS] gather 返回顺序与 agent 列表顺序一致")

    @pytest.mark.asyncio
    async def test_gather_with_list_comprehension(self):
        """
        测试使用列表推导式的 gather（_initialize_new_members 的实际用法）

        场景：
        new_members = [agent_A, agent_B, agent_C]
        results = await asyncio.gather(*[start_conversation(m) for m in new_members])
        """

        async def start_conversation(agent_id, delay):
            """模拟 start_conversation"""
            await asyncio.sleep(delay)
            return f"result_{agent_id}"

        # 模拟成员列表
        new_members = [
            ("A", 0.3),  # 最慢
            ("B", 0.1),  # 最快
            ("C", 0.2),  # 中等
        ]

        # 模拟 _initialize_new_members 的实际调用
        results = await asyncio.gather(*[
            start_conversation(agent_id, delay)
            for agent_id, delay in new_members
        ])

        # 验证：结果顺序与 new_members 顺序一致
        assert results[0] == "result_A", "results[0] 对应 new_members[0]"
        assert results[1] == "result_B", "results[1] 对应 new_members[1]"
        assert results[2] == "result_C", "results[2] 对应 new_members[2]"

        print(f"输入顺序: ['A', 'B', 'C']")
        print(f"完成顺序: B(0.1s) → C(0.2s) → A(0.3s)")
        print(f"结果顺序: {results}")
        print("[PASS] 列表推导式 + gather 保持输入顺序")

    @pytest.mark.asyncio
    async def test_gather_ordering_guarantees_for_update_session(self):
        """
        验证 _initialize_new_members 中的 update_agent_session 调用是否安全

        代码片段：
        results = await asyncio.gather(*[start_conversation(member) for member in new_members])
        for result in results:
            await self.runtime.update_agent_session(result)

        关键问题：result 和对应的 agent 是否匹配？
        """

        class Agent:
            def __init__(self, name):
                self.name = name

        class AgentResult:
            def __init__(self, agent_name, session_id):
                self.agent_name = agent_name
                self.session_id = session_id

        async def start_conversation(agent: Agent):
            # 模拟不同的延迟
            if agent.name == "agent_A":
                await asyncio.sleep(0.3)
            elif agent.name == "agent_B":
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(0.2)
            return AgentResult(agent.name, f"session_{agent.name}")

        # 模拟 new_members
        new_members = [
            Agent("agent_A"),
            Agent("agent_B"),
            Agent("agent_C"),
        ]

        # 模拟 _initialize_new_members 的实际代码
        results = await asyncio.gather(*[start_conversation(member) for member in new_members])

        # 验证：results[i] 对应 new_members[i]
        for i, (member, result) in enumerate(zip(new_members, results)):
            assert result.agent_name == member.name, \
                f"results[{i}] 的 agent_name 应该匹配 new_members[{i}].name"
            assert result.session_id == f"session_{member.name}", \
                f"results[{i}] 的 session_id 应该是 session_{member.name}"

        print("[PASS] gather 返回顺序与输入顺序一致，update_agent_session 是安全的")
        print("结论：group_chat.py:486-488 的代码逻辑是正确的")
        print("      for result in results:")
        print("          await self.runtime.update_agent_session(result)")
        print("      每个 result 会正确匹配对应的 agent")

    @pytest.mark.asyncio
    async def test_gather_exception_handling(self):
        """
        测试 gather 在部分任务失败时的行为

        默认情况下，如果某个任务抛出异常，gather 会立即抛出该异常
        """

        async def task_success():
            await asyncio.sleep(0.1)
            return "success"

        async def task_failure():
            await asyncio.sleep(0.05)
            raise ValueError("task failed")

        # 默认行为：遇到异常立即抛出
        with pytest.raises(ValueError, match="task failed"):
            await asyncio.gather(task_success(), task_failure())

        print("[PASS] gather 遇到异常会立即抛出")

    @pytest.mark.asyncio
    async def test_gather_return_exceptions(self):
        """
        测试 gather(return_exceptions=True) 的行为

        return_exceptions=True 时，异常作为结果返回，不会中断
        """

        async def task_success():
            await asyncio.sleep(0.1)
            return "success"

        async def task_failure():
            await asyncio.sleep(0.05)
            raise ValueError("task failed")

        # return_exceptions=True：异常作为结果返回
        results = await asyncio.gather(
            task_success(),
            task_failure(),
            return_exceptions=True
        )

        # 验证：results[0] 是正常结果，results[1] 是异常对象
        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
        assert str(results[1]) == "task failed"

        print(f"结果: {results}")
        print("[PASS] return_exceptions=True 时异常作为结果返回")
