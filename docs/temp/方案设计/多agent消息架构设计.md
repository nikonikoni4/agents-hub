# 多 Agent 消息架构设计方案

重要说明：该设计只是临时设计，不作为程序实现基础

## 设计日期
2026-05-28
claude session_id : 6ac09607-caa6-47f5-b5fd-00a02bd05996
"C:\Users\15535\.claude\projects\D--desktop------agents-hub\6ac09607-caa6-47f5-b5fd-00a02bd05996.jsonl"
## 设计目标

基于以下三个核心原则设计消息传递架构：

1. **避免越权访问**：Agent 不能直接访问其他 Agent 的方法和状态
2. **按需提供上下文**：每个 Agent 只获取与其职责相关的上下文信息
3. **点对点优于广播**：消息精确路由到目标 Agent，而非广播后过滤

---

## 核心组件

### 1. Message（消息）

**职责：**
- 承载消息内容和路由信息
- 关联任务 ID，用于异步任务追踪

**关键设计：**
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Message:
    content: str                                    # 消息内容
    send_to: str                                    # 接收者（路由目标）
    sent_from: str                                  # 发送者
    call_id: str | None = None                      # 关联的调用 ID（用于异步调用追踪）
    timestamp: datetime = field(default_factory=datetime.now)  # 消息时间戳
```

**@ 符号的双重语义：**

1. **User 的 @**：有路由作用
   - `User: "@Agent A 请分析需求"`
   - 系统解析后：`send_to = "Agent A"`
   - 消息直接路由到 Agent A（绕过 Manager）

2. **Agent 的 @**：无路由作用，用于上下文澄清
   - `Manager: "@Agent A 请分析需求"`
   - `send_to = "Agent A"`（路由）
   - 内容中的 `@Agent A` 是给其他 Agent 看的
   - 避免后续 Agent 误解任务对象

**为什么需要 Agent 的 @：**
- 场景：Manager 说"请分析需求"（没有 @）
- 问题：后续 Agent B 被触发时，可能误以为任务是给自己的
- 解决：Manager 说"@Agent A 请分析需求"
- 效果：Agent B 看到上下文时，知道这是给 Agent A 的任务

---

### 2. AgentCallManager（Agent 调用管理器）

**职责：**
- 统一管理所有跨 Agent 的异步调用
- 提供调用状态追踪和查询能力
- 维护调用生命周期（创建 → 执行 → 完成/失败/超时）
- 基于状态和时间自动清理过期调用

**命名说明：**
- `AgentCall`：表示一次 Agent 之间的消息调用（细粒度）
- 与业务层的 `Task`（用户级别的任务，如"开发登录功能"）区分开
- 一个业务 `Task` 可能包含多个 `AgentCall`

**关键设计：**
```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4

class CallStatus(Enum):
    PENDING = "pending"      # 已创建，等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    TIMEOUT = "timeout"      # 执行超时

class MessageType(Enum):
    TASK = "task"           # 需要回复的任务
    NOTIFICATION = "notification"  # 不需要回复的通知
    QUERY = "query"         # 查询请求

@dataclass
class AgentCall:
    call_id: str = field(default_factory=lambda: str(uuid4())[:8])  # 8 位短 ID
    send_from: str          # 调用发起者
    send_to: str            # 调用执行者
    content: str            # 调用内容
    message_type: MessageType = MessageType.TASK  # 消息类型
    status: CallStatus = CallStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: AgentResult | None = None  # 执行结果
    error: str | None = None           # 错误信息
    business_task_id: str | None = None  # 关联的业务任务 ID（可选）
    timeout_seconds: int = 300  # 超时时间（默认 5 分钟）
    
    def is_timeout(self) -> bool:
        """判断是否超时"""
        if self.status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT):
            return False
        
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds
    
    def can_be_deleted(self) -> bool:
        """判断是否可以被删除"""
        now = datetime.now()
        
        # 1. NOTIFICATION 类型：完成后立即可删除
        if self.message_type == MessageType.NOTIFICATION:
            return self.status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT)
        
        # 2. TASK 类型：需要保留一段时间供查询
        if self.status == CallStatus.COMPLETED:
            # 完成后保留 60 秒（给发起者查询的时间）
            if self.completed_at:
                elapsed = (now - self.completed_at).total_seconds()
                return elapsed > 60
        
        if self.status == CallStatus.FAILED:
            # 失败后保留 300 秒（5 分钟，便于调试）
            if self.completed_at:
                elapsed = (now - self.completed_at).total_seconds()
                return elapsed > 300
        
        if self.status == CallStatus.TIMEOUT:
            # 超时后保留 300 秒（5 分钟，便于调试）
            if self.completed_at:
                elapsed = (now - self.completed_at).total_seconds()
                return elapsed > 300
        
        # 3. PENDING/RUNNING 状态：不能删除
        return False

