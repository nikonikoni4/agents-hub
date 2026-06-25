# 群聊Agent单独聊天（Private Chat）PRD

Status: ready-for-agent

## Problem Statement

用户在使用Agents Hub的群聊功能时，希望能够与群聊中的某个agent进行单独对话，而不被群聊中的其他消息打断。当前的单聊功能（`continue_group_chat`类型）存在以下问题：

1. **会话污染**：单聊session会保存到`index.json`，导致单聊session列表混入群聊相关的session
2. **状态冲突**：单聊中的agent仍然可以接收群聊消息，导致对话被打断
3. **缺乏状态标识**：无法直观地看到哪个agent正在与用户进行单独聊天
4. **操作冲突**：单聊中的agent可能被其他用户停止、重置或压缩，导致单聊中断

用户需要一个与群聊强关联但独立的单聊通道，确保单聊过程中不被群聊消息干扰，同时保持与群聊session的关联性。

## Solution

在群聊成员列表的下拉菜单中增加"邀请单聊"功能，允许用户与群聊中的非manager agent进行单独聊天。该功能的特点：

1. **状态隔离**：新增`in_private_chat`状态，单聊中的agent不接受群聊消息
2. **操作保护**：单聊中的agent不能被停止、重置、压缩
3. **自动退出**：agent最后一次回复后3分钟无活动自动退出单聊状态
4. **会话透传**：单聊session不保存到`index.json`，由平台单独管理
5. **Manager限制**：禁用manager的单聊功能，避免复杂的消息处理逻辑

## User Stories

1. 作为用户，我希望在群聊成员列表的下拉菜单中看到"邀请单聊"选项，以便与特定agent进行单独对话
2. 作为用户，我希望点击"邀请单聊"后进入单聊界面，以便与agent进行一对一交流
3. 作为用户，我希望在单聊过程中不被群聊消息打断，以便专注于与当前agent的对话
4. 作为用户，我希望看到agent处于"单聊中"状态，以便了解agent当前的工作状态
5. 作为用户，我希望在单聊界面看到"退出单聊"按钮，以便随时结束单聊
6. 作为用户，我希望在3分钟无活动后自动退出单聊，以便agent能够继续处理群聊任务
7. 作为用户，我希望在单聊中继续使用当前群聊中agent的session，以便保持对话的连续性
8. 作为用户，我希望单聊session不保存到单聊session列表，以便保持列表的整洁
9. 作为用户，我希望在agent压缩时无法邀请单聊，以便避免状态冲突
10. 作为用户，我希望在单聊中无法停止、重置或压缩agent，以便保护单聊过程不被中断
11. 作为用户，我希望在群聊中向单聊中的agent发送消息时收到自动回复，以便了解agent当前状态
12. 作为用户，我希望manager不能被邀请单聊，以便避免复杂的消息处理逻辑
13. 作为用户，我希望在单聊中发送消息时重置3分钟计时器，以便延长单聊时间
14. 作为用户，我希望在退出单聊后agent恢复idle状态，以便继续处理群聊任务
15. 作为用户，我希望在单聊界面看到agent的名称和头像，以便确认当前对话的agent
16. 作为用户，我希望在单聊中使用fork和全新选项，以便开始新的对话或分叉现有对话
17. 作为用户，我希望在单聊中看到continue选项，以便继续群聊中某个agent的会话
18. 作为用户，我希望在单聊中看到消息历史，以便回顾之前的对话内容
19. 作为用户，我希望在单聊中使用SSE流式传输，以便实时看到agent的回复
20. 作为用户，我希望在单聊结束后单聊界面自动关闭，以便返回群聊界面

## Implementation Decisions

### 1. 状态管理

**新增状态**：`in_private_chat`

**状态定义**：
- 在`AgentMemberInfo.status`字段中新增`"in_private_chat"`状态
- 前端`GroupChatMemberApiItem.status`类型中新增`'in_private_chat'`枚举值

