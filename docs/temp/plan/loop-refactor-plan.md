# Loop 定义与执行分离重构方案

## Context

当前 Loop 设计将"循环定义"和"执行实例"混合在同一个数据模型中，导致以下问题：

1. **复用性差**：每次执行不同任务都需要删除旧 Loop 并创建新 Loop，即使循环结构完全相同
2. **语义不清**：`initial_task` 作为 Loop 的持久化字段，但实际上是"执行参数"而非"定义属性"
3. **历史不可追溯**：无法查看同一 Loop 定义的多次执行历史
4. **内存管理矛盾**：单 Loop 保持策略与复用需求冲突

**设计目标**：
- 将 Loop 拆分为 `Loop`（循环定义，可复用模板）和 `LoopExecution`（执行实例，一次性）
- `initial_task` 从 `create_loop()` 移到 `start_loop()`，作为执行参数而非定义属性
- 支持同一 Loop 定义多次启动，每次传入不同的 `initial_task`
- 保留完整的执行历史，方便追溯和分析

## Current Implementation Analysis

### 数据模型
- **Loop**：包含 11 个字段（loop_id, group_chat_id, nodes, status, max_iterations, current_iteration, current_node_index, initial_task, created_at, updated_at, error_message）
- **LoopNode**：包含 7 个字段（node_id, node_type, agent_name, role_description, output_schema_prompt, output_schema_fields, max_retries）

### 关键问题
1. `initial_task` 耦合在 Loop 模型中，但只在第一次发送时使用（loop_executor.py:537）
2. 执行状态（status, current_iteration, current_node_index, error_message）与定义混在一起
3. 状态机不支持 COMPLETED/FAILED → RUNNING 转换，无法复用

### initial_task 使用路径
```
MCP create_loop(initial_task)
  ↓
GroupChat.create_loop(initial_task)
  ↓
LoopManager.create_loop(initial_task) → 存储在 loop.initial_task
  ↓
LoopExecutor.__init__(loop) → self._last_node_output = loop.initial_task
  ↓
LoopExecutor.run() → _send_to_node(first_node, self.loop.initial_task)
```

## Implementation Plan

### 1. 创建新的数据模型

**文件**：`agents_hub/core/context/loop_models.py`

**新增 LoopExecution 类**：
```python
@dataclass
class LoopExecution:
    execution_id: str               # 执行实例 ID（UUID）
    loop_id: str                    # 关联的 Loop 定义 ID
    initial_task: str               # 本次执行的初始任务
    status: str                     # created/running/paused/completed/failed
    current_iteration: int          # 当前循环轮次
    current_node_index: int         # 当前节点索引
    created_at: datetime            # 创建时间
    updated_at: datetime            # 最后更新时间
    error_message: str | None       # 错误信息
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        
    @staticmethod
    def from_dict(data: dict) -> "LoopExecution":
        """从字典反序列化"""
```

**修改 Loop 类**（移除执行状态字段）：
```python
@dataclass
class Loop:
    loop_id: str                    # Loop 定义 ID
    group_chat_id: str              # 所属群聊
    nodes: list[LoopNode]           # 节点列表
    max_iterations: int             # 最大循环次数
    created_at: datetime            # 创建时间
    updated_at: datetime            # 最后更新时间
    
    # 移除字段：initial_task, status, current_iteration, current_node_index, error_message
```

