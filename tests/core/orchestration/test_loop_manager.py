"""
LoopManager 单元测试
"""

import json
import pytest
from pathlib import Path
from uuid import uuid4

from agents_hub.core.context.loop_models import LoopNodeType
from agents_hub.core.orchestration.loop_manager import LoopManager
from agents_hub.core.foundation.exceptions import (
    LoopNotFoundError,
    LoopValidationError,
    LoopStateError,
    AgentNotFoundError,
)
from agents_hub.core.foundation.models import LoopStatus
from agents_hub.utils.logger import setup_logging


@pytest.fixture(scope="session", autouse=True)
def setup_test_logging(tmp_path_factory):
    """初始化测试日志系统"""
    log_dir = tmp_path_factory.mktemp("logs")
    setup_logging(log_dir=log_dir)


@pytest.fixture
def temp_project_path(tmp_path):
    """临时项目路径"""
    return str(tmp_path / "test_project")


@pytest.fixture
def loop_manager(temp_project_path):
    """LoopManager 实例"""
    group_chat_id = f"test_gc_{uuid4().hex[:8]}"
    return LoopManager(group_chat_id, temp_project_path)


@pytest.fixture
def valid_nodes():
    """有效的节点列表（2 个 NORMAL + 1 个 TERMINATOR）"""
    return [
        {
            "node_type": LoopNodeType.NORMAL.value,
            "agent_name": "Agents-Hub-Assistant",
            "role_description": "执行代码生成任务",
            "output_schema": None,
        },
        {
            "node_type": LoopNodeType.NORMAL.value,
            "agent_name": "bare_claude",
            "role_description": "审查生成的代码",
            "output_schema": None,
        },
        {
            "node_type": LoopNodeType.TERMINATOR.value,
            "agent_name": "manager",
            "role_description": "判断是否继续循环",
            "output_schema": None,
        },
    ]