class AgentCallManager:
    """统一管理所有跨 Agent 的异步调用"""
    
    def __init__(self, log_dir: Path = Path("local_data/logs")):
        self._calls: dict[str, AgentCall] = {}  # call_id -> AgentCall
        self._lock = threading.Lock()  # 线程安全
        
        # 导入 logger
        from lifeprism.utils.logger import setup_agent_call_logging
        self._logger = setup_agent_call_logging(log_dir)
        
        # 启动后台清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def create_call(
        self, 
        send_from: str, 
        send_to: str, 
        content: str,
        message_type: MessageType = MessageType.TASK,
        business_task_id: str | None = None,
        timeout_seconds: int = 300
    ) -> str:
        """创建新调用，返回 call_id"""
        call = AgentCall(
            send_from=send_from, 
            send_to=send_to, 
            content=content,
            message_type=message_type,
            business_task_id=business_task_id,
            timeout_seconds=timeout_seconds
        )
        
        with self._lock:
            # 极小概率冲突检查（8 位 UUID 在 100 个缓存下冲突概率 0.00012%）
            while call.call_id in self._calls:
                call.call_id = str(uuid4())[:8]
            
            self._calls[call.call_id] = call
        
        # 记录创建事件
        self._log_call(call)
        
        return call.call_id
    
    def get_call(self, call_id: str) -> AgentCall | None:
        """获取调用详情（先查缓存，再查日志）"""
        # 1. 先查内存缓存
        with self._lock:
            if call := self._calls.get(call_id):
                return call
        
        # 2. 再查日志文件
        return self._search_call_in_log(call_id)
    
    def update_status(self, call_id: str, status: CallStatus):
        """更新调用状态"""
        with self._lock:
            if call := self._calls.get(call_id):
                call.status = status
                if status == CallStatus.RUNNING:
                    call.started_at = datetime.now()
                elif status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT):
                    call.completed_at = datetime.now()
                
                # 记录状态变更
                self._log_call(call)
    
    def set_result(self, call_id: str, result: AgentResult):
        """设置调用结果"""
        with self._lock:
            if call := self._calls.get(call_id):
                call.result = result
                call.status = CallStatus.COMPLETED
                call.completed_at = datetime.now()
                
                # 记录完成事件
                self._log_call(call)
    
    def set_error(self, call_id: str, error: str):
        """设置调用错误"""
        with self._lock:
            if call := self._calls.get(call_id):
                call.error = error
                call.status = CallStatus.FAILED
                call.completed_at = datetime.now()
                
                # 记录失败事件
                self._log_call(call)
    
    def _cleanup_loop(self):
        """后台清理线程：定期检查并删除可删除的调用"""
        while True:
            try:
                time.sleep(30)  # 每 30 秒清理一次
                self._cleanup_expired_calls()
                self._check_timeouts()
            except Exception as e:
                self._logger.error(f"清理线程异常: {e}")
    
    def _cleanup_expired_calls(self):
        """清理可删除的调用"""
        with self._lock:
            to_delete = [
                call_id for call_id, call in self._calls.items()
                if call.can_be_deleted()
            ]
            
            for call_id in to_delete:
                del self._calls[call_id]
            
            if to_delete:
                self._logger.info(f"清理了 {len(to_delete)} 个过期调用")
    
    def _check_timeouts(self):
        """检查超时的调用"""
        with self._lock:
            for call in self._calls.values():
                if call.is_timeout() and call.status in (CallStatus.PENDING, CallStatus.RUNNING):
                    call.status = CallStatus.TIMEOUT
                    call.completed_at = datetime.now()
                    
                    # 记录超时事件
                    self._log_call(call)
                    
                    self._logger.warning(
                        f"调用超时: {call.call_id} ({call.send_from} -> {call.send_to})"
                    )
    
    def _log_call(self, call: AgentCall):
        """记录调用到专用日志文件"""
        log_entry = {
            "call_id": call.call_id,
            "send_from": call.send_from,
            "send_to": call.send_to,
            "content": call.content,
            "message_type": call.message_type.value,
            "status": call.status.value,
            "created_at": call.created_at.isoformat(),
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "completed_at": call.completed_at.isoformat() if call.completed_at else None,
            "result": call.result.text if call.result else None,
            "error": call.error,
            "business_task_id": call.business_task_id,
            "timeout_seconds": call.timeout_seconds
        }
        # 直接输出 JSON 字符串到日志
        self._logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def _search_call_in_log(self, call_id: str) -> AgentCall | None:
        """从日志文件中搜索历史调用"""
        log_file = Path("local_data/logs/agent_calls.jsonl")
        
        if not log_file.exists():
            return None
        
        try:
            # 从后往前读（最新的调用在文件末尾）
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 倒序查找
            for line in reversed(lines):
                try:
                    entry = json.loads(line.strip())
                    if entry.get('call_id') == call_id:
                        # 重建 AgentCall 对象（只读）
                        return self._rebuild_call_from_log(entry)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            self._logger.error(f"搜索日志失败: {e}")
        
        return None
    
    def get_stats(self) -> dict:
        """获取统计信息（用于调试）"""
        with self._lock:
            stats = {
                "total": len(self._calls),
                "pending": sum(1 for c in self._calls.values() if c.status == CallStatus.PENDING),
                "running": sum(1 for c in self._calls.values() if c.status == CallStatus.RUNNING),
                "completed": sum(1 for c in self._calls.values() if c.status == CallStatus.COMPLETED),
                "failed": sum(1 for c in self._calls.values() if c.status == CallStatus.FAILED),
                "timeout": sum(1 for c in self._calls.values() if c.status == CallStatus.TIMEOUT),
            }
            return stats
