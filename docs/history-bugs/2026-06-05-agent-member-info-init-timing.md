# Agent 初始化时 agent_member_info 时序问题

- 发现时间：2026-06-05
- 影响范围：所有新建群聊的 Agent（agent_cwd 为空导致工作目录错误）
- 状态：已修复

## 问题描述

新建群聊时，Agent 的 `agent_cwd` 始终为空字符串，导致 Agent 执行时没有正确的工作目录。

## 根因

`GroupChat.start()` 的初始化顺序导致 Agent 对象创建时 `agent_member_infos` 为空：

```
1. group_chat_context.load()        → agent_member_infos = {} (空)
2. runtime.initialize_metadata()
3. _init_agents()                    → Agent.__init__() 读取 agent_member_infos → 空
                                       ↓ agent_cwd = "" (缓存)
4. _generate_and_register_tokens()   → set_agent_token_and_default_cwd() 创建 AgentMemberInfo
                                       ↓ cwd = project_path/w1
5. _initialize_new_members()         → agent.execute() 使用缓存的 agent_cwd = "" ← BUG
```

步骤 3 中 `Agent.__init__` 将 `agent_cwd` 缓存为实例变量，步骤 4 才设置正确的 `cwd`，但 Agent 对象已经不会更新。

## 修复方案

将 `agent_token` 和 `agent_cwd` 从缓存实例变量改为动态 property：

```python
# 修复前（base_agent.py）
class Agent:
    def __init__(self, ...):
        agent_member_info = group_chat_context.agent_member_info.get(self.name)
        self.agent_token: str = agent_member_info.token if agent_member_info else ""
        self.agent_cwd: str = agent_member_info.cwd if agent_member_info else ""

# 修复后
class Agent:
    @property
    def agent_token(self) -> str:
        info = self.group_chat_context.agent_member_info.get(self.name)
        return info.token if info else ""

    @property
    def agent_cwd(self) -> str:
        info = self.group_chat_context.agent_member_info.get(self.name)
        return info.cwd if info else ""
```

## 关联问题：get_or_create_agent_member_info 默认 cwd 为空

`group_chat_runtime.py` 的 `get_or_create_agent_member_info` 创建新条目时 `cwd` 默认为空字符串。多个调用方（`set_agent_use_docker`、`update_context_load_state`、`update_agent_member_info_from_result`）首次创建条目时不设置 `cwd`。

修复：新条目默认 `cwd=project_path`：

```python
def get_or_create_agent_member_info(self, agent_name: str) -> AgentMemberInfo:
    if agent_name not in self.state.agent_member_infos:
        self.state.agent_member_infos[agent_name] = AgentMemberInfo(cwd=self.project_path)
    return self.state.agent_member_infos[agent_name]
```

## 关联问题：_update_agent_context_state 重复创建逻辑

`agent_context.py` 的 `_update_agent_context_state` 直接创建 `AgentMemberInfo`（不经过 `get_or_create`），导致 `cwd` 为空。

修复：复用 `runtime.update_context_load_state()`，统一通过 `get_or_create` 创建条目。

## 涉及文件

- `agents_hub/core/agent/base_agent.py` - agent_token/agent_cwd 改为 property
- `agents_hub/core/context/group_chat_runtime.py` - get_or_create 默认 cwd
- `agents_hub/core/context/agent_context.py` - _update_agent_context_state 简化
