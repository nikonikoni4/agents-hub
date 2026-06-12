# Agent 上下文主动压缩 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Agent 级别的 CLI session 上下文主动压缩，支持前端 HTTP 触发（成员列表下拉菜单 + 输入框 slash command）。

**Architecture:** 压缩逻辑放在 Agent 基类 `compress_context()` 方法中，通过 `self.execute()` 让 Agent 在当前 session 中自我总结，然后用摘要新建 session。前端通过两个入口触发：成员列表 `...` 下拉菜单和输入框 `/` slash command。压缩状态由前端本地管理（`compressingAgents` Set），不持久化到后端。

**Tech Stack:** Python + FastAPI (后端), React + TypeScript (前端)

---

## File Structure

### 新增文件

| 文件 | 职责 |
|------|------|
| `agents_hub/core/foundation/prompt.py` | 系统级 prompt 模板（COMPACT_CONTEXT_PROMPT） |

### 修改文件

| 文件 | 变更 |
|------|------|
| `agents_hub/core/foundation/__init__.py` | 导出 AgentBusyError |
| `agents_hub/core/agent/base_agent.py` | 新增 `compress_context()` 方法 |
| `agents_hub/core/orchestration/group_chat.py` | 新增 `compress_all()` 方法 |
| `agents_hub/api/schemas/group_chats.py` | 新增压缩响应 Schema |
| `agents_hub/api/routes/group_chat.py` | 新增两个 POST 端点 |
| `agents_hub/api/services/group_chat_service.py` | 新增压缩服务方法 |
| `agents_hub/core/context/group_chat_runtime.py` | 新增 `add_system_message()` 方法 |
| `frontend/src/shared/types/api-schemas.ts` | 新增压缩相关类型 |
| `frontend/src/core/api/groupChatApi.ts` | 新增压缩 API 调用函数 |
| `frontend/src/features/chat/hooks/useMembers.ts` | 新增 compressing 状态管理和 compressAgent 方法 |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | MemberItem 新增 `...` 下拉菜单 |
| `frontend/src/layouts/ChatArea/ChatInput.tsx` | 新增通用 slash command 框架 |

---

## Task 1: Foundation 层 — 异常类和 Prompt 模板

**Files:**
- Create: `agents_hub/core/foundation/prompt.py`
- Modify: `agents_hub/core/foundation/exceptions.py` — 新增 AgentBusyError
- Modify: `agents_hub/core/foundation/__init__.py` — 导出 AgentBusyError

- [x] **Step 1: 在 exceptions.py 中添加 AgentBusyError**

在 `exceptions.py` 的 `CompactionError` 之后添加：

```python
class AgentBusyError(AgentsHubError):
    """Agent 正在执行任务，无法压缩上下文"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__(
            message=f"Agent {agent_name} 正在执行任务，无法压缩上下文",
            error_code="AGENT_BUSY",
            details={"agent_name": agent_name},
        )
```

并在 `__all__` 中添加 `"AgentBusyError"`。

- [x] **Step 2: 创建 prompt.py — COMPACT_CONTEXT_PROMPT**

```python
# agents_hub/core/foundation/prompt.py
"""系统级 prompt 模板"""

COMPACT_CONTEXT_PROMPT = """\
<compact_request>
请总结你当前的工作上下文：
1. 已经完成的工作内容
2. 当前正在做的事情
3. 接下来需要完成的任务
4. 关键决策和约束

请简洁明了，控制在 500 字以内。
</compact_request>
"""
```

- [x] **Step 3: 更新 foundation/__init__.py 导出 AgentBusyError**

在 `__init__.py` 的 exceptions import 中添加 `AgentBusyError`，并在 `__all__` 中添加。

- [x] **Step 4: 验证导入正常** ✅

- [x] **Step 5: Commit** ✅

---

## Task 2: GroupChatRuntime — add_system_message 方法

**Files:**
- Modify: `agents_hub/core/context/group_chat_runtime.py`