class TestLoopManagerCreate:
    """测试 Loop 创建"""

    @pytest.mark.asyncio
    async def test_create_loop_success(self, loop_manager, valid_nodes):
        """正常创建 Loop"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="生成一个计算器",
        )

        assert loop.loop_id is not None
        assert loop.group_chat_id == loop_manager.group_chat_id
        assert len(loop.nodes) == 3
        assert loop.status == LoopStatus.CREATED.value
        assert loop.max_iterations == 10
        assert loop.current_iteration == 1
        assert loop.current_node_index == 0
        assert loop.initial_task == "生成一个计算器"

    @pytest.mark.asyncio
    async def test_create_loop_insufficient_nodes(self, loop_manager):
        """节点数量不足（< 2）"""
        nodes = [
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "executor",
                "role_description": "执行任务",
                "output_schema": None,
            }
        ]

        with pytest.raises(LoopValidationError) as exc_info:
            await loop_manager.create_loop(
                nodes=nodes,
                max_iterations=10,
                initial_task="测试任务",
            )

        assert "节点数量不足" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_loop_no_terminator(self, loop_manager):
        """缺少 TERMINATOR 节点"""
        nodes = [
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "executor",
                "role_description": "执行任务",
                "output_schema": None,
            },
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "reviewer",
                "role_description": "审查任务",
                "output_schema": None,
            },
        ]

        with pytest.raises(LoopValidationError) as exc_info:
            await loop_manager.create_loop(
                nodes=nodes,
                max_iterations=10,
                initial_task="测试任务",
            )

        assert "缺少 TERMINATOR 节点" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_loop_multiple_terminators(self, loop_manager):
        """多个 TERMINATOR 节点"""
        nodes = [
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "executor",
                "role_description": "执行任务",
                "output_schema": None,
            },
            {
                "node_type": LoopNodeType.TERMINATOR.value,
                "agent_name": "reviewer",
                "role_description": "判断1",
                "output_schema": None,
            },
            {
                "node_type": LoopNodeType.TERMINATOR.value,
                "agent_name": "manager",
                "role_description": "判断2",
                "output_schema": None,
            },
        ]

        with pytest.raises(LoopValidationError) as exc_info:
            await loop_manager.create_loop(
                nodes=nodes,
                max_iterations=10,
                initial_task="测试任务",
            )

        assert "TERMINATOR 节点过多" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_loop_agent_not_found(self, loop_manager):
        """Agent 不存在"""
        nodes = [
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "non_existent_agent",
                "role_description": "执行任务",
                "output_schema": None,
            },
            {
                "node_type": LoopNodeType.TERMINATOR.value,
                "agent_name": "manager",
                "role_description": "判断",
                "output_schema": None,
            },
        ]

        with pytest.raises(AgentNotFoundError):
            await loop_manager.create_loop(
                nodes=nodes,
                max_iterations=10,
                initial_task="测试任务",
            )

    @pytest.mark.asyncio
    async def test_create_loop_concurrent_running_conflict(
        self, loop_manager, valid_nodes
    ):
        """并发限制：已有 RUNNING Loop 时不能创建新的"""
        # 创建第一个 Loop
        loop1 = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="任务1",
        )

        # 更新为 RUNNING
        await loop_manager.update_loop_status(loop1.loop_id, LoopStatus.RUNNING.value)

        # 尝试创建第二个 Loop（应该失败）
        with pytest.raises(LoopValidationError) as exc_info:
            await loop_manager.create_loop(
                nodes=valid_nodes,
                max_iterations=10,
                initial_task="任务2",
            )

        assert "已有 RUNNING 状态的 Loop" in str(exc_info.value)


class TestLoopManagerQuery:
    """测试 Loop 查询"""

    @pytest.mark.asyncio
    async def test_get_loop_success(self, loop_manager, valid_nodes):
        """查询已存在的 Loop"""
        created_loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        retrieved_loop = loop_manager.get_loop(created_loop.loop_id)

        assert retrieved_loop.loop_id == created_loop.loop_id
        assert retrieved_loop.status == LoopStatus.CREATED.value

    def test_get_loop_not_found(self, loop_manager):
        """查询不存在的 Loop"""
        with pytest.raises(LoopNotFoundError):
            loop_manager.get_loop("non_existent_loop_id")

    @pytest.mark.asyncio
    async def test_list_loops_all(self, loop_manager, valid_nodes):
        """查询所有 Loop"""
        loop1 = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="任务1",
        )
        loop2 = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=5,
            initial_task="任务2",
        )

        all_loops = loop_manager.list_loops()

        assert len(all_loops) == 2
        loop_ids = [loop.loop_id for loop in all_loops]
        assert loop1.loop_id in loop_ids
        assert loop2.loop_id in loop_ids

    @pytest.mark.asyncio
    async def test_list_loops_by_status(self, loop_manager, valid_nodes):
        """按状态过滤 Loop"""
        loop1 = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="任务1",
        )
        loop2 = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=5,
            initial_task="任务2",
        )

        # 更新 loop1 为 RUNNING
        await loop_manager.update_loop_status(loop1.loop_id, LoopStatus.RUNNING.value)

        # 查询 RUNNING 状态
        running_loops = loop_manager.list_loops(status=LoopStatus.RUNNING.value)
        assert len(running_loops) == 1
        assert running_loops[0].loop_id == loop1.loop_id

        # 查询 CREATED 状态
        created_loops = loop_manager.list_loops(status=LoopStatus.CREATED.value)
        assert len(created_loops) == 1
        assert created_loops[0].loop_id == loop2.loop_id


class TestLoopManagerUpdate:
    """测试 Loop 更新"""

    @pytest.mark.asyncio
    async def test_update_loop_status(self, loop_manager, valid_nodes):
        """更新 Loop 状态"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        updated_loop = await loop_manager.update_loop_status(
            loop.loop_id,
            LoopStatus.RUNNING.value,
        )

        assert updated_loop.status == LoopStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_update_loop_iteration_and_node(self, loop_manager, valid_nodes):
        """更新 Loop 迭代次数和节点索引"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        updated_loop = await loop_manager.update_loop_status(
            loop.loop_id,
            LoopStatus.RUNNING.value,
            current_iteration=3,
            current_node_index=1,
        )

        assert updated_loop.current_iteration == 3
        assert updated_loop.current_node_index == 1

    @pytest.mark.asyncio
    async def test_update_loop_with_error(self, loop_manager, valid_nodes):
        """更新 Loop 为失败状态并记录错误"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        # 先转为 RUNNING
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)

        updated_loop = await loop_manager.update_loop_status(
            loop.loop_id,
            LoopStatus.FAILED.value,
            error_message="节点执行超时",
        )

        assert updated_loop.status == LoopStatus.FAILED.value
        assert updated_loop.error_message == "节点执行超时"