**状态转换**：
- `idle` → `in_private_chat`：调用`start-private-chat` API
- `in_private_chat` → `idle`：调用`stop-private-chat` API 或 3分钟超时自动转换

**状态限制**：
- 只有`idle`状态的agent才能进入单聊
- `in_private_chat`状态下的agent不能被停止、重置、压缩
- `in_private_chat`状态下的agent不接受群聊消息

### 2. API设计

**进入单聊**：`POST /{group_chat_id}/members/{agent_name}/start-private-chat`

请求参数：
- `group_chat_id`：群聊ID（路径参数）
- `agent_name`：Agent名称（路径参数）

响应：
- 成功：`{"agent_name": string, "status": "in_private_chat"}`
- 失败：
  - 404：群聊或Agent不存在
  - 409：Agent非idle状态（`StateError`）

**退出单聊**：`POST /{group_chat_id}/members/{agent_name}/stop-private-chat`

请求参数：
- `group_chat_id`：群聊ID（路径参数）
- `agent_name`：Agent名称（路径参数）

响应：
- 成功：`{"agent_name": string, "status": "idle"}`
- 失败：
  - 404：群聊或Agent不存在
  - 409：Agent非`in_private_chat`状态（`StateError`）

### 3. 消息处理

**消息拦截位置**：`GroupChat.send_message_to_agent()`

**拦截逻辑**：
```python
if agent_info.status == "in_private_chat":
    # 创建自动回复消息
    auto_reply = AgentMessage(
        send_from=agent_name,
        send_to=message.send_from,
        content=f"当前{agent_name}正在与user进行单独聊天，无法处理当前的消息：{message.content[:20]}，请稍后再发送该任务",
        type=MessageType.NOTIFICATION
    )
    # 写入群聊历史
    await self.add_message(auto_reply)
    return
```

**消息类型**：使用`NOTIFICATION`类型，不需要agent回复

### 4. 状态变化接口检查

需要在以下接口增加`in_private_chat`状态检查：

**stop_member**：
```python
if agent_info.status == "in_private_chat":
    raise StateError(
        f"Agent {agent_name} 正在单聊中，无法停止",
        details={"agent_name": agent_name, "current_status": "in_private_chat"}
    )
```

**reset_member**：
```python
if agent_info.status == "in_private_chat":
    raise StateError(
        f"Agent {agent_name} 正在单聊中，无法重置",
        details={"agent_name": agent_name, "current_status": "in_private_chat"}
    )
```

**compress_agent_context**：
```python
if agent_info.status == "in_private_chat":
    raise StateError(
        f"Agent {agent_name} 正在单聊中，无法压缩上下文",
        details={"agent_name": agent_name, "current_status": "in_private_chat"}
    )
```

**compress_all_agents**：
```python
for agent in agents:
    if agent.status == "in_private_chat":
        results.append({"agent_name": agent.name, "status": "skipped", "reason": "in_private_chat"})
        continue
    # 正常压缩逻辑
```

### 5. 前端交互流程

**邀请单聊流程**：
1. 用户点击群聊头部的`MoreVerticalIcon`按钮，打开成员管理弹窗
2. 在成员列表中，每个非manager成员旁边显示"邀请单聊"下拉选项
3. 用户点击"邀请单聊"：
   - 前端检查`useCompressStatusStore`，如果agent正在压缩，弹出toast拒绝
   - 前端调用`POST /{group_chat_id}/members/{agent_name}/start-private-chat`
   - 成功后，右侧栏切换到单聊tab，显示单聊界面
   - 成员列表中该agent状态更新为"单聊中"

**单聊界面**：
1. 复用现有的`SingleChatPanel`组件
2. 将原来的X按钮改为"退出单聊"按钮
3. 显示chat type标签：`continue`（继续群聊中某个agent的会话）
4. 支持`fork`和`全新`选项
5. 使用当前群聊中agent的session继续对话