**新增 LoopExecutionStatus 枚举**：
```python
class LoopExecutionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

### 2. 创建 LoopExecutionManager

**新文件**：`agents_hub/core/orchestration/loop_execution_manager.py`

**职责**：
- 管理 LoopExecution 的 CRUD
- 持久化到 `loop_executions.jsonl`
- 内存缓存当前活跃的 execution
- 提供懒加载和查询接口

**主要方法**：
```python
class LoopExecutionManager:
    def __init__(self, group_chat_paths, logger):
        self._executions: dict[str, LoopExecution] = {}  # 内存缓存
        self._lock = asyncio.Lock()
        
    async def create_execution(
        self, 
        loop_id: str, 
        initial_task: str
    ) -> LoopExecution:
        """创建新的执行实例"""
        
    def get_execution(self, execution_id: str) -> LoopExecution:
        """查询执行实例（仅内存）"""
        
    def get_execution_with_lazy_load(self, execution_id: str) -> LoopExecution:
        """查询执行实例（支持懒加载）"""
        
    async def update_execution_status(
        self,
        execution_id: str,
        status: str,
        current_iteration: int | None = None,
        current_node_index: int | None = None,
        error_message: str | None = None,
    ) -> LoopExecution:
        """更新执行状态并持久化"""
        
    def list_executions(
        self, 
        loop_id: str | None = None,
        status: str | None = None
    ) -> list[dict]:
        """查询执行历史（直接读 JSONL）"""
        
    async def delete_execution(self, execution_id: str) -> None:
        """删除执行实例（写墓碑记录）"""
        
    def clear_other_executions(self, keep_execution_id: str) -> int:
        """清空内存中除指定 execution 外的所有实例"""
```

**持久化路径**：`{project_path}/.claude/group_chats/{group_chat_id}/loop_executions.jsonl`

---

### 3. 修改 LoopManager

**文件**：`agents_hub/core/orchestration/loop_manager.py`

**修改点**：
1. `create_loop()` 移除 `initial_task` 参数
2. 移除状态管理相关方法（委托给 LoopExecutionManager）
3. Loop 定义可以长期保留在内存（不再需要单 Loop 保持）
4. 简化为纯"定义管理器"

**修改后的方法签名**：
```python
async def create_loop(
    self,
    nodes: list[dict],
    max_iterations: int,
) -> Loop:
    """创建循环定义（无 initial_task 参数）"""
    
def get_loop(self, loop_id: str) -> Loop:
    """查询 Loop 定义"""
    
async def delete_loop(self, loop_id: str) -> None:
    """删除 Loop 定义（同时删除关联的所有 executions）"""
```

---

### 4. 修改 LoopExecutor

**文件**：`agents_hub/core/orchestration/loop_executor.py`

**修改点**：
1. 构造函数接收 `loop: Loop` 和 `execution: LoopExecution`
2. 从 `execution.initial_task` 读取初始任务
3. 状态更新调用 `loop_execution_manager.update_execution_status()`
4. 不再直接修改 `loop` 对象的状态字段

**修改后的构造函数**：
```python
def __init__(
    self,
    loop: Loop,                      # Loop 定义
    execution: LoopExecution,        # 执行实例
    runtime: GroupChatRuntime | None = None,
    completion_queue: asyncio.Queue | None = None,
    send_message_callback: Callable[[AgentMessage], Awaitable[None]] | None = None,
    agent_call_manager=None,
    loop_execution_manager=None,     # 新增：执行管理器
    agents: dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
    node_result_timeout_seconds: float = 300.0,
):
    self.loop = loop
    self.execution = execution       # 新增
    self._last_node_output = execution.initial_task  # 从 execution 读取
    self._loop_execution_manager = loop_execution_manager  # 新增
```

**run() 方法修改**：
- 第 537 行：`self.loop.initial_task` → `self.execution.initial_task`
- 所有 `loop.status` → `execution.status`
- 所有 `loop.current_iteration` → `execution.current_iteration`
- 所有 `loop.current_node_index` → `execution.current_node_index`

**状态更新修改**：
- 所有调用 `self._loop_manager.update_loop_status()` 的地方
- 改为调用 `self._loop_execution_manager.update_execution_status()`

---

### 5. 修改 GroupChat

**文件**：`agents_hub/core/orchestration/group_chat.py`

**修改点**：
1. 新增 `loop_execution_manager` 实例
2. 修改 `create_loop()` 移除 `initial_task` 参数
3. 修改 `create_and_start_loop()` 添加 `initial_task` 参数
4. 启动时创建 `LoopExecution` 实例
5. 修改 `active_loops` 存储 execution_id 而非 loop_id
6. 修改 `stop_loop()` 和 `delete_loop()` 使用 execution_id

**修改后的方法签名**：
```python
async def create_loop(
    self,
    nodes: list[dict],
    max_iterations: int,
) -> Loop:
    """创建循环定义（移除 initial_task）"""
    