- [ ] **Step 1: 在 GroupChatRuntime 中添加 add_system_message 方法**

在 `add_message` 方法之后添加：

```python
async def add_system_message(self, content: str) -> None:
    """
    添加系统消息到群聊历史

    Args:
        content: 系统消息内容
    """
    from datetime import datetime

    from agents_hub.agent_bridge.models import AgentResult
    from agents_hub.config.types import AgentPlatform, RoleType

    system_result = AgentResult(
        text=content,
        session_id="",
        timestamp=datetime.now().isoformat(),
        agent_name="__SYSTEM__",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.SYSTEM,
    )
    await self.add_message(system_result)
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/core/context/group_chat_runtime.py
git commit -m "feat(runtime): add add_system_message method"
```

---

## Task 3: Agent 基类 — compress_context 方法

**Files:**
- Modify: `agents_hub/core/agent/base_agent.py`

- [ ] **Step 1: 在 Agent 类中添加 compress_context 方法**

在 `_update_context_usage` 方法之后添加：

```python
async def compress_context(self):
    """
    压缩 Agent 的 CLI session 上下文

    流程：
    1. 忙碌校验
    2. 发送压缩 prompt 给当前 session，让 Agent 自我总结
    3. 提取摘要
    4. 写入留痕文件
    5. 用摘要新建 session
    6. 更新状态
    7. 广播 refresh

    Returns:
        CompressResult: 包含 old_session_id, new_session_id, context_usage_before, context_usage_after

    Raises:
        AgentBusyError: Agent 正在执行任务
    """
    from datetime import datetime

    from agents_hub.core.foundation.exceptions import AgentBusyError
    from agents_hub.core.foundation.prompt import COMPACT_CONTEXT_PROMPT

    # 1. 忙碌校验
    agent_member_info = self.group_chat_context.agent_member_info.get(self.name)
    if agent_member_info and agent_member_info.status == "busy":
        raise AgentBusyError(self.name)

    old_session_id = self.main_session_id
    context_usage_before = self.context_usage

    # 2. 发送压缩 prompt 给当前 session
    result = await self.execute(COMPACT_CONTEXT_PROMPT)

    # 3. 提取摘要
    summary = result.text if result.text else ""

    # 4. 写入留痕文件
    # Spec 明确要求：留痕文件写入失败仅 log warning，不影响压缩流程。
    # 这是项目编码规则"中间层不做兜底"的特例，因为留痕是辅助功能而非核心路径。
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        handoff_dir = Path(self.agent_cwd) / "docs" / "hand-off"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_file = handoff_dir / f"{timestamp}-{self.name}-compact.md"
        handoff_content = (
            f"# Context Compact - {self.name} - {datetime.now().isoformat()}\n\n"
            f"## 原 Session\n"
            f"- session_id: {old_session_id}\n"
            f"- context_usage: {context_usage_before}K tokens\n\n"
            f"## 摘要\n"
            f"{summary}\n\n"
            f"## 新 Session\n"
            f"- session_id: (待填充)\n"
        )
        handoff_file.write_text(handoff_content, encoding="utf-8")
    except Exception as e:
        self.logger.warning("留痕文件写入失败: %s", str(e))

    # 5. 清空 main_session
    if agent_member_info:
        agent_member_info.main_session = None

    # 6. 用摘要作为首轮 prompt 新建 session（失败时回滚 main_session）
    try:
        new_result = await self.execute(summary)
    except Exception as e:
        # 回滚 main_session 到旧值
        if agent_member_info:
            agent_member_info.main_session = old_session_id
        self.logger.error("Agent %s 新建 session 失败，已回滚 main_session: %s", self.name, str(e))
        raise
    new_session_id = new_result.session_id

    # 7. 更新留痕文件中的新 session_id
    try:
        handoff_content = handoff_content.replace(
            "- session_id: (待填充)", f"- session_id: {new_session_id}"
        )
        handoff_file.write_text(handoff_content, encoding="utf-8")
    except Exception:
        pass

    # 8. 更新 main_session
    if agent_member_info:
        agent_member_info.main_session = new_session_id

    # 9. 重置 context_usage
    await self.group_chat_context.runtime.update_agent_context_usage(self.name, 0)

    # 10. 写入系统消息
    system_msg = (
        f"⚙️ Agent {self.name} 上下文已压缩\n"
        f"   旧 session: {old_session_id} → 新 session: {new_session_id}\n"
        f"   {context_usage_before}K tokens → 0K tokens"
    )
    await self.group_chat_context.runtime.add_system_message(system_msg)

    # 11. 广播 refresh（update_agent_context_usage 内部已调用 _notify_change，无需重复调用）

    self.logger.info(
        "Agent %s 上下文已压缩: old_session=%s, new_session=%s, usage_before=%dK",
        self.name,
        old_session_id,
        new_session_id,
        context_usage_before,
    )

    return {
        "old_session_id": old_session_id,
        "new_session_id": new_session_id,
        "context_usage_before": context_usage_before,
        "context_usage_after": 0,
    }
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/core/agent/base_agent.py
git commit -m "feat(agent): add compress_context method"
```