```

**设计要点：**
- 所有调用都在 `AgentCallManager` 中注册，避免调用分散在各个 Agent 的队列中
- 每个调用都有唯一的 `call_id`（8 位 UUID 截断），短小精悍
- 支持查询调用状态、执行时长、结果等信息
- `_calls` 字典就是异步调用的 "pending 池"
- 可选的 `business_task_id` 字段用于关联业务层任务
- **生命周期管理**：基于状态和时间自动清理，而非简单的 LRU
- **超时机制**：后台线程定期检查，超时调用自动标记为 TIMEOUT
- **日志持久化**：所有状态变更都记录到 `agent_calls.jsonl`，内存删除后仍可查询

**生命周期规则：**

| 状态 | MessageType | 删除条件 | 保留时间 | 说明 |
|------|-------------|---------|---------|------|
| PENDING | 任意 | ❌ 不删除 | - | 等待执行，不能删除 |
| RUNNING | 任意 | ❌ 不删除 | - | 正在执行，不能删除 |
| COMPLETED | TASK | ✅ 完成后 60 秒 | 60 秒 | 给发起者查询的时间 |
| COMPLETED | NOTIFICATION | ✅ 立即删除 | 0 秒 | 不需要回复，立即清理 |
| FAILED | 任意 | ✅ 失败后 300 秒 | 5 分钟 | 便于调试 |
| TIMEOUT | 任意 | ✅ 超时后 300 秒 | 5 分钟 | 便于调试 |

**call_id 生成策略：**
- 使用 UUID4 截断前 8 位（十六进制）
- 在 100 个缓存下冲突概率约 0.00012%
- 使用 `while` 循环处理极小概率的连续冲突
- 短小精悍，易读易用，便于日志查看

---

### 3. MessageRouter（消息总线）

**职责：**
- 管理所有 Agent 的私有队列引用
- 负责点对点消息路由
- 记录所有消息到 GroupChatSession

**关键设计：**
```python
class MessageRouter:
    def __init__(self, context: GroupChatContext):
        self._agent_buffers: dict[str, asyncio.Queue] = {}  # 实例变量：Agent 名称 → 私有队列
        self._context = context                              # 实例变量：群聊上下文引用
    
    def register(self, agent_name: str, buffer: asyncio.Queue):
        """注册 Agent 的私有队列"""
        self._agent_buffers[agent_name] = buffer
    
    def publish_message(self, msg: Message):
        """点对点路由 + 记录历史"""
        # 1. 记录到 GroupChatSession
        self._context.group_chat_session.add_message(
            sender=msg.sent_from,
            content=msg.content,
            send_to=msg.send_to
        )
        # 2. 路由到目标 Agent 的私有队列
        target_buffer = self._agent_buffers.get(msg.send_to)
        if target_buffer:
            target_buffer.put_nowait(msg)
```

**为什么不用中心化暂存队列：**
- 私有队列已经提供异步解耦
- 中心化队列只是多一层中转，无实际价值
- 直接路由更简单高效

---

### 4. Agent（智能体）

**职责：**
- 持有私有消息队列（`asyncio.Queue`）
- 持有 MessageRouter 引用（用于发送消息）
- 持有 GroupChatContext 引用（用于读取上下文）
- 从队列接收消息并处理
- 更新调用状态到 AgentCallManager

**关键设计：**
```python
class Agent:
    def __init__(self, name: str, message_router: MessageRouter, context: GroupChatContext):
        self.name = name                        # 实例变量：每个 Agent 独立
        self.message_buffer = asyncio.Queue()   # 实例变量：每个 Agent 独立的私有队列
        self.context = context                  # 实例变量：持有 GroupChatContext 引用
        self._bus = message_router              # 实例变量：持有 MessageRouter 引用（共享同一实例）
        
        # 注册自己的队列到 MessageRouter
        self._bus.register(self.name, self.message_buffer)
    
    def send_message(self, content: str, send_to: str):
        """发送消息：Agent 不知道目标在哪，只知道名字"""
        msg = Message(content, send_to, sent_from=self.name)
        self._bus.publish_message(msg)
    
    async def run(self):
        """主循环：从队列取消息并处理"""
        while True:
            msg = await self.message_buffer.get()  # 阻塞等待
            await self._process_message(msg)
    
    async def _process_message(self, msg: Message):
        """处理消息，并更新调用状态"""
        call_id = msg.call_id
        
        try:
            # 1. 标记调用为 RUNNING
            if call_id:
                self.context.agent_call_manager.update_status(call_id, CallStatus.RUNNING)
            
            # 2. 从 GroupChatContext 获取上下文
            agent_context = self.context.get_agent_context(self.name)
            
            # 3. 组装 prompt 并执行 LLM 调用
            prompt = f"{agent_context}\n\n新消息：{msg.content}"
            result = await self.execute(prompt)
            
            # 4. 写入群聊历史
            self.context.group_chat_session.add_message(result)
            self.context.save_group_chat_session()
            
            # 5. 更新 session_id
            self.context.update_agent_member_info(result)
            self.context.save_agent_member_info()
            
            # 6. 标记调用为 COMPLETED
            if call_id:
                self.context.agent_call_manager.set_result(call_id, result)
            
            # 7. 发送回复消息（可选，根据消息类型决定）
            # self.send_message(result.text, msg.sent_from)
            
        except Exception as e:
            # 8. 标记调用为 FAILED
            if call_id:
                self.context.agent_call_manager.set_error(call_id, str(e))
            raise
```

**为什么 Agent 持有 GroupChatContext：**
- 这不是"耦合"，这是"依赖注入"
- Agent 需要读取上下文来执行任务
- Agent 只读取，不修改其他 Agent 的状态
- 类比：Agent 依赖 RoleConfig 一样合理

**群聊消息写入时机：**
- 在 `_process_message()` 中，LLM 返回后立即写入
- 确保每次 Agent 的回复都被记录到群聊历史
- 写入时机：LLM 返回后、发送下一条消息前

---

### 5. GroupChatContext（群聊上下文）

**职责：**
- 管理群聊历史消息（`GroupChatSession`）
- 管理压缩历史（`compact_history.jsonl`）
- 管理 Agent 调用状态（`AgentCallManager`）
- 为每个 Agent 提供定制化上下文

**关键设计：**
```python
class GroupChatContext:
    group_chat_session: GroupChatSession    # 原始消息历史
    compact_history_file: str               # 压缩历史文件路径
    agent_call_manager: AgentCallManager    # Agent 调用管理器
    
    def get_agent_context(agent_name) -> str:
        """获取该 Agent 的上下文（已实现）"""
        # 1. 压缩历史的 summary（全局）
        # 2. 压缩历史中针对该 Agent 的部分
        # 3. 最新未压缩消息（过滤后）
```

**上下文过滤规则（已在 team.py 实现）：**
- Agent 只看到与自己相关的消息
- 避免被无关信息干扰
- 减少 token 消耗

---

## Agent 调用管理架构

### 设计目标

解决以下问题：
1. **调用分散问题**：调用不再分散在各个 Agent 的队列中，而是统一在 AgentCallManager 中管理
2. **状态追踪问题**：通过 call_id 可以查询调用的执行状态、进度、结果
3. **异步执行问题**：`call_agent` 立即返回 call_id，不阻塞调用者

### 完整调用链路

```
A 调用 call_agent(B, "分析需求")
    ↓