**退出单聊流程**：
1. 用户点击"退出单聊"按钮：
   - 前端调用`POST /{group_chat_id}/members/{agent_name}/stop-private-chat`
   - 成功后，单聊界面关闭，返回群聊界面
   - 成员列表中该agent状态更新为"idle"

2. 3分钟自动退出：
   - 前端维护定时器，从agent最后一次回复开始计时
   - 用户发送消息时重置计时器
   - 3分钟无活动后，前端自动调用`stop-private-chat` API
   - 成功后，单聊界面关闭，显示toast提示

### 6. 计时器管理

**前端实现**：
- 在`singleChatStore`中维护`lastActivityTime`和`timerId`
- 每次收到agent回复时更新`lastActivityTime`并重置计时器
- 用户发送消息时重置计时器
- 3分钟超时后调用退出单聊API

**状态同步**：
- 前端定时器触发时调用后端API
- 后端API将agent状态从`in_private_chat`改回`idle`
- WebSocket通知前端刷新成员状态

### 7. Session管理

**Session透传**：
- 单聊session不保存到`index.json`
- 由平台单独管理（claude code，codex等）
- 使用当前群聊中agent的`main_session`继续对话

**Session选择**：
- 进入单聊时，读取agent的`main_session`
- 将`main_session`作为单聊的session_id
- 单聊消息通过SSE流式传输到该session

### 8. Manager限制

**前端限制**：
- 在成员管理弹窗中，manager成员不显示"邀请单聊"选项
- 前端通过`agent_name === config.default_manager_name`判断

**后端限制**：
- 在`start-private-chat` API中检查agent是否为manager
- 如果是manager，返回403错误

### 9. WebSocket通知

**通知时机**：
- 进入单聊时：通知前端刷新成员状态
- 退出单聊时：通知前端刷新成员状态
- 3分钟超时退出时：通知前端刷新成员状态

**通知机制**：
- 调用现有的group chat WebSocket回调函数
- 发送RefreshSignal事件
- 前端收到后重新请求成员列表

### 10. 前端组件修改

**ManageMembersDialog**：
- 在每个非manager成员旁边添加"邀请单聊"下拉选项
- 点击后调用`start-private-chat` API
- 成功后切换到单聊tab

**SingleChatPanel**：
- 将X按钮改为"退出单聊"按钮
- 点击后调用`stop-private-chat` API
- 支持`continue`类型的chat type标签

**useMembers hook**：
- 添加`startPrivateChat`和`stopPrivateChat`方法
- 处理API调用和状态更新

**singleChatStore**：
- 添加`lastActivityTime`和`timerId`状态
- 添加`resetTimer`和`clearTimer`方法
- 处理3分钟超时逻辑

**compressStatusStore**：
- 无需修改，直接使用现有的`pendingAgents`判断

## Testing Decisions

### 测试边界

1. **状态转换测试**：
   - 测试`idle` → `in_private_chat`转换成功
   - 测试`busy/stopped/error/in_loop` → `in_private_chat`转换失败（返回409）
   - 测试`in_private_chat` → `idle`转换成功（手动退出）
   - 测试`in_private_chat` → `idle`转换成功（3分钟超时）

2. **操作限制测试**：
   - 测试单聊中执行stop操作失败（返回409）
   - 测试单聊中执行reset操作失败（返回409）
   - 测试单聊中执行compress操作失败（返回409）
   - 测试单聊中执行compress_all操作跳过该agent

3. **消息拦截测试**：
   - 测试单聊中发送群聊消息返回自动回复
   - 测试自动回复消息格式正确
   - 测试自动回复消息写入群聊历史

4. **计时器测试**：
   - 测试3分钟无活动自动退出
   - 测试用户发送消息重置计时器
   - 测试收到agent回复重置计时器

5. **压缩状态测试**：
   - 测试压缩中点击邀请单聊弹出toast拒绝
   - 测试压缩完成后可以正常邀请单聊

6. **Manager限制测试**：
   - 测试manager成员不显示"邀请单聊"选项
   - 测试调用manager的start-private-chat API返回403