---

## Task 4: GroupChat — compress_all 方法

**Files:**
- Modify: `agents_hub/core/orchestration/group_chat.py`

- [ ] **Step 1: 在 GroupChat 类中添加 compress_all 方法**

在 `compact_history` 方法之后添加：

```python
async def compress_all(self):
    """
    全量压缩所有在线 Agent 的上下文

    逐个处理，忙碌的 Agent 被跳过而非报错。

    Returns:
        list[dict]: 每个 Agent 的压缩结果
    """
    from agents_hub.core.foundation.exceptions import AgentBusyError

    results = []

    # 收集所有 agent（manager + workers）
    all_agents: list[Agent] = []
    if self.manager:
        all_agents.append(self.manager)
    all_agents.extend(self.workers.values())

    for agent in all_agents:
        try:
            result = await agent.compress_context()
            results.append({
                "agent_name": agent.name,
                "status": "compressed",
                "old_session_id": result["old_session_id"],
                "new_session_id": result["new_session_id"],
            })
        except AgentBusyError:
            results.append({
                "agent_name": agent.name,
                "status": "skipped",
                "reason": "busy",
            })
        except Exception as e:
            logger.warning("Agent %s 压缩失败: %s", agent.name, str(e))
            results.append({
                "agent_name": agent.name,
                "status": "failed",
                "reason": str(e),
            })

    return results
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/core/orchestration/group_chat.py
git commit -m "feat(group_chat): add compress_all method"
```

---

## Task 5: API Schema — 压缩响应类型

**Files:**
- Modify: `agents_hub/api/schemas/group_chats.py`

- [ ] **Step 1: 在 schemas 文件末尾添加压缩相关 Schema**

```python
# --- Compress Context Schemas ---


class CompressResponse(BaseModel):
    """单个 Agent 压缩响应"""

    message: str = Field(..., description="操作结果消息")
    old_session_id: str | None = Field(None, description="旧 session ID")
    new_session_id: str | None = Field(None, description="新 session ID")
    context_usage_before: int = Field(0, description="压缩前 context usage (K tokens)")
    context_usage_after: int = Field(0, description="压缩后 context usage (K tokens)")


class CompressAllResponse(BaseModel):
    """全量压缩响应"""

    message: str = Field(..., description="操作结果消息")
    results: list[dict] = Field(..., description="每个 Agent 的压缩结果")
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/api/schemas/group_chats.py
git commit -m "feat(schemas): add compress response schemas"
```

---