class TestLoopManagerDelete:
    """测试 Loop 删除"""

    @pytest.mark.asyncio
    async def test_delete_loop_success(self, loop_manager, valid_nodes):
        """删除非 RUNNING Loop"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        await loop_manager.delete_loop(loop.loop_id)

        with pytest.raises(LoopNotFoundError):
            loop_manager.get_loop(loop.loop_id)

    @pytest.mark.asyncio
    async def test_delete_running_loop_fails(self, loop_manager, valid_nodes):
        """删除 RUNNING Loop 失败"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        # 更新为 RUNNING
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)

        # 尝试删除
        with pytest.raises(LoopStateError) as exc_info:
            await loop_manager.delete_loop(loop.loop_id)

        assert "不支持操作" in str(exc_info.value)


class TestLoopManagerPersistence:
    """测试 Loop 持久化"""

    @pytest.mark.asyncio
    async def test_persistence_and_recovery(self, temp_project_path, valid_nodes):
        """创建后可以从 JSONL 恢复"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        # 第一个 Manager：创建 Loop
        manager1 = LoopManager(group_chat_id, temp_project_path)
        loop = await manager1.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        # 第二个 Manager：从持久化恢复
        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered_loop = manager2.get_loop(loop.loop_id)

        assert recovered_loop.loop_id == loop.loop_id
        assert recovered_loop.status == loop.status
        assert len(recovered_loop.nodes) == len(loop.nodes)

    @pytest.mark.asyncio
    async def test_persistence_same_id_takes_latest(
        self, temp_project_path, valid_nodes
    ):
        """同一 loop_id 多条记录取最新"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopManager(group_chat_id, temp_project_path)
        loop = await manager1.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        # 更新状态（追加新记录）
        await manager1.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)
        await manager1.update_loop_status(loop.loop_id, LoopStatus.COMPLETED.value)

        # 重新加载
        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered_loop = manager2.get_loop(loop.loop_id)

        # 应该取最新状态
        assert recovered_loop.status == LoopStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_delete_persists_across_restart(self, temp_project_path, valid_nodes):
        """删除 Loop 后重启 Manager，Loop 不再存在"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopManager(group_chat_id, temp_project_path)
        loop = await manager1.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        await manager1.delete_loop(loop.loop_id)

        # 重启 Manager
        manager2 = LoopManager(group_chat_id, temp_project_path)
        with pytest.raises(LoopNotFoundError):
            manager2.get_loop(loop.loop_id)


class TestLoopNodeFields:
    """测试 LoopNode PRD 字段完整性"""

    @pytest.mark.asyncio
    async def test_node_id_auto_generated(self, loop_manager, valid_nodes):
        """node_id 自动生成 UUID"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        for node in loop.nodes:
            assert node.node_id is not None
            assert len(node.node_id) > 0

    @pytest.mark.asyncio
    async def test_node_id_preserved_in_persistence(
        self, temp_project_path, valid_nodes
    ):
        """node_id 序列化/反序列化后保持一致"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopManager(group_chat_id, temp_project_path)
        loop = await manager1.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        original_ids = [n.node_id for n in loop.nodes]

        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered = manager2.get_loop(loop.loop_id)
        recovered_ids = [n.node_id for n in recovered.nodes]

        assert original_ids == recovered_ids

    @pytest.mark.asyncio
    async def test_max_retries_defaults_to_3(self, loop_manager, valid_nodes):
        """max_retries 默认值为 3"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        for node in loop.nodes:
            assert node.max_retries == 3

    @pytest.mark.asyncio
    async def test_max_retries_custom_value(self, loop_manager):
        """max_retries 支持自定义值"""
        nodes = [
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "Agents-Hub-Assistant",
                "role_description": "执行任务",
                "max_retries": 5,
            },
            {
                "node_type": LoopNodeType.TERMINATOR.value,
                "agent_name": "manager",
                "role_description": "判断",
            },
        ]
        loop = await loop_manager.create_loop(
            nodes=nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        assert loop.nodes[0].max_retries == 5
        assert loop.nodes[1].max_retries == 3  # 默认值

    @pytest.mark.asyncio
    async def test_output_schema_prompt_preserved_in_persistence(
        self, temp_project_path
    ):
        """output_schema_prompt 序列化/反序列化后保持一致"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"
        nodes = [
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "Agents-Hub-Assistant",
                "role_description": "执行任务",
                "output_schema_prompt": "请输出以下格式：\n# 执行结果\n**任务状态**：完成/失败",
            },
            {
                "node_type": LoopNodeType.TERMINATOR.value,
                "agent_name": "manager",
                "role_description": "判断",
            },
        ]

        manager1 = LoopManager(group_chat_id, temp_project_path)
        loop = await manager1.create_loop(
            nodes=nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered = manager2.get_loop(loop.loop_id)
        assert "执行结果" in recovered.nodes[0].output_schema_prompt

    @pytest.mark.asyncio
    async def test_output_schema_fields_preserved_in_persistence(
        self, temp_project_path
    ):
        """output_schema_fields 序列化/反序列化后保持一致"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"
        nodes = [
            {
                "node_type": LoopNodeType.NORMAL.value,
                "agent_name": "Agents-Hub-Assistant",
                "role_description": "执行任务",
                "output_schema_fields": ["# 执行结果", "**任务状态**"],
            },
            {
                "node_type": LoopNodeType.TERMINATOR.value,
                "agent_name": "manager",
                "role_description": "判断",
            },
        ]

        manager1 = LoopManager(group_chat_id, temp_project_path)
        loop = await manager1.create_loop(
            nodes=nodes,
            max_iterations=10,
            initial_task="测试任务",
        )

        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered = manager2.get_loop(loop.loop_id)
        assert recovered.nodes[0].output_schema_fields == ["# 执行结果", "**任务状态**"]
        assert recovered.nodes[1].output_schema_fields is None  # 默认 None


class TestLoopStateMachine:
    """测试 Loop 状态机校验"""

    @pytest.mark.asyncio
    async def test_invalid_transition_completed_to_running(
        self, loop_manager, valid_nodes
    ):
        """COMPLETED 不能转为 RUNNING"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.COMPLETED.value)

        with pytest.raises(LoopStateError):
            await loop_manager.update_loop_status(
                loop.loop_id, LoopStatus.RUNNING.value
            )

    @pytest.mark.asyncio
    async def test_invalid_transition_failed_to_running(
        self, loop_manager, valid_nodes
    ):
        """FAILED 不能转为 RUNNING"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.FAILED.value)

        with pytest.raises(LoopStateError):
            await loop_manager.update_loop_status(
                loop.loop_id, LoopStatus.RUNNING.value
            )

    @pytest.mark.asyncio
    async def test_valid_transition_created_to_running(self, loop_manager, valid_nodes):
        """CREATED 可以转为 RUNNING"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        updated = await loop_manager.update_loop_status(
            loop.loop_id, LoopStatus.RUNNING.value
        )
        assert updated.status == LoopStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_valid_transition_running_to_completed(
        self, loop_manager, valid_nodes
    ):
        """RUNNING 可以转为 COMPLETED"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)
        updated = await loop_manager.update_loop_status(
            loop.loop_id, LoopStatus.COMPLETED.value
        )
        assert updated.status == LoopStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_valid_transition_running_to_failed(self, loop_manager, valid_nodes):
        """RUNNING 可以转为 FAILED"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)
        updated = await loop_manager.update_loop_status(
            loop.loop_id, LoopStatus.FAILED.value, error_message="超时"
        )
        assert updated.status == LoopStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_valid_transition_running_to_paused(self, loop_manager, valid_nodes):
        """RUNNING 可以转为 PAUSED"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
            initial_task="测试任务",
        )
        await loop_manager.update_loop_status(loop.loop_id, LoopStatus.RUNNING.value)
        updated = await loop_manager.update_loop_status(
            loop.loop_id, LoopStatus.PAUSED.value
        )
        assert updated.status == LoopStatus.PAUSED.value