async def create_and_start_loop(
    self,
    loop_id: str,
    initial_task: str,  # 新增参数
) -> dict:
    """启动循环（添加 initial_task 参数）"""
    # 1. 获取 Loop 定义
    # 2. 创建 LoopExecution 实例
    # 3. 清空其他 execution（单 execution 保持）
    # 4. 设置 Agent 状态为 in_loop
    # 5. 创建 LoopExecutor 传入 loop 和 execution
    # 6. 启动后台任务
    
async def stop_loop(self, execution_id: str) -> dict:
    """停止循环（使用 execution_id）"""
    
async def delete_loop(self, loop_id: str) -> None:
    """删除 Loop 定义（同时删除所有 executions）"""
```

**内存管理调整**：
```python
self.active_loops: dict[str, LoopExecutor] = {}           # execution_id → executor
self._loop_tasks: dict[str, asyncio.Task] = {}            # execution_id → task
self._loop_queues: dict[str, asyncio.Queue] = {}          # execution_id → queue
```

---

### 6. 修改 MCP 工具接口

**文件**：`agents_hub/mcp/server.py`

**修改点**：

**create_loop**（第 1105 行）：
- 移除 `initial_task` 参数
- 返回 `{"loop_id": "...", "created_at": "..."}`

```python
async def create_loop(
    agent_token: str,
    nodes: list[dict],
    max_iterations: int,
    # 移除 initial_task 参数
) -> dict:
```

**start_loop**（第 1168 行）：
- 添加 `initial_task` 参数
- 返回 `{"execution_id": "...", "loop_id": "...", "status": "running"}`

```python
async def start_loop(
    agent_token: str, 
    loop_id: str,
    initial_task: str,  # 新增参数
) -> dict:
```

**stop_loop**（第 1206 行）：
- 参数改为 `execution_id`
- 返回 `{"execution_id": "...", "status": "paused"}`

```python
async def stop_loop(
    agent_token: str, 
    execution_id: str,  # 从 loop_id 改为 execution_id
) -> dict:
```

**get_loop_status**（第 1282 行）：
- 参数改为 `execution_id`
- 返回 execution 信息（包含 loop_id）

```python
async def get_loop_status(
    agent_token: str, 
    execution_id: str,  # 从 loop_id 改为 execution_id
) -> dict:
```

**新增 list_loop_executions**：
```python
async def list_loop_executions(
    agent_token: str,
    loop_id: str | None = None,  # 可选：过滤特定 Loop 的 executions
    status: str | None = None,
) -> dict:
    """查询执行历史"""
```

**保留 list_loops**（第 1323 行）：
- 查询 Loop 定义列表
- 返回每个 Loop 的 executions 统计

---

### 7. 更新异常体系

**文件**：`agents_hub/core/foundation/exceptions.py`

**新增异常**：
```python
class LoopExecutionNotFoundError(AgentsHubError):
    """执行实例不存在"""
    def __init__(self, execution_id: str):
        super().__init__(
            code="LOOP_EXECUTION_NOT_FOUND",
            message=f"Loop execution {execution_id} not found",
        )

class LoopExecutionStateError(AgentsHubError):
    """执行实例状态转换非法"""
    def __init__(self, execution_id: str, current: str, target: str):
        super().__init__(
            code="LOOP_EXECUTION_STATE_ERROR",
            message=f"Cannot transition execution {execution_id} from {current} to {target}",
        )