1. AgentCallManager.create_call() → 返回 call_id
    ↓
2. MessageRouter.publish_message(msg with call_id)
    ↓
3. 投递到 B.message_buffer
    ↓
4. 立即返回 "调用已派遣，call_id: xxx"
    ↓
（A 可以继续做其他事情，不阻塞）
    ↓
5. B.run() 从队列取出消息
    ↓
6. B._process_message()
   - 标记调用为 RUNNING
   - 执行 LLM 调用
   - 写入群聊历史
   - 标记调用为 COMPLETED
    ↓
7. A 调用 query_call_status(call_id) 查询结果
```

### 工具接口设计

#### 1. call_agent（派遣调用）

```python
def call_agent(
    send_from: str, 
    send_to: str, 
    content: str, 
    group_chat: GroupChat,
    business_task_id: str | None = None
) -> str:
    """
    派遣调用给目标 Agent（异步执行）
    
    Args:
        send_from: 发送者名称
        send_to: 接收者名称
        content: 调用内容
        group_chat: 群聊实例
        business_task_id: 可选的业务任务 ID，用于关联业务层任务
    
    Returns:
        "调用已派遣，call_id: xxx"
    """
    # 1. 创建调用记录
    call_id = group_chat.agent_call_manager.create_call(
        send_from, send_to, content, business_task_id
    )
    
    # 2. 发送消息到目标 Agent
    message = AgentsMessage(
        content=content,
        send_from=send_from,
        send_to=send_to,
        call_id=call_id
    )
    group_chat.message_router._agents_queue[send_to].put_nowait(message)
    
    return f"调用已派遣，call_id: {call_id}"
```

**设计要点：**
- 立即返回 call_id，不等待执行完成
- 真正的异步，调用者不阻塞
- 调用状态由 AgentCallManager 统一管理
- 可选的 business_task_id 用于关联业务层任务

#### 2. query_call_status（查询调用状态）

```python
def query_call_status(call_id: str, group_chat: GroupChat) -> str:
    """
    查询调用执行状态
    
    Args:
        call_id: 调用 ID
        group_chat: 群聊实例
    
    Returns:
        调用状态的 JSON 字符串
    """
    call = group_chat.agent_call_manager.get_call(call_id)
    
    if not call:
        return f"调用不存在: {call_id}"
    
    # 构建返回信息
    info = {
        "call_id": call.call_id,
        "status": call.status.value,
        "send_from": call.send_from,
        "send_to": call.send_to,
        "content": call.content[:50] + "...",
        "created_at": call.created_at.isoformat(),
    }
    
    if call.business_task_id:
        info["business_task_id"] = call.business_task_id
    
    if call.status == CallStatus.COMPLETED and call.result:
        info["result"] = call.result.text[:200] + "..."
        info["duration"] = (call.completed_at - call.created_at).total_seconds()
    
    if call.status == CallStatus.FAILED and call.error:
        info["error"] = call.error
    
    return json.dumps(info, ensure_ascii=False, indent=2)
```

**设计要点：**
- 返回调用的完整状态信息
- 包括执行时长、结果摘要、错误信息
- 支持 LLM 解析 JSON 格式
- 包含关联的业务任务 ID（如果有）

### 使用示例

```python
# 场景：Manager 派遣调用给 Agent A

# 1. Manager 调用 call_agent
result = call_agent("Manager", "Agent A", "请分析需求", group_chat)
# 返回: "调用已派遣，call_id: 123e4567-e89b-12d3-a456-426614174000"

# 2. 提取 call_id
call_id = "123e4567-e89b-12d3-a456-426614174000"

# 3. Manager 继续做其他事情（不阻塞）
# ...

# 4. 稍后查询调用状态
status = query_call_status(call_id, group_chat)
# 返回:
# {
#   "call_id": "123e4567-e89b-12d3-a456-426614174000",
#   "status": "running",
#   "send_from": "Manager",
#   "send_to": "Agent A",
#   "content": "请分析需求",
#   "created_at": "2026-05-29T10:30:00"
# }

# 5. 调用完成后再次查询
status = query_call_status(call_id, group_chat)
# 返回:
# {
#   "call_id": "123e4567-e89b-12d3-a456-426614174000",
#   "status": "completed",
#   "send_from": "Manager",
#   "send_to": "Agent A",
#   "content": "请分析需求",
#   "created_at": "2026-05-29T10:30:00",
#   "result": "需求分析完成：用户需要一个登录功能...",
#   "duration": 40.0
# }
```

### 调用完成后的通知机制

**问题：B 完成调用后，是否自动通知 A？**

**方案：引入消息类型，避免无限循环**

```python
class MessageType(Enum):
    TASK = "task"           # 任务派遣，需要执行并回复
    NOTIFICATION = "notification"  # 通知消息，不需要回复
    QUERY = "query"         # 查询请求，需要回复

@dataclass
class AgentsMessage:
    content: str
    send_from: str
    send_to: str
    call_id: str | None = None
    message_type: MessageType = MessageType.TASK  # 默认是任务
    session_type: SessionType = SessionType.MAIN
    timestamp: datetime = field(default_factory=datetime.now)
