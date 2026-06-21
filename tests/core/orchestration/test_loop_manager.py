"""
LoopManager 单元测试

测试 Loop 循环定义的 CRUD 操作、校验规则和持久化。
注意：Loop 定义不再包含执行状态字段（status、current_iteration 等），
这些字段已迁移到 LoopExecution。
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
    AgentNotFoundError,
)
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
        """正常创建 Loop 定义"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
        )

        assert loop.loop_id is not None
        assert loop.group_chat_id == loop_manager.group_chat_id
        assert len(loop.nodes) == 3
        assert loop.max_iterations == 10

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
            )

        assert "节点数量不足" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_loop_rejects_non_positive_max_iterations(
        self, loop_manager, valid_nodes
    ):
        """max_iterations 必须大于 0"""
        with pytest.raises(LoopValidationError) as exc_info:
            await loop_manager.create_loop(
                nodes=valid_nodes,
                max_iterations=0,
            )

        assert "max_iterations 必须大于 0" in str(exc_info.value)

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
            )


class TestLoopManagerQuery:
    """测试 Loop 查询"""

    @pytest.mark.asyncio
    async def test_get_loop_success(self, loop_manager, valid_nodes):
        """查询已存在的 Loop"""
        created_loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
        )

        retrieved_loop = loop_manager.get_loop(created_loop.loop_id)

        assert retrieved_loop.loop_id == created_loop.loop_id
        assert retrieved_loop.max_iterations == 10

    def test_get_loop_not_found(self, loop_manager):
        """查询不存在的 Loop"""
        with pytest.raises(LoopNotFoundError):
            loop_manager.get_loop("non_existent_loop_id")

    @pytest.mark.asyncio
    async def test_list_loops_all(self, loop_manager, valid_nodes):
        """查询所有 Loop 定义"""
        loop1 = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
        )
        loop2 = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=5,
        )

        all_loops = loop_manager.list_loops()

        assert len(all_loops) == 2
        loop_ids = [loop["loop_id"] for loop in all_loops]
        assert loop1.loop_id in loop_ids
        assert loop2.loop_id in loop_ids
        # 验证包含 in_memory 标记
        assert all("in_memory" in loop for loop in all_loops)

    @pytest.mark.asyncio
    async def test_list_loops_returns_definition_summary(self, loop_manager, valid_nodes):
        """list_loops 返回 Loop 定义摘要（不含执行状态字段）"""
        await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
        )

        all_loops = loop_manager.list_loops()

        assert len(all_loops) == 1
        summary = all_loops[0]
        assert "loop_id" in summary
        assert "max_iterations" in summary
        assert "nodes_count" in summary
        assert summary["nodes_count"] == 3
        assert "in_memory" in summary
        # 执行状态字段不应出现
        assert "status" not in summary
        assert "current_iteration" not in summary


class TestLoopManagerDelete:
    """测试 Loop 删除"""

    @pytest.mark.asyncio
    async def test_delete_loop_success(self, loop_manager, valid_nodes):
        """删除 Loop 定义"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
        )

        await loop_manager.delete_loop(loop.loop_id)

        with pytest.raises(LoopNotFoundError):
            loop_manager.get_loop(loop.loop_id)

    @pytest.mark.asyncio
    async def test_delete_loop_cascades_executions(self, temp_project_path, valid_nodes):
        """删除 Loop 时级联删除关联的 executions"""
        from agents_hub.core.orchestration.loop_execution_manager import LoopExecutionManager

        group_chat_id = f"test_gc_{uuid4().hex[:8]}"
        manager = LoopManager(group_chat_id, temp_project_path)
        loop = await manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
        )

        # 创建关联的 execution
        exec_manager = LoopExecutionManager(group_chat_id, temp_project_path)
        execution = await exec_manager.create_execution(loop.loop_id, "测试任务")

        # 删除 Loop（传入 exec_manager 以级联删除）
        await manager.delete_loop(loop.loop_id, loop_execution_manager=exec_manager)

        # Loop 应该不存在
        with pytest.raises(LoopNotFoundError):
            manager.get_loop(loop.loop_id)

        # Execution 也应该被级联删除
        # list_executions 应该返回空（因为墓碑记录）
        execs = exec_manager.list_executions(loop_id=loop.loop_id)
        assert len(execs) == 0


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
        )

        # 第二个 Manager：从持久化恢复
        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered_loop = manager2.get_loop_with_lazy_load(loop.loop_id)

        assert recovered_loop.loop_id == loop.loop_id
        assert recovered_loop.max_iterations == loop.max_iterations
        assert len(recovered_loop.nodes) == len(loop.nodes)

    @pytest.mark.asyncio
    async def test_delete_persists_across_restart(self, temp_project_path, valid_nodes):
        """删除 Loop 后重启 Manager，Loop 不再存在"""
        group_chat_id = f"test_gc_{uuid4().hex[:8]}"

        manager1 = LoopManager(group_chat_id, temp_project_path)
        loop = await manager1.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
        )
        await manager1.delete_loop(loop.loop_id)

        # 重启 Manager
        manager2 = LoopManager(group_chat_id, temp_project_path)
        with pytest.raises(LoopNotFoundError):
            manager2.get_loop_with_lazy_load(loop.loop_id)


class TestLoopNodeFields:
    """测试 LoopNode 字段完整性"""

    @pytest.mark.asyncio
    async def test_node_id_auto_generated(self, loop_manager, valid_nodes):
        """node_id 自动生成 UUID"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
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
        )
        original_ids = [n.node_id for n in loop.nodes]

        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered = manager2.get_loop_with_lazy_load(loop.loop_id)
        recovered_ids = [n.node_id for n in recovered.nodes]

        assert original_ids == recovered_ids

    @pytest.mark.asyncio
    async def test_max_retries_defaults_to_3(self, loop_manager, valid_nodes):
        """max_retries 默认值为 3"""
        loop = await loop_manager.create_loop(
            nodes=valid_nodes,
            max_iterations=10,
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
        )

        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered = manager2.get_loop_with_lazy_load(loop.loop_id)
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
        )

        manager2 = LoopManager(group_chat_id, temp_project_path)
        recovered = manager2.get_loop_with_lazy_load(loop.loop_id)
        assert recovered.nodes[0].output_schema_fields == ["# 执行结果", "**任务状态**"]
        assert recovered.nodes[1].output_schema_fields is None  # 默认 None


class TestLoopCompatibility:
    """测试向后兼容性"""

    @pytest.mark.asyncio
    async def test_from_dict_ignores_old_status_fields(self):
        """Loop.from_dict 忽略旧版本的执行状态字段"""
        from agents_hub.core.context.loop_models import Loop
        from datetime import datetime

        now = datetime.now().isoformat()
        old_data = {
            "loop_id": "loop-1",
            "group_chat_id": "group-1",
            "nodes": [
                {
                    "node_type": "normal",
                    "agent_name": "executor",
                    "role_description": "执行任务",
                },
                {
                    "node_type": "terminator",
                    "agent_name": "reviewer",
                    "role_description": "审查",
                },
            ],
            "max_iterations": 5,
            "created_at": now,
            "updated_at": now,
            # 旧版本字段（应被忽略）
            "status": "running",
            "current_iteration": 2,
            "current_node_index": 1,
            "initial_task": "旧任务",
            "error_message": None,
        }

        loop = Loop.from_dict(old_data)

        assert loop.loop_id == "loop-1"
        assert loop.max_iterations == 5
        assert len(loop.nodes) == 2
        # 确认旧字段不会导致错误
        assert not hasattr(loop, "status") or loop.__dataclass_fields__.get("status") is None