7. **Session管理测试**：
   - 测试单聊session不保存到index.json
   - 测试单聊使用agent的main_session
   - 测试退出单聊后session状态正确

8. **WebSocket通知测试**：
   - 测试进入单聊时发送RefreshSignal
   - 测试退出单聊时发送RefreshSignal
   - 测试3分钟超时时发送RefreshSignal

### 测试模块

1. **API层测试**：
   - `start-private-chat` API测试
   - `stop-private-chat` API测试
   - 状态变化接口检查测试

2. **Core层测试**：
   - `send_message_to_agent`消息拦截测试
   - `stop_member`状态检查测试
   - `reset_member`状态检查测试
   - `compress_agent_context`状态检查测试

3. **前端组件测试**：
   - `ManageMembersDialog`邀请单聊选项测试
   - `SingleChatPanel`退出单聊按钮测试
   - 计时器管理测试

4. **集成测试**：
   - 完整的邀请单聊 → 对话 → 退出流程测试
   - 3分钟超时自动退出流程测试
   - 压缩状态拒绝邀请单聊流程测试

### 测试数据

- 使用现有的群聊测试数据
- 创建测试用的agent状态数据（idle、busy、stopped、error、in_loop、in_private_chat）
- 模拟agent回复消息用于计时器测试

## Out of Scope

1. **Manager单聊**：本PRD不包含manager的单聊功能，避免复杂的消息处理逻辑
2. **单聊历史持久化**：单聊session不保存到index.json，历史由平台管理
3. **单聊消息加密**：本PRD不包含单聊消息的加密功能
4. **单聊消息搜索**：本PRD不包含单聊消息的搜索功能
5. **单聊消息导出**：本PRD不包含单聊消息的导出功能
6. **多agent同时单聊**：本PRD只支持与一个agent进行单聊
7. **单聊消息通知**：本PRD不包含单聊消息的通知功能
8. **单聊消息已读状态**：本PRD不包含单聊消息的已读状态功能
9. **单聊消息撤回**：本PRD不包含单聊消息的撤回功能
10. **单聊消息引用**：本PRD不包含单聊消息的引用功能

## Further Notes

### 依赖关系

- 依赖现有的群聊成员管理功能（`ManageMembersDialog`、`useMembers`）
- 依赖现有的单聊功能（`SingleChatPanel`、`singleChatStore`）
- 依赖现有的压缩状态管理（`useCompressStatusStore`）
- 依赖现有的WebSocket通知机制
- 依赖现有的API路由和Service层结构

### 后续迭代

1. **Manager单聊支持**：在后续版本中考虑支持manager的单聊功能，需要处理Heartbeat和Loop结束通知
2. **单聊消息持久化**：考虑将单聊消息保存到独立的存储位置，支持历史查询
3. **单聊消息通知**：考虑添加单聊消息的通知功能，提醒用户有新消息
4. **单聊消息已读状态**：考虑添加单聊消息的已读状态功能
5. **多agent同时单聊**：考虑支持与多个agent同时进行单聊
6. **单聊消息搜索**：考虑添加单聊消息的搜索功能
7. **单聊消息导出**：考虑添加单聊消息的导出功能
8. **单聊消息加密**：考虑添加单聊消息的加密功能

### 风险点

1. **状态同步**：前端定时器和后端状态可能存在同步延迟
2. **并发控制**：多个用户同时邀请同一个agent单聊可能导致状态冲突
3. **Session管理**：透传session可能导致平台管理复杂性增加
4. **消息拦截**：在`send_message_to_agent`中拦截消息可能影响其他功能
5. **WebSocket通知**：频繁的状态变化可能导致WebSocket通知过多

### 监控指标

1. **单聊使用率**：统计单聊功能的使用频率
2. **单聊时长**：统计单聊的平均时长
3. **超时退出率**：统计3分钟超时自动退出的比例
4. **状态冲突率**：统计因状态冲突导致的邀请失败比例
5. **消息拦截率**：统计单聊中拦截的群聊消息数量