```

---

### 8. 更新渲染器

**文件**：`agents_hub/core/foundation/renderer.py`

**修改 render_for_chat()**：
- 循环消息格式从 `[循环-节点X-第N轮]` 改为 `[循环exec123-节点X-第N轮]`
- 添加 execution_id 标识，便于区分不同执行实例

---

### 9. 更新持久化路径工具

**文件**：`agents_hub/core/foundation/group_chat_paths.py`

**新增方法**：
```python
def loop_executions_data(self, group_chat_id: str, project_path: str) -> Path:
    """Loop 执行实例数据文件路径"""
    return self._group_chat_dir(group_chat_id, project_path) / "loop_executions.jsonl"
```

---

### 10. 更新测试

**需要修改的测试文件**：
1. `tests/core/orchestration/test_loop_manager.py` - 测试 Loop 定义 CRUD
2. `tests/core/orchestration/test_loop_executor.py` - 测试执行流程
3. `tests/core/orchestration/test_group_chat.py` - 测试 GroupChat Loop 方法
4. `tests/mcp/test_server.py` - 测试 MCP 工具接口

**新增测试文件**：
1. `tests/core/orchestration/test_loop_execution_manager.py` - 测试 LoopExecutionManager

**测试场景**：
- Loop 定义的创建、查询、删除
- 同一 Loop 多次启动，每次传入不同 initial_task
- LoopExecution 的生命周期管理
- 执行历史的查询和过滤
- 删除 Loop 定义时级联删除 executions
- 内存管理（单 execution 保持策略）

---

### 11. 更新文档

**需要更新的文档**：
1. `docs/specs/2026-06-21-loop.md` - Loop 规格定义
2. `docs/flows/loop-lifecycle.md` - Loop 生命周期数据流
3. `.scratch/loop-feature/PRD.md` - PRD 文档
4. `CONTEXT.md` - 新增 LoopExecution 术语

**主要修改点**：
- 数据模型拆分为 Loop 和 LoopExecution
- MCP 工具接口参数调整
- 状态机规则更新（Loop 无状态，LoopExecution 有状态）
- 内存管理策略调整
- 复用语义说明（同一 Loop 可多次启动）

---

## Verification Plan

### 1. 单元测试验证
```bash
# 运行 Loop 相关测试
pytest tests/core/orchestration/test_loop_manager.py -v
pytest tests/core/orchestration/test_loop_execution_manager.py -v
pytest tests/core/orchestration/test_loop_executor.py -v
pytest tests/mcp/test_server.py::test_loop_tools -v
```

### 2. 集成测试验证

**场景 1：创建 Loop 定义并多次启动**
```python
# 1. 创建 Loop 定义
response = await mcp.create_loop(
    agent_token=manager_token,
    nodes=[executor_node, reviewer_node],
    max_iterations=10,
)
loop_id = response["loop_id"]

# 2. 第一次启动
exec1 = await mcp.start_loop(
    agent_token=manager_token,
    loop_id=loop_id,
    initial_task="审查 user_service.py",
)
assert exec1["status"] == "running"

# 等待完成...

# 3. 第二次启动（复用同一 Loop 定义）
exec2 = await mcp.start_loop(
    agent_token=manager_token,
    loop_id=loop_id,
    initial_task="审查 payment_service.py",
)
assert exec2["execution_id"] != exec1["execution_id"]
assert exec2["loop_id"] == loop_id
```

**场景 2：查询执行历史**
```python
# 查询特定 Loop 的所有执行历史
executions = await mcp.list_loop_executions(
    agent_token=manager_token,
    loop_id=loop_id,
)
assert len(executions["executions"]) == 2
assert executions["executions"][0]["initial_task"] == "审查 user_service.py"
assert executions["executions"][1]["initial_task"] == "审查 payment_service.py"
```

**场景 3：停止和删除**
```python
# 停止执行实例
await mcp.stop_loop(agent_token=manager_token, execution_id=exec2["execution_id"])

# 删除 Loop 定义（级联删除所有 executions）
await mcp.delete_loop(agent_token=manager_token, loop_id=loop_id)