```

**使用场景：**

1. **A 派遣调用给 B**：
   ```python
   call_agent(A, B, "请分析需求", message_type=MessageType.TASK)
   # B 执行完成后，发送 NOTIFICATION 给 A
   send_message(B, A, "调用完成：需求分析结果...", message_type=MessageType.NOTIFICATION)
   ```

2. **A 收到 NOTIFICATION**：
   ```python
   async def _process_message(self, msg: AgentsMessage):
       result = await self.execute(msg.content)
       
       # 只有 TASK 类型才需要回复
       if msg.message_type == MessageType.TASK:
           self.send_message(msg.send_from, result.text, MessageType.NOTIFICATION)
   ```

**这样就避免了循环：**
- A → B (TASK)
- B 执行 → A (NOTIFICATION)
- A 收到 NOTIFICATION，不回复 ✅

**注意：**
- 当前设计中，B 完成调用后**不会自动通知 A**
- A 需要主动调用 `query_call_status` 查询结果
- 如果需要自动通知，可以在 `_process_message` 中添加逻辑：
  ```python
  # 调用完成后，发送 NOTIFICATION 给发起者
  if call_id and msg.message_type == MessageType.TASK:
      self.send_message(
          msg.send_from, 
          f"调用 {call_id} 已完成：{result.text[:100]}...",
          MessageType.NOTIFICATION
      )
  ```

---

## 消息流转完整链路

### 基本流程（带调用管理）

```
发送者调用 call_agent(send_to, content)
    ↓
1. AgentCallManager.create_call() → 返回 call_id
    ↓
2. MessageRouter.publish_message(msg with call_id)
    ↓
3. 记录到 GroupChatSession
4. 路由到目标 Agent 的 message_buffer
    ↓
5. 立即返回 "调用已派遣，call_id: xxx"（不阻塞）
    ↓
目标 Agent.message_buffer.get()
    ↓
目标 Agent._process_message(msg)
    ↓
1. 标记调用为 RUNNING
2. 从 GroupChatContext 获取上下文
3. 组装 prompt
4. 执行 LLM 调用
5. 写入群聊历史
6. 更新 session_id
7. 标记调用为 COMPLETED
8. （可选）发送 NOTIFICATION 给发起者
```

### 关键点

1. **异步解耦**：
   - 发送者调用 `call_agent()` 立即返回 call_id
   - 接收者从队列阻塞等待（`await queue.get()`）
   - 发送者不等待接收者处理，可以继续做其他事情

2. **调用追踪**：
   - 所有调用都在 `AgentCallManager` 中注册
   - 通过 `call_id` 可以查询调用状态、进度、结果
   - 支持 PENDING → RUNNING → COMPLETED/FAILED 状态流转

3. **FIFO 保证**：
   - `asyncio.Queue` 保证消息按顺序处理
   - Manager 连续发送 3 个调用，Agent 按顺序执行

4. **消息记录**：
   - 所有消息都记录到 `GroupChatSession`
   - 包括 User 消息、Manager 调用、Agent 结果
   - 便于调试和信息公开

5. **群聊消息写入时机**：
   - 在 `Agent._process_message()` 中，LLM 返回后立即写入
   - 确保每次 Agent 的回复都被记录到群聊历史
   - 写入时机：LLM 返回后、发送下一条消息前

---

## 三种使用场景

### 场景 1：Workflow（顺序执行）

**特点：**
- 执行顺序确定（User 明确告知）
- Manager 维护 workflow 状态机
- 按顺序调度 Agent

**流程：**
```
User: "请按照 A→B→C 顺序开发登录功能"
    ↓
Manager 解析：workflow = ["Agent A", "Agent B", "Agent C"]
    ↓
Manager → Agent A: "@Agent A 请分析需求"
    ↓
Agent A 完成 → Manager: "@Manager 任务完成"
    ↓
Manager → Agent B: "@Agent B 请开始设计"
    ↓
Agent B 完成 → Manager: "@Manager 任务完成"
    ↓
Manager → Agent C: "@Agent C 请开始编码"
    ↓
...
```

**Manager 实现要点：**
- 维护 `workflow` 列表和 `current_step` 索引
- 收到 Agent 回复后，`current_step += 1`
- 继续发送给下一个 Agent

---

### 场景 2：Manager-SubAgent（动态协调）

**特点：**
- 执行顺序不确定
- Manager 通过 LLM 动态决策下一步
- 灵活应对复杂任务

**流程：**
```
User: "帮我开发登录功能"
    ↓
Manager LLM 决策：需要先分析需求 → 调用 Agent A
    ↓
Manager → Agent A: "@Agent A 请分析需求"
    ↓
Agent A 完成 → Manager: "@Manager 需求分析完成"
    ↓
Manager LLM 决策：需要设计架构 → 调用 Agent B
    ↓
Manager → Agent B: "@Agent B 请设计架构"
    ↓
...
```

**Manager 实现要点：**
- 每次收到消息后，调用 LLM 决策
- LLM 输出：调用哪个 Agent + 给他什么任务
- 动态调整执行流程

**注意：**
- Manager 的决策逻辑超出消息设计范围
- 需要防止死循环（最大轮数限制）

---

### 场景 3：User 直接 @Agent

**特点：**
- User 绕过 Manager，直接与 Agent 对话
- Manager 通过 GroupChatSession 仍能看到对话

**流程：**
```
User: "@Agent A 请分析这个需求"
    ↓
系统解析 @Agent A
    ↓
匹配成功 → 直接路由到 Agent A
匹配失败 → 降级到 Manager
    ↓
Agent A 处理 → 回复 User
    ↓
消息记录到 GroupChatSession
    ↓