## Task 6: API Service — 压缩服务方法

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py`

- [ ] **Step 1: 在 GroupChatService 中添加 compress_agent_context 方法**

在 `toggle_use_docker` 方法之后添加：

```python
async def compress_agent_context(
    self,
    group_chat_id: str,
    agent_name: str,
) -> dict:
    """压缩指定 Agent 的上下文

    Args:
        group_chat_id: 群聊 ID
        agent_name: Agent 名称

    Returns:
        dict: 压缩结果

    Raises:
        ResourceNotFoundError: 群聊或 Agent 不存在
        StateError: Agent 正在执行任务（409）
    """
    from agents_hub.core.foundation.exceptions import AgentBusyError

    logger.info("压缩 Agent 上下文: group=%s, agent=%s", group_chat_id, agent_name)

    # 1. 加载群聊
    try:
        group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
    except GroupChatNotFoundError as e:
        raise ResourceNotFoundError(
            f"群聊不存在: {group_chat_id}",
            details={"group_chat_id": group_chat_id},
        ) from e

    # 2. 查找 Agent
    agent = group_chat._find_agent(agent_name)
    if agent is None:
        raise ResourceNotFoundError(
            f"Agent '{agent_name}' 不在此群聊中",
            details={"agent_name": agent_name},
        )

    # 3. 执行压缩
    try:
        result = await agent.compress_context()
    except AgentBusyError as e:
        raise StateError(
            f"Agent {agent_name} 正在执行任务，无法压缩上下文",
            details={"agent_name": agent_name},
        ) from e

    return {
        "message": f"Agent {agent_name} 上下文已压缩",
        "old_session_id": result["old_session_id"],
        "new_session_id": result["new_session_id"],
        "context_usage_before": result["context_usage_before"],
        "context_usage_after": result["context_usage_after"],
    }

    async def compress_all_agents(
        self,
        group_chat_id: str,
    ) -> dict:
        """全量压缩所有 Agent 的上下文

        Args:
            group_chat_id: 群聊 ID

        Returns:
            dict: 全量压缩结果

        Raises:
            ResourceNotFoundError: 群聊不存在
        """
        logger.info("全量压缩 Agent 上下文: group=%s", group_chat_id)

        # 1. 加载群聊
        try:
            group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
        except GroupChatNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e

        # 2. 执行全量压缩
        results = await group_chat.compress_all()

        # 3. 统计结果
        compressed_count = sum(1 for r in results if r["status"] == "compressed")

        return {
            "message": f"已压缩 {compressed_count} 个 Agent 的上下文",
            "results": results,
        }
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/api/services/group_chat_service.py
git commit -m "feat(service): add compress context service methods"
```

---

## Task 7: API Routes — 压缩端点

**Files:**
- Modify: `agents_hub/api/routes/group_chat.py`

- [ ] **Step 1: 在 routes 文件末尾添加两个压缩端点**

在 `upload_file` 端点之后添加：

```python
@router.post(
    "/{group_chat_id}/members/{agent_name}/compress",
    response_model=dict,
    responses={
        404: {"description": "群聊或 Agent 不存在"},
        409: {"description": "Agent 正在执行任务"},
    },
)
async def compress_agent_context(
    group_chat_id: str,
    agent_name: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """压缩指定 Agent 的 CLI session 上下文"""
    return await service.compress_agent_context(group_chat_id, agent_name)


@router.post(
    "/{group_chat_id}/compress-all",
    response_model=dict,
    responses={
        404: {"description": "群聊不存在"},
    },
)
async def compress_all_agents(
    group_chat_id: str,
    service: GroupChatService = Depends(get_group_chat_service),
):
    """全量压缩所有 Agent 的上下文"""
    return await service.compress_all_agents(group_chat_id)
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/api/routes/group_chat.py
git commit -m "feat(api): add compress context endpoints"
```

---

## Task 8: 前端类型和 API — 压缩接口

**Files:**
- Modify: `frontend/src/shared/types/api-schemas.ts`
- Modify: `frontend/src/core/api/groupChatApi.ts`

- [ ] **Step 1: 在 api-schemas.ts 末尾添加压缩相关类型**

```typescript
// ==================== 压缩相关 ====================

/**
 * 单个 Agent 压缩响应
 * 对应后端: CompressResponse schema
 */
export interface CompressApiResponse {
  /** 操作结果消息 */
  message: string;
  /** 旧 session ID */
  old_session_id: string | null;
  /** 新 session ID */
  new_session_id: string | null;
  /** 压缩前 context usage (K tokens) */
  context_usage_before: number;
  /** 压缩后 context usage (K tokens) */
  context_usage_after: number;
}

/**
 * 全量压缩响应
 * 对应后端: CompressAllResponse schema
 */
export interface CompressAllApiResponse {
  /** 操作结果消息 */
  message: string;
  /** 每个 Agent 的压缩结果 */
  results: CompressAllResultItem[];
}

/**
 * 全量压缩结果项
 */
export interface CompressAllResultItem {
  /** Agent 名称 */
  agent_name: string;
  /** 状态: compressed/skipped/failed */
  status: 'compressed' | 'skipped' | 'failed';
  /** 旧 session ID（仅 compressed） */
  old_session_id?: string;
  /** 新 session ID（仅 compressed） */
  new_session_id?: string;
  /** 跳过/失败原因 */
  reason?: string;
}
```

- [ ] **Step 2: 在 groupChatApi.ts 末尾添加压缩 API 函数**

```typescript
/**
 * 压缩指定 Agent 的上下文
 */
export async function compressAgentContext(
  chatId: string,
  agentName: string
): Promise<CompressApiResponse> {
  return apiClient.post<CompressApiResponse>(
    `/group-chats/${chatId}/members/${agentName}/compress`
  );
}

/**
 * 全量压缩所有 Agent 的上下文
 */
export async function compressAllAgents(chatId: string): Promise<CompressAllApiResponse> {
  return apiClient.post<CompressAllApiResponse>(`/group-chats/${chatId}/compress-all`);
}
```

并在文件顶部的 import 中添加 `CompressApiResponse` 和 `CompressAllApiResponse` 类型导入（它们定义在同一项目的类型文件中，通过 `@/shared/types` 导入）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/shared/types/api-schemas.ts frontend/src/core/api/groupChatApi.ts
git commit -m "feat(frontend/api): add compress context API types and functions"
```

---

## Task 9: 前端 useMembers — compressing 状态管理

**Files:**
- Modify: `frontend/src/features/chat/hooks/useMembers.ts`

- [ ] **Step 1: 在 useMembers hook 中添加 compressing 状态和 compressAgent 方法**

在 `useMembers` 函数中：

1. 在 `members` state 之后添加 `compressingAgents` state：

```typescript
const [compressingAgents, setCompressingAgents] = useState<Set<string>>(new Set());
```

2. 在 `toggleDockerMode` 之后添加 `compressAgent` 方法：

```typescript
const compressAgent = useCallback(
  async (agentName: string) => {
    if (!activeSessionId) return;

    // 标记开始压缩
    setCompressingAgents((prev) => new Set(prev).add(agentName));

    try {
      await compressAgentContext(activeSessionId, agentName);
      // 压缩成功后刷新成员列表（后端会广播 refresh，但主动刷新更可靠）
      await fetchMembers();
    } catch (error) {
      console.error('Failed to compress agent context:', error);
      throw error;
    } finally {
      // 标记压缩结束
      setCompressingAgents((prev) => {
        const next = new Set(prev);
        next.delete(agentName);
        return next;
      });
    }
  },
  [activeSessionId, fetchMembers]
);
```

3. 在 `return` 语句中添加 `compressAgent` 和在 members 的 useMemo 中合并 `compressing` 字段。

将 `return` 改为：

```typescript
// 在 members 映射后合并 compressing 状态
const membersWithCompressing = useMemo(
  () => members.map((m) => ({ ...m, compressing: compressingAgents.has(m.name) })),
  [members, compressingAgents]
);

return { members: membersWithCompressing, loading, refresh: fetchMembers, toggleDockerMode, compressAgent };
```

4. 在文件顶部 import 中添加 `compressAgentContext`：

```typescript
import { getMembers, listRoles, updateMemberDockerMode, compressAgentContext } from '@/core/api';
```

5. 在 `MemberWithRole` 接口中添加 `compressing` 字段：

```typescript
export interface MemberWithRole extends GroupChatMemberApiItem {
  role: RoleApiResponse | null;
  isOnline: boolean;
  compressing: boolean;  // 前端本地计算
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/chat/hooks/useMembers.ts
git commit -m "feat(hooks): add compressing state and compressAgent to useMembers"
```

---

## Task 10: 前端 RightSidebar — 成员列表下拉菜单

**Files:**
- Modify: `frontend/src/layouts/RightSidebar/RightSidebar.tsx`

- [ ] **Step 1: 修改 MemberItem 组件，添加 `...` 下拉菜单**

将 `MemberItem` 组件修改为包含下拉菜单的版本。需要：

1. 添加 `onCompress` prop
2. 添加下拉菜单状态管理
3. 添加 `...` 按钮和菜单项

```typescript
function MemberItem({
  member,
  onToggleDocker,
  onCompress,
}: {
  member: MemberWithRole;
  onToggleDocker: (memberName: string, enableDocker: boolean) => void;
  onCompress: (memberName: string) => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭菜单
  useEffect(() => {
    if (!showMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showMenu]);

  const canCompress = member.isOnline && member.status !== 'busy' && !member.compressing;

  return (
    <div className={styles.memberItem}>
      <div className={styles.memberAvatar}>
        <AvatarImage avatar={member.role?.avatar ?? null} fallback={member.name} />
      </div>
      <div className={styles.memberInfo}>
        <div className={styles.memberName}>{member.name}</div>
        <div className={styles.memberRole}>
          {member.role?.type === 'leader' ? '负责人' : '成员'}
          <span className={styles.memberPlatform}>{member.role?.platform ?? 'unknown'}</span>
          {member.context_usage != null && member.context_usage > 0 && (
            <span className={styles.memberContext}>{member.context_usage}K</span>
          )}
        </div>
        {member.cwd && (
          <div className={styles.memberCwd} title={member.cwd}>
            📁 {member.cwd}
          </div>
        )}
      </div>
      <div className={styles.memberStatus}>
        <span className={member.status === 'busy' ? styles.statusBusy : styles.statusIdle}>
          {member.compressing ? '压缩中' : member.status === 'busy' ? '忙碌' : '空闲'}
        </span>
      </div>
      <button
        className={styles.dockerToggle}
        onClick={() => onToggleDocker(member.name, !member.use_docker)}
        title={
          member.use_docker ? 'Docker 模式（点击切换到本地）' : '本地模式（点击切换到 Docker）'
        }
      >
        {member.use_docker ? '🐳' : '💻'}
      </button>
      <div className={styles.memberMenuWrapper} ref={menuRef}>
        <button
          className={styles.memberMenuBtn}
          onClick={() => setShowMenu(!showMenu)}
          title="更多操作"
        >
          ⋮
        </button>
        {showMenu && (
          <div className={styles.memberMenuDropdown}>
            <button
              className={styles.memberMenuItem}
              disabled={!canCompress}
              onClick={() => {
                setShowMenu(false);
                onCompress(member.name);
              }}
              title={
                !member.isOnline
                  ? 'Agent 离线'
                  : member.status === 'busy'
                    ? 'Agent 正在执行任务'
                    : member.compressing
                      ? '压缩中...'
                      : '压缩上下文'
              }
            >
              {member.compressing ? '压缩中...' : '压缩上下文'}
            </button>
          </div>
        )}
      </div>
      <div className={member.isOnline ? styles.onlineDot : styles.offlineDot} />
    </div>
  );
}
```

- [ ] **Step 2: 在 RightSidebar 组件中添加 compressAgent 调用**

在 `useMembers` 解构中添加 `compressAgent`：

```typescript
const { members, loading, toggleDockerMode, compressAgent } = useMembers();
```

在 `MemberItem` 渲染处传递 `onCompress`：

```typescript
<MemberItem
  key={member.name}
  member={member}
  onToggleDocker={handleToggleDocker}
  onCompress={handleCompress}
/>
```

添加 `handleCompress` 回调：

```typescript
const handleCompress = useCallback(
  (memberName: string) => {
    compressAgent(memberName).catch((error) => {
      const message = error instanceof Error ? error.message : '压缩上下文失败';
      toast.error(message);
    });
  },
  [compressAgent, toast]
);
```

- [ ] **Step 3: 添加下拉菜单样式**

在 `RightSidebar.module.css` 中添加：

```css
.memberMenuWrapper {
  position: relative;
}

.memberMenuBtn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 4px;
  font-size: 14px;
  color: var(--text-secondary);
  border-radius: 4px;
}

.memberMenuBtn:hover {
  background: var(--bg-hover);
}

.memberMenuDropdown {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 10;
  min-width: 120px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 4px 0;
}

.memberMenuItem {
  display: block;
  width: 100%;
  padding: 6px 12px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  font-size: 13px;
  color: var(--text-primary);
}

.memberMenuItem:hover:not(:disabled) {
  background: var(--bg-hover);
}

.memberMenuItem:disabled {
  color: var(--text-disabled);
  cursor: not-allowed;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/layouts/RightSidebar/RightSidebar.tsx frontend/src/layouts/RightSidebar/RightSidebar.module.css
git commit -m "feat(sidebar): add compress context dropdown to MemberItem"
```

---

## Task 11: 前端 ChatInput — Slash Command 框架

**Files:**
- Modify: `frontend/src/layouts/ChatArea/ChatInput.tsx`

- [ ] **Step 1: 在 ChatInput 中添加 slash command 检测逻辑**

在 `ChatInput` 组件中添加：

1. 新增 state：

```typescript
const [showSlash, setShowSlash] = useState(false);
const [slashIndex, setSlashIndex] = useState(0);
```

2. 定义命令注册表（在组件内部）：

```typescript
const slashCommands = useMemo(
  () => [
    {
      name: '压缩上下文',
      description: '压缩 Agent 的 CLI session 上下文',
    },
  ],
  []
);
```

3. 修改 `handleChange` 检测 `/` 触发：

```typescript
const handleChange = useCallback(
  (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInputValue(value);

    const cursorPos = e.target.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPos);

    // 检测 slash command（行首或 @name 之后的 /）
    const slashMatch = textBeforeCursor.match(/(^|@\\w+\\s)\\/$/);
    if (slashMatch) {
      setShowSlash(true);
      setSlashIndex(0);
      setShowMention(false);
      return;
    }

    // 检测 @ 触发（保留原有逻辑）
    const atIndex = textBeforeCursor.lastIndexOf('@');
    if (atIndex !== -1) {
      const charBeforeAt = atIndex > 0 ? textBeforeCursor[atIndex - 1] : ' ';
      if (charBeforeAt === ' ' || charBeforeAt === '\n' || atIndex === 0) {
        const query = textBeforeCursor.slice(atIndex + 1);
        if (!query.includes(' ') && !query.includes('\n')) {
          setMentionQuery(query);
          setMentionIndex(0);
          setShowMention(true);
          setShowSlash(false);
          return;
        }
      }
    }
    setShowMention(false);
    setShowSlash(false);
  },
  []
);
```

4. 在 `handleKeyDown` 中添加 slash command 导航和选择逻辑：

在现有的 `showMention` 处理之前添加：

```typescript
// slash command 选择导航
if (showSlash && slashCommands.length > 0) {
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    setSlashIndex((prev) => (prev + 1) % slashCommands.length);
    return;
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    setSlashIndex((prev) => (prev - 1 + slashCommands.length) % slashCommands.length);
    return;
  }
  if (e.key === 'Enter' || e.key === 'Tab') {
    e.preventDefault();
    // 检测是否有 @name 前缀
    const atMatch = inputValue.match(/@(\w+)\s+\//);
    const agentName = atMatch ? atMatch[1] : undefined;
    // 清空输入框
    setInputValue('');
    setShowSlash(false);
    // 触发压缩（通过 props 回调）
    if (onSlashCommand) {
      onSlashCommand('compress', agentName);
    }
    return;
  }
  if (e.key === 'Escape') {
    e.preventDefault();
    setShowSlash(false);
    return;
  }
}
```

5. 更新 `handleKeyDown` 的依赖数组和 `ChatInputProps` 接口：

```typescript
export interface ChatInputProps {
  activeSessionId: string | null;
  members: { name: string }[];
  onSend: (text: string, files?: UploadedFileInfo[]) => void;
  quotedMessage?: MessageApiItem | null;
  onClearQuote?: () => void;
  onSlashCommand?: (command: string, agentName?: string) => void;
}
```

6. 在 JSX 中添加 slash command 下拉菜单（在 mention dropdown 之后）：

```typescript
{showSlash && slashCommands.length > 0 && (
  <div className={styles.mentionDropdown} onClick={(e) => e.stopPropagation()}>
    {slashCommands.map((cmd, i) => (
      <div
        key={cmd.name}
        className={styles.mentionItem}
        style={i === slashIndex ? { background: 'var(--bg-hover)' } : undefined}
        onMouseDown={(e) => {
          e.preventDefault();
          const atMatch = inputValue.match(/@(\w+)\s+\//);
          const agentName = atMatch ? atMatch[1] : undefined;
          setInputValue('');
          setShowSlash(false);
          if (onSlashCommand) {
            onSlashCommand('compress', agentName);
          }
        }}
        onMouseEnter={() => setSlashIndex(i)}
      >
        <span>/{cmd.name}</span>
        <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginLeft: '8px' }}>
          {cmd.description}
        </span>
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 2: 在 ChatArea 父组件中连接 onSlashCommand**

需要在使用 `ChatInput` 的父组件（`ChatArea`）中传递 `onSlashCommand` prop。

**关键**：复用 `useMembers` 的 `compressAgent` 方法（已维护 compressing 状态），避免绕过前端 compressing 保护。全量压缩直接调用 API（无单个 Agent 的 compressing 状态需要维护）。

找到 `ChatInput` 的使用位置，添加：

```typescript
const { members, compressAgent } = useMembers();
const { compressAllAgents } = useGroupChatApi(); // 或直接 import

const handleSlashCommand = useCallback(
  (command: string, agentName?: string) => {
    if (command === 'compress') {
      if (agentName) {
        // 复用 useMembers 的 compressAgent（有 compressing 状态保护）
        compressAgent(agentName).catch((err) => {
          toast.error(err instanceof Error ? err.message : '压缩失败');
        });
      } else {
        // 全量压缩直接调用 API
        if (activeSessionId) {
          compressAllAgents(activeSessionId).catch((err) => {
            toast.error(err instanceof Error ? err.message : '压缩失败');
          });
        }
      }
    }
  },
  [activeSessionId, compressAgent, toast]
);
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/layouts/ChatArea/ChatInput.tsx
git commit -m "feat(chat-input): add slash command framework for context compression"
```

---

## Task 12: 端到端验证

- [ ] **Step 1: 启动后端，验证 API 端点**

Run: `python -m agents_hub` 或项目启动命令

验证：
- `POST /group-chats/{id}/members/{name}/compress` 返回正确响应
- `POST /group-chats/{id}/compress-all` 返回正确响应
- Agent 忙碌时返回 409
- Agent 不存在时返回 404

- [ ] **Step 2: 启动前端，验证 UI 交互**

验证：
- 成员列表中出现 `...` 按钮
- 点击 `...` 弹出下拉菜单
- 忙碌 Agent 的菜单项置灰
- 输入框输入 `/` 弹出命令列表
- `@name /` 触发指定 Agent 压缩
- `/` 触发全量压缩

- [ ] **Step 3: Commit 最终调整（如有）**

```bash
git add -A
git commit -m "feat: agent context compression - end-to-end verification"
```