# 验证 executions 也被删除
executions = await mcp.list_loop_executions(agent_token=manager_token, loop_id=loop_id)
assert len(executions["executions"]) == 0
```

### 3. 手动测试

启动系统，通过 Manager 测试完整流程：
1. 创建一个 "代码审查" Loop 定义
2. 启动第一次执行，传入 "审查 auth.py"
3. 等待循环完成
4. 启动第二次执行，传入 "审查 api.py"
5. 查询执行历史，验证两次执行记录
6. 删除 Loop 定义

---

## Critical Files

**需要修改的核心文件**：
1. `agents_hub/core/context/loop_models.py` - 数据模型拆分
2. `agents_hub/core/orchestration/loop_execution_manager.py` - 新建执行管理器
3. `agents_hub/core/orchestration/loop_manager.py` - 简化为定义管理器
4. `agents_hub/core/orchestration/loop_executor.py` - 接收 execution 参数
5. `agents_hub/core/orchestration/group_chat.py` - 调整 Loop 方法
6. `agents_hub/mcp/server.py` - MCP 工具接口调整
7. `agents_hub/core/foundation/exceptions.py` - 新增异常
8. `agents_hub/core/foundation/renderer.py` - 渲染格式调整
9. `agents_hub/core/foundation/group_chat_paths.py` - 路径工具

**需要更新的文档**：
1. `docs/specs/2026-06-21-loop.md`
2. `docs/flows/loop-lifecycle.md`
3. `.scratch/loop-feature/PRD.md`
4. `CONTEXT.md`

---

## Migration Strategy

### 数据迁移

**兼容性处理**：
- 旧的 `loops.jsonl` 文件保留，不删除
- 新代码读取时识别旧格式，自动转换：
  - 旧 Loop 记录 → 拆分为 Loop 定义 + LoopExecution 实例
  - `initial_task` 迁移到 LoopExecution
  - 执行状态字段迁移到 LoopExecution

**迁移脚本**（可选）：
```python
# agents_hub/scripts/migrate_loops.py
async def migrate_loops_to_executions():
    """将旧的 loops.jsonl 拆分为 loops.jsonl 和 loop_executions.jsonl"""
```

### 向后兼容

**阶段 1：兼容读取**
- 保留旧 MCP 工具的参数签名，标记为 deprecated
- 新旧接口并存，给用户迁移时间

**阶段 2：废弃警告**
- 调用旧接口时返回警告信息
- 文档更新，引导用户使用新接口

**阶段 3：移除旧接口**
- 移除 deprecated 接口
- 只保留新接口

---

## Risk Analysis

### 高风险点
1. **数据模型变更**：Loop 和 LoopExecution 拆分后，序列化/反序列化逻辑复杂
2. **状态管理**：LoopExecutor 需要同时管理 Loop 和 LoopExecution 的引用
3. **内存管理**：单 execution 保持策略需要仔细测试
4. **MCP 工具接口变更**：影响所有调用方（Manager Agent）

### 缓解措施
1. **充分测试**：单元测试 + 集成测试覆盖所有场景
2. **渐进式重构**：先完成数据模型和管理器，再修改执行器和 MCP 接口
3. **向后兼容**：保留旧接口一段时间，给用户迁移时间
4. **文档先行**：先更新文档，确保设计对齐

---

## Implementation Order

1. **Phase 1：数据层**
   - 创建 LoopExecution 数据模型
   - 修改 Loop 数据模型
   - 创建 LoopExecutionManager
   - 更新异常体系

2. **Phase 2：业务层**
   - 修改 LoopManager（简化为定义管理器）
   - 修改 LoopExecutor（接收 execution 参数）
   - 修改 GroupChat Loop 方法

3. **Phase 3：接口层**
   - 修改 MCP 工具接口
   - 更新渲染器

4. **Phase 4：测试与文档**
   - 编写单元测试
   - 编写集成测试
   - 更新文档

5. **Phase 5：验证与迁移**
   - 手动测试完整流程
   - 数据迁移脚本（如需要）
   - 向后兼容处理