Manager 下次被触发时，能看到这段对话
```

**实现要点：**
- 外部系统（UI 层）解析 User 输入的 `@`
- 提取目标 Agent 名称
- 调用 `message_bus.publish_message()` 直接路由
- 所有消息都记录到 `GroupChatSession`，Manager 不会丢失上下文

---

## 关键设计决策

### 决策 1：为什么不用 MetaGPT 的双向引用？

**MetaGPT 方式：**
```python
Agent.rc.env → Environment
Environment.roles[name] → Agent
```

**问题：**
- Agent 能通过 `self.rc.env.roles[name]` 访问其他 Agent
- Agent 理论上能调用其他 Agent 的任何方法
- 程序上容易出错，存在越权风险

**我们的方式：**
```python
Agent._bus → MessageRouter
MessageRouter._agent_buffers[name] → Queue（私有变量）
```

**优点：**
- Agent 只能调用 `_bus.publish_message()`
- Agent 无法访问 `_agent_buffers`（私有变量）
- 完全避免越权

---

### 决策 2：为什么不用 AutoGen 的公共 Buffer？

**AutoGen 方式：**
```python
GroupChat.message_buffer = []  # 公共 buffer
Agent 主动过滤：for msg in buffer if msg.send_to == self.name
```

**问题：**
- 所有 Agent 都能看到所有消息
- 依赖 Agent "自觉"不偷看其他消息
- 不符合"按需提供上下文"原则

**我们的方式：**
```python
每个 Agent 有私有队列
MessageRouter 精确路由到目标队列
```

**优点：**
- Agent 的队列里只有发给自己的消息
- 不需要过滤，不会看到无关消息
- 真正的点对点路由

---

### 决策 3：为什么不用中心化暂存队列？

**中心化队列方式：**
```python
MessageRouter._central_queue = asyncio.Queue()
后台任务：从 central_queue 取消息 → 路由到私有队列
```

**问题：**
- 多了一层中转，增加延迟
- 需要后台任务维护
- 增加复杂度，无实际价值

**我们的方式：**
```python
MessageRouter.publish_message() 直接路由到私有队列
```

**优点：**
- 简单直接，无额外延迟
- 私有队列已经提供异步解耦
- 不需要后台任务

---

## 与现有代码的集成

### 已实现的部分（team.py）

1. **GroupChatContext**：
   - `get_agent_context(agent_name)`：获取定制化上下文
   - `compact_messages(agent_info)`：压缩历史消息
   - `load_compact_history()`：加载压缩历史

2. **GroupChatSession**：
   - `add_message(agent_result)`：记录消息
   - `get_uncompact_messages()`：获取未压缩消息

3. **Agent 基础结构**：
   - `Agent.message_buffer`：私有队列（已定义）
   - `Agent.execute()`：LLM 调用接口

4. **MessageRouter 基础**：
   - 已实现 `register()` 和 `send_message()`
   - 需要扩展以支持任务管理

### 需要新增的部分

1. **AgentCallManager 类**：
   - 实现 `AgentCall` 和 `CallStatus` 数据结构
   - 实现 `create_call()`、`get_call()`、`update_status()`、`set_result()`、`set_error()`
   - 集成到 `GroupChatContext` 中

2. **Message 数据类扩展**：
   - 添加 `call_id` 字段
   - 添加 `message_type` 字段（可选，用于避免循环回复）

3. **Agent 消息处理逻辑扩展**：
   - 修改 `_process_message()`，添加调用状态更新逻辑
   - 添加群聊消息写入逻辑
   - 添加 session_id 更新逻辑

4. **call_agent 工具扩展**：
   - 修改为先创建调用，再发送消息
   - 返回 call_id 而不是简单的成功消息
   - 支持可选的 business_task_id 参数

5. **query_call_status 工具**：
   - 新增工具，用于查询调用状态
   - 返回 JSON 格式的调用详情

6. **GroupChat 类扩展**：
   - 添加 `agent_call_manager` 成员变量
   - 在初始化时创建 `AgentCallManager` 实例

---

## 实现优先级

### P0（核心功能）

1. 实现 `AgentCallManager` 类和相关数据结构
2. 实现 `AgentCall` 和 `CallStatus` 枚举（包含 TIMEOUT 状态）
3. 实现 `MessageType` 枚举（TASK / NOTIFICATION / QUERY）
4. 修改 `AgentsMessage`：添加 `call_id` 和 `message_type` 字段
5. 修改 `Agent._process_message()`：
   - 添加调用状态更新逻辑
   - 添加群聊消息写入逻辑
   - 添加 session_id 更新逻辑
6. 修改 `call_agent()`：集成调用创建和 call_id 返回，支持 message_type 和 timeout_seconds 参数
7. 实现 `query_call_status()` 工具
8. 修改 `GroupChat.__init__()`：添加 `AgentCallManager` 初始化
9. 在 `logger.py` 中添加 `setup_agent_call_logging()` 函数
10. 实现后台清理线程和超时检查机制

### P1（场景支持）

1. 修改 `Agent._process_message()`：根据 `message_type` 决定是否回复
2. 实现 `Manager` 类的 workflow 调度逻辑
3. 实现 User `@Agent` 的解析和路由
4. 实现调用完成后的自动通知机制（可选）

### P2（优化）

1. 添加消息路由日志
2. 添加错误处理（目标 Agent 不存在）
3. 添加调用取消功能
4. 优化日志搜索性能（索引、缓存等）
5. 添加调用统计和监控（get_stats 扩展）

---

## Logger 集成方案

### 在 logger.py 中添加专用函数

```python
# 在 lifeprism/utils/logger.py 末尾添加

def setup_agent_call_logging(log_dir: Path) -> logging.Logger:
    """
    为 AgentCall 创建独立的 logger，输出到单独的文件
    
    Args:
        log_dir: 日志目录路径（如 local_data/logs）
    
    Returns:
        配置好的 agent_call logger
    """
    logger_name = "agent_call"
    logger = logging.getLogger(logger_name)
    
    # 防止重复添加 handler
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(logging.INFO)
    
    # 不继承 root logger 的 handlers（这样就不会输出到 lifeprism.log）
    logger.propagate = False
    
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'agent_calls.jsonl'
        
        # 使用追加模式，不清空旧日志
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        
        # 使用简单格式，只输出消息内容（因为我们会记录 JSON）
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        
        logger.addHandler(file_handler)
        
    except Exception as e:
        print(f"[WARNING] 无法创建 agent_call 日志文件: {e}")
    
    return logger
```

### 日志文件结构

**local_data/logs/lifeprism.log**（通用日志）：
```
2026-05-29 10:30:00 INFO team.py func:start line 252 : 初始化群聊
2026-05-29 10:30:01 INFO agent.py func:execute line 740 : Manager 执行任务
```

**local_data/logs/agent_calls.jsonl**（AgentCall 专用日志）：
```json
{"call_id": "a3f5b2c1", "send_from": "Manager", "send_to": "Agent A", "content": "分析需求", "message_type": "task", "status": "pending", "created_at": "2026-05-29T10:30:00", ...}
{"call_id": "a3f5b2c1", "send_from": "Manager", "send_to": "Agent A", "content": "分析需求", "message_type": "task", "status": "completed", "created_at": "2026-05-29T10:30:00", "completed_at": "2026-05-29T10:30:45", "result": "需求分析完成...", ...}
```

**关键点：**
- `logger.propagate = False` 确保不会输出到 root logger（lifeprism.log）
- 使用独立的文件 handler
- JSONL 格式：每行一个 JSON 对象，便于解析和搜索
- 支持追加写入，记录完整的调用生命周期

---

## 业务层任务管理（未来扩展）

### 与 AgentCall 的区别

当前的 `AgentCall` 是**消息层面**的调用追踪，粒度较细。未来需要实现**业务层面**的任务管理，用于前端可视化展示。

| 维度 | AgentCall（消息层） | Task（业务层） |
|------|---------------------|----------------|
| **含义** | 一次跨 Agent 的消息调用 | 用户请求的业务功能 |
| **粒度** | 细粒度（一次 LLM 调用） | 粗粒度（多次 Agent 协作） |
| **生命周期** | A 调用 B → B 执行 → 返回结果 | 创建 → 分解子任务 → 多 Agent 协作 → 完成 |
| **用途** | 追踪异步消息的执行状态 | 前端可视化展示任务进度 |
| **示例** | "Manager 调用 Agent A 分析需求" | "开发登录功能"（包含需求分析、设计、编码、测试） |

### 业务层任务架构（待实现）

```python
class TaskStatus(Enum):
    TODO = "todo"               # 待开始
    IN_PROGRESS = "in_progress" # 进行中
    DONE = "done"               # 已完成
    BLOCKED = "blocked"         # 被阻塞

@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    title: str                  # 任务标题（如"开发登录功能"）
    description: str            # 任务描述
    status: TaskStatus = TaskStatus.TODO
    subtasks: list[str] = field(default_factory=list)  # 子任务 ID 列表
    agent_calls: list[str] = field(default_factory=list)  # 关联的 AgentCall ID 列表
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    progress: float = 0.0       # 进度百分比（0-100）

class TaskManager:
    """管理业务层任务"""
    
    def __init__(self):
        self._tasks: dict[str, Task] = {}
    
    def create_task(self, title: str, description: str) -> str:
        """创建业务任务"""
        task = Task(title=title, description=description)
        self._tasks[task.task_id] = task
        return task.task_id
    
    def add_subtask(self, task_id: str, subtask_title: str) -> str:
        """为任务添加子任务"""
        subtask_id = self.create_task(subtask_title, "")
        if task := self._tasks.get(task_id):
            task.subtasks.append(subtask_id)
        return subtask_id
    
    def link_agent_call(self, task_id: str, call_id: str):
        """关联 AgentCall 到任务"""
        if task := self._tasks.get(task_id):
            task.agent_calls.append(call_id)
    
    def update_progress(self, task_id: str):
        """根据子任务完成情况更新进度"""
        if task := self._tasks.get(task_id):
            if not task.subtasks:
                return
            completed = sum(
                1 for subtask_id in task.subtasks
                if self._tasks.get(subtask_id, Task()).status == TaskStatus.DONE
            )
            task.progress = (completed / len(task.subtasks)) * 100
```

### 两层架构的关系

```
用户请求："增加登录功能"
    ↓
TaskManager.create_task() → Task(id=1, title="增加登录功能")
    ↓
Manager 分解任务：
    - Subtask 1: 需求分析
    - Subtask 2: 设计架构
    - Subtask 3: 编码实现
    - Subtask 4: 编写测试
    ↓
执行 Subtask 1：
    Manager 调用 call_agent(Agent A, "分析需求", business_task_id=1)
        ↓
    AgentCallManager.create_call() → AgentCall(call_id=abc, business_task_id=1)
        ↓
    Agent A 执行 → 更新 CallStatus.COMPLETED
        ↓
    TaskManager.update_subtask(1, "需求分析", DONE)
    TaskManager.update_progress(1)  # 更新主任务进度
    ↓
执行 Subtask 2、3、4...
    ↓
所有 Subtask 完成 → TaskManager.update_task(1, DONE)
    ↓
前端显示："登录功能开发完成 ✅ (100%)"
```

**关键点：**
- `AgentCall` 是底层的消息调用追踪
- `Task` 是上层的业务任务管理
- 一个 `Task` 可能包含多个 `AgentCall`
- `AgentCall` 可以通过 `business_task_id` 关联到 `Task`
- 前端通过 `TaskManager` 获取任务进度，而不是直接查询 `AgentCall`

---

## 注意事项

1. **User 消息的处理**：
   - User 不是 Agent，没有 `message_buffer`
   - User 消息的发送和接收由外部业务层处理
   - 本方案暂不涉及 User 与系统的交互接口

2. **Manager 的决策逻辑**：
   - 超出消息设计范围
   - 需要单独设计 Manager 的 prompt 和决策流程

3. **消息持久化**：
   - 当前通过 `GroupChatSession` 持久化到 JSONL 文件
   - MessageRouter 不负责持久化，只负责路由

4. **并发安全**：
   - `asyncio.Queue` 天然支持并发
   - 多个 Agent 可以并发发送消息
   - MessageRouter 的 `publish_message()` 是同步方法，但 `put_nowait()` 是线程安全的
   - `AgentCallManager` 使用 `threading.Lock` 保护共享状态

5. **调用管理的持久化**：
   - `AgentCallManager._calls` 是内存字典
   - 所有状态变更都记录到 `agent_calls.jsonl` 日志文件
   - 内存删除后仍可从日志查询历史调用

6. **异步设计的权衡**：
   - **优点**：真正的异步，调用者不阻塞，支持并发调用
   - **缺点**：LLM 需要主动查询结果，增加复杂度
   - **建议**：初期实现异步 + 查询工具，后期可以添加自动通知机制

7. **循环回复的避免**：
   - 通过 `MessageType` 区分 TASK 和 NOTIFICATION
   - TASK 需要执行并回复，NOTIFICATION 只记录不回复
   - 确保消息链路有明确的终止条件

8. **命名约定**：
   - `AgentCall`：消息层面的调用追踪（细粒度）
   - `Task`：业务层面的任务管理（粗粒度，未来实现）
   - 两者通过 `business_task_id` 关联

9. **生命周期管理**：
   - 不使用简单的 LRU 缓存（可能删除正在执行的调用）
   - 基于状态和时间的智能清理策略
   - PENDING/RUNNING 状态永不删除
   - COMPLETED 状态根据 MessageType 决定保留时间
   - FAILED/TIMEOUT 状态保留 5 分钟便于调试

10. **超时机制**：
    - 每个调用有独立的 `timeout_seconds` 配置
    - 后台线程每 30 秒检查一次
    - 超时后自动标记为 TIMEOUT 状态
    - 避免调用永久占用内存

11. **日志分离**：
    - 通用日志：`lifeprism.log`（所有模块的日志）
    - AgentCall 日志：`agent_calls.jsonl`（专门记录调用历史）
    - 使用独立的 logger，互不干扰

---
   - `Task`：业务层面的任务管理（粗粒度，未来实现）
   - 两者通过 `business_task_id` 关联

---

## 设计决策总结

### 决策 1：群聊消息何时写入？

**决策**：在 `Agent._process_message()` 中，LLM 返回后立即写入

**理由**：
- 确保每次 Agent 的回复都被记录
- 写入时机明确：LLM 返回后、发送下一条消息前
- 便于调试和追踪对话历史

### 决策 2：call_agent 是否立即返回结果？

**决策**：采用异步设计，立即返回 call_id，不等待执行完成

**理由**：
- 真正的异步，调用者不阻塞
- 支持并发调用（A 可以同时派遣多个调用给不同的 Agent）
- 符合现实场景（派遣调用后继续做其他事）
- 通过 `query_call_status` 工具查询结果

**权衡**：
- 增加了 LLM 的使用复杂度（需要主动查询）
- 但提供了更大的灵活性和并发能力

### 决策 3：B 完成调用后是否自动通知 A？

**决策**：默认不自动通知，A 需要主动查询；可选支持自动通知

**理由**：
- 避免无限循环（A → B → A → B ...）
- 通过 `MessageType` 区分 TASK 和 NOTIFICATION
- 给予 LLM 更多控制权（决定何时查询结果）

**可选扩展**：
- 在 `_process_message` 中添加自动通知逻辑
- 发送 NOTIFICATION 类型消息给调用发起者
- A 收到 NOTIFICATION 后不会自动回复

### 决策 4：调用如何统一管理？

**决策**：引入 `AgentCallManager`，所有调用在其中注册

**理由**：
- 避免调用分散在各个 Agent 的队列中
- 提供统一的调用状态追踪和查询能力
- `_calls` 字典就是异步调用的 "pending 池"
- 支持查询调用状态、执行时长、结果等信息

### 决策 5：如何区分消息层调用和业务层任务？

**决策**：使用不同的命名 —— `AgentCall` vs `Task`

**理由**：
- `AgentCall`：消息层面，细粒度，追踪一次 Agent 调用
- `Task`：业务层面，粗粒度，管理用户级别的任务
- 通过 `business_task_id` 字段关联两者
- 避免命名冲突，概念清晰

**关系**：
- 一个业务 `Task` 可能包含多个 `AgentCall`
- `AgentCall` 可以关联到 `Task`（通过 `business_task_id`）
- 前端通过 `TaskManager` 获取任务进度，而不是直接查询 `AgentCall`

---

## 总结

2. **Manager 的决策逻辑**：
   - 超出消息设计范围
   - 需要单独设计 Manager 的 prompt 和决策流程

3. **消息持久化**：
   - 当前通过 `GroupChatSession` 持久化到 JSONL 文件
   - MessageRouter 不负责持久化，只负责路由

4. **并发安全**：
   - `asyncio.Queue` 天然支持并发
   - 多个 Agent 可以并发发送消息
   - MessageRouter 的 `publish_message()` 是同步方法，但 `put_nowait()` 是线程安全的

---

## 总结

本方案通过以下设计实现了三个核心原则：

1. **避免越权**：Agent 只持有 MessageRouter 引用，无法访问其他 Agent
2. **按需上下文**：通过 `GroupChatContext.get_agent_context()` 提供定制化上下文
3. **点对点路由**：MessageRouter 精确路由到目标 Agent 的私有队列

核心优势：
- 简单直接，无过度设计
- 异步解耦，支持并发
- 消息有序，FIFO 保证
- 完整记录，便于调试
- 调用追踪，状态可查

**命名约定：**
- `AgentCall`：消息层面的调用追踪（细粒度，一次 LLM 调用）
- `Task`：业务层面的任务管理（粗粒度，用户级别任务，未来实现）
- 两者通过 `business_task_id` 关联

**核心解决的问题：**
1. ✅ 群聊消息在 `Agent._process_message()` 中，LLM 返回后立即写入
2. ✅ 异步设计，`call_agent` 立即返回 call_id，不阻塞调用者
3. ✅ 通过 `MessageType` 避免循环回复（TASK vs NOTIFICATION）
4. ✅ 通过 `AgentCallManager` 统一管理所有调用，提供 pending 池和状态查询
5. ✅ 命名清晰区分消息层调用（AgentCall）和业务层任务（Task）

下一步：按照实现优先级逐步开发。
