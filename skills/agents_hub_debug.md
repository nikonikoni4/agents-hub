# Agents Hub 系统 Debug 指南

## 概述

本文档提供 Agents Hub 系统的问题排查方法、资源定位技巧和 debug 流程。适用于开发者和维护者快速定位和解决系统问题。

## 1. 核心资源定位

### 1.1 Agent Session 原始文件位置

#### Codex 平台
- **路径**: `local_data/agents/codex/work_root/sessions/YYYY/MM/DD/`
- **文件格式**: `<type>-<date>T<time>-<session_id>.jsonl`
- **匹配方式**: **部分匹配**（session_id 只是文件名的一部分）

**示例**:
```
session_id: 019ee47a-9ef6-7062-bf2d-ec9b9861583f
文件名: rollout-2026-06-20T18-01-42-019ee47a-9ef6-7062-bf2d-ec9b9861583f.jsonl
```

**定位步骤**:
1. 在群聊目录找到 `agent_members/codex/agent_member.json`
2. 读取 `main_session` 字段（如 `019ee47a-9ef6-7062-bf2d-ec9b9861583f`）
3. 在 `local_data/agents/codex/work_root/sessions/` 下按日期查找
4. 使用部分匹配搜索包含该 session_id 的文件

**搜索命令**:
```bash
# Windows (Git Bash)
find local_data/agents/codex/work_root/sessions/ -name "*019ee47a-9ef6-7062*"

# 或者使用 grep
grep -r "019ee47a-9ef6-7062" local_data/agents/codex/work_root/sessions/
```

#### Claude 平台
- **路径**: `<project_path>/.claude/sessions/<session_id>.jsonl`
- **文件格式**: `<session_id>.jsonl`
- **匹配方式**: **精确匹配**（session_id 就是文件名）

**示例**:
```
session_id: f8c2c14e-9bef-4f97-b3c1-17227c0c49b9
文件路径: D:/desktop/软件开发/agents-hub/.claude/sessions/f8c2c14e-9bef-4f97-b3c1-17227c0c49b9.jsonl
```

**定位步骤**:
1. 在群聊目录找到 `agent_members/claude/agent_member.json`
2. 读取 `main_session` 字段
3. 读取 `agent_cwd` 字段（项目路径）
4. 直接访问 `<agent_cwd>/.claude/sessions/<main_session>.jsonl`

**快速访问**:
```bash
# 如果 project_path = D:/desktop/软件开发/agents-hub
# session_id = f8c2c14e-9bef-4f97-b3c1-17227c0c49b9
cat "D:/desktop/软件开发/agents-hub/.claude/sessions/f8c2c14e-9bef-4f97-b3c1-17227c0c49b9.jsonl"
```

### 1.2 群聊目录结构说明

**群聊根目录**: `local_data/teams/<project_name_encoded>/<group_chat_id>/`

**示例**: `local_data/teams/D-desktop-软件开发-agents-hub/d7fa3e44-27fe-4eee-99c3-b81822ba1343/`

#### 目录结构

```
d7fa3e44-27fe-4eee-99c3-b81822ba1343/
├── agent_calls.jsonl              # Agent 任务调用记录（历史所有调用）
├── agent_calls.log                # Agent 任务调用日志（当前运行时）
├── agent_members/                 # 成员信息目录
│   ├── manager/
│   │   └── agent_member.json      # Manager agent 元数据
│   ├── codex/
│   │   └── agent_member.json      # Codex agent 元数据
│   └── claude/
│       └── agent_member.json      # Claude agent 元数据
├── compact_records.jsonl          # 上下文压缩记录
├── group_chat.json                # 群聊元数据（创建时间、成员列表等）
├── messages.jsonl                 # 群聊消息历史（所有消息）
├── pinned_messages.jsonl          # 置顶消息列表
└── tasks.jsonl                    # 任务列表
```

#### 关键文件说明

##### 1. `agent_member.json`
**用途**: 存储 agent 的运行时状态和会话信息

**关键字段**:
- `main_session`: 主会话 ID（用于定位原始 session 文件）
- `agent_cwd`: agent 工作目录（Claude 平台需要）
- `status`: agent 状态（`idle`, `busy`, `error` 等）
- `context_usage`: 上下文使用量（K tokens）
- `context_window`: 上下文窗口大小（K tokens）
- `last_active_at`: 最后活跃时间

**定位 session 文件的关键字段**:
```json
{
  "main_session": "019ee47a-9ef6-7062-bf2d-ec9b9861583f",
  "agent_cwd": "D:/desktop/软件开发/agents-hub"
}
```

##### 2. `agent_calls.jsonl`
**用途**: 记录所有 agent 任务调用的完整历史

**关键字段**:
- `call_id`: 任务唯一标识（用于追踪任务）
- `sender`: 发送者 agent 名称
- `receiver`: 接收者 agent 名称
- `status`: 任务状态（`pending`, `running`, `completed`, `failed`）
- `created_at`: 创建时间
- `completed_at`: 完成时间
- `error`: 错误信息（如果失败）

**Debug 用途**:
- 查找卡住的任务（`status: running` 但长时间未完成）
- 查看任务的完整生命周期
- 定位任务失败的原因

**查找示例**:
```bash
# 查找所有 running 状态的任务
grep '"status":"running"' agent_calls.jsonl

# 查找特定 call_id 的任务
grep 'be304726' agent_calls.jsonl
```

##### 3. `messages.jsonl`
**用途**: 存储群聊中所有消息的历史记录

**关键字段**:
- `message_id`: 消息唯一标识
- `send_from`: 发送者
- `send_to`: 接收者
- `content`: 消息内容
- `call_id`: 关联的任务 ID（如果是任务消息）
- `message_type`: 消息类型（`USER_INPUT`, `TASK`, `NOTIFICATION` 等）
- `timestamp`: 时间戳

**Debug 用途**:
- 查看消息是否成功保存
- 追踪消息的发送和接收流程
- 定位消息丢失问题

##### 4. `agent_calls.log`
**用途**: 实时任务日志（运行时写入，重启后清空）

**Debug 用途**:
- 查看任务执行的详细日志
- 追踪任务状态变化
- 定位任务执行过程中的问题

**注意**: 重启后此文件会被清空，历史记录在 `agent_calls.jsonl` 中。

##### 5. `compact_records.jsonl`
**用途**: 记录上下文压缩操作的历史

**关键字段**:
- `agent_name`: 被压缩的 agent
- `old_session`: 压缩前的 session ID
- `new_session`: 压缩后的 session ID
- `timestamp`: 压缩时间

**Debug 用途**:
- 追踪 session 的压缩历史
- 定位压缩操作导致的问题

## 2. 系统 Debug 方法论

### 核心三步法

```
1. 查看 Spec/Flow 文档  →  理解设计意图和数据流
2. 查看日志记录        →  定位卡住的区间
3. 增加日志（如需要）  →  缩小问题范围
```

### 2.1 第一步：查看 Spec 和 Flow 文档

**目的**: 快速了解当前功能的设计意图和数据流转路径

#### 查看 Spec（技术契约）
1. **位置**: `docs/specs/index.md`
2. **作用**: 理解模块的业务意图、对外接口、状态机规则、设计决策
3. **查找方式**: 根据问题涉及的模块查找对应的 spec

**示例**:
```bash
# 如果问题涉及消息流转
cat docs/specs/2026-06-05-message-flow-and-persistence.md

# 如果问题涉及 Agent 执行
cat docs/specs/2026-05-31-core-agent-orchestration.md
```

#### 查看 Flow（数据流文档）
1. **位置**: `docs/flows/index.md`
2. **作用**: 提供完整的调用链路和函数位置导航
3. **查找方式**: 根据问题场景查找对应的 flow

**示例**:
```bash
# 如果问题涉及 AgentCall 生命周期
cat docs/flows/agent-call-lifecycle.md

# 如果问题涉及消息处理
cat docs/flows/message-lifecycle.md
```

**关键信息**:
- 完整的函数调用链路（从入口到出口）
- 每个函数的文件位置和行号
- 关键状态变化的触发点

### 2.2 第二步：查看日志记录

**目的**: 判断问题发生的区间和卡住的位置

#### 主日志文件
- **位置**: `local_data/logs/agents_hub.log`
- **作用**: 记录整个系统的运行日志

#### 日志分析方法

##### 1. 确定应该打印的日志
- 阅读相关代码，列出关键路径上应该打印的所有日志
- 特别关注状态变化、异步操作、进程管理等关键点

**示例**（CodexExecutor.execute 的关键日志）:
```python
# 应该打印的日志（按执行顺序）
1. logger.info("Codex CLI: %s", " ".join(cmd))           # 67 行
2. logger.debug("[CodexExecutor] 进程已启动: pid=%s")    # 84 行
3. logger.debug("[CodexExecutor] read 等待: ...")       # 96 行（循环）
4. logger.debug("[CodexExecutor] read 返回空 (EOF)")    # 104 行
5. logger.debug("[CodexExecutor] stdout 流结束")        # 124 行
6. logger.debug("[CodexExecutor] 等待进程退出")         # 132 行
7. logger.debug("[CodexExecutor] 进程已退出")           # 138 行
```

##### 2. 搜索实际打印的日志
- 使用 `grep` 搜索关键字段（如 `call_id`, `session_id`, `pid`）
- 按时间顺序排列，找出最后一条日志

**示例**:
```bash
# 搜索特定任务的日志
grep "be304726" local_data/logs/agents_hub.log

# 搜索特定进程的日志
grep "pid=40712" local_data/logs/agents_hub.log

# 搜索某个时间段的日志
grep "2026-06-20 18:18" local_data/logs/agents_hub.log | grep codex
```

##### 3. 对比应该打印 vs 实际打印
- 找出**没有打印的日志**，这就是卡住的位置
- 分析卡住位置的代码逻辑

**示例分析**:
```
✅ 已打印: [CodexExecutor] 等待进程退出 (18:18:19)
❌ 未打印: [CodexExecutor] 进程已退出

结论: 卡在 await process.wait() 这一行（第 136 行）
```

#### 日志级别说明
- `DEBUG`: 详细的调试信息（需要在代码中设置 `logging.DEBUG`）
- `INFO`: 关键操作记录
- `WARNING`: 警告信息
- `ERROR`: 错误信息（包含堆栈）

**如果看不到 DEBUG 日志**:
- 检查 `agents_hub/utils/__init__.py` 中的 `get_logger()` 配置
- 确认日志级别是否正确设置

### 2.3 第三步：增加日志（如果找不到问题）

**目的**: 在关键路径上添加更多日志，缩小问题范围

#### 添加日志的原则

1. **在关键路径上添加**
   - 函数入口和出口
   - 状态变化点
   - 异步操作的前后
   - 条件分支的判断结果

2. **日志内容要包含上下文**
   - 关键变量的值（如 `call_id`, `session_id`, `pid`）
   - 操作类型（如 "开始", "完成", "失败"）
   - 当前状态

3. **使用合适的日志级别**
   - 调试过程：`DEBUG`
   - 关键操作：`INFO`
   - 异常情况：`ERROR`

#### 示例：添加日志

**原代码**:
```python
await process.wait()
```

**添加日志后**:
```python
logger.debug(
    "[CodexExecutor] 等待进程退出: pid=%s, session_id=%s",
    process.pid,
    session_id,
)
await process.wait()
logger.debug(
    "[CodexExecutor] 进程已退出: pid=%s, session_id=%s, returncode=%s",
    process.pid,
    session_id,
    process.returncode,
)
```

#### 重启服务观察新日志
```bash
# 重启后端服务
python -m agents_hub.api.app

# 实时查看日志
tail -f local_data/logs/agents_hub.log
```

### 2.4 第四步：记录 Bug

**目的**: 将问题、排查过程、修复方案记录下来，便于未来复用

#### Bug 文档位置
- **路径**: `docs/history-bugs/`
- **命名**: `YYYY-MM-DD-<problem-description>.md`

#### Bug 文档模板

参考现有的 bug 文档（如 `2026-06-20-codex-process-wait-blocking.md`），包含以下内容：

1. **Bug 简述**
   - 问题现象
   - 出现频率
   - 严重程度

2. **典型案例**
   - Case ID
   - 时间线
   - 关键日志

3. **复用场景**
   - 哪些地方可能出现类似问题
   - 触发条件

4. **代码位置**
   - 问题位置（文件 + 行号）
   - 上游传播链路

5. **发生原因**
   - 根因分析
   - 为什么会发生

6. **解决方案**
   - 推荐方案
   - 修复代码
   - 影响范围

7. **验证方式**
   - 如何验证修复
   - 测试用例

8. **经验教训**
   - 从这个 bug 中学到的教训
   - 未来如何避免

#### 更新索引文件
在 `docs/history-bugs/index.md` 中添加新 bug 的索引条目。

## 3. 常见问题排查场景

### 3.1 任务一直卡在 running 状态

**症状**:
- Agent Call 长时间处于 `running` 状态
- 消息无法显示在群聊中
- 前端显示 agent 一直在执行

**排查步骤**:

1. **找到卡住的任务**
   ```bash
   grep '"status":"running"' local_data/teams/<project>/<group_id>/agent_calls.jsonl
   ```

2. **查看任务的日志**
   ```bash
   # 使用 call_id 搜索
   grep "<call_id>" local_data/logs/agents_hub.log
   ```

3. **定位卡住的位置**
   - 查看最后一条日志在哪里
   - 对比代码中应该打印的日志
   - 确定卡在哪个函数/哪一行

4. **查看 session 文件**
   - 从 `agent_member.json` 获取 `main_session`
   - 查看 session 文件的最后几行
   - 确认 CLI 是否已经完成

5. **检查进程状态**（如果是进程问题）
   ```bash
   # Windows
   tasklist | findstr <pid>
   
   # Linux/Mac
   ps aux | grep <pid>
   ```

**常见原因**:
- 进程 `wait()` 阻塞（参考 `2026-06-20-codex-process-wait-blocking.md`）
- 异常未被捕获和记录
- 死锁或资源竞争

### 3.2 消息丢失或不显示

**症状**:
- 发送消息后，群聊中看不到
- Agent 的回复消息没有保存

**排查步骤**:

1. **检查消息是否发送**
   ```bash
   grep "<message_content>" local_data/teams/<project>/<group_id>/messages.jsonl
   ```

2. **检查消息路由**
   - 查看 `docs/flows/message-lifecycle.md`
   - 搜索日志中的消息投递记录
   ```bash
   grep "消息投递" local_data/logs/agents_hub.log | grep "<call_id>"
   ```

3. **检查消息类型**
   - `NOTIFICATION` 消息可能不被保存（参考 `2026-06-19-notification-message-not-saved.md`）
   - 确认消息类型是否正确

4. **检查 WebSocket 连接**
   - 前端是否收到 refresh 信号
   - WebSocket 是否断连

**常见原因**:
- 消息类型处理逻辑缺失
- WebSocket 断连导致前端未刷新
- 消息保存逻辑的条件判断错误

### 3.3 Session 找不到或串台

**症状**:
- 报错 "session not found"
- 多个 agent 的 `main_session` 相同
- Resume 时报 "no rollout found"

**排查步骤**:

1. **检查 agent_member.json**
   ```bash
   cat local_data/teams/<project>/<group_id>/agent_members/<agent>/agent_member.json
   ```

2. **搜索 session 文件**
   - Codex: 部分匹配搜索
   - Claude: 精确匹配搜索

3. **检查并发问题**
   - 是否有多个 agent 并发初始化
   - Parser 是否是共享单例（参考 `2026-06-15-parser-concurrency-race-condition.md`）

4. **检查压缩记录**
   ```bash
   cat local_data/teams/<project>/<group_id>/compact_records.jsonl
   ```

**常见原因**:
- Parser 并发竞态导致 session_id 串台
- Session 文件路径错误
- 上下文压缩后旧 session 被删除

### 3.4 Agent 状态异常

**症状**:
- Agent 一直显示 `busy` 但没有任务在执行
- Agent 状态显示 `error` 但不知道错误原因

**排查步骤**:

1. **检查 agent_member.json**
   ```bash
   cat local_data/teams/<project>/<group_id>/agent_members/<agent>/agent_member.json
   ```

2. **查看状态变化日志**
   ```bash
   grep "Agent <agent> status" local_data/logs/agents_hub.log
   ```

3. **检查是否有残留任务**
   ```bash
   grep '"receiver":"<agent>","status":"running"' agent_calls.jsonl
   ```

4. **查看错误信息**
   - 在 `agent_member.json` 中查看 `error_message` 字段
   - 在日志中搜索异常堆栈

**常见原因**:
- 任务未正确闭环导致状态未更新
- 异常未被捕获导致状态未回退
- 状态更新逻辑的竞态条件

## 4. 调试工具和技巧

### 4.1 日志搜索技巧

```bash
# 按时间过滤
grep "2026-06-20 18:1[0-9]" agents_hub.log

# 多个关键字 AND 搜索
grep "codex" agents_hub.log | grep "be304726"

# 查看上下文（前后各 5 行）
grep -C 5 "关键字" agents_hub.log

# 统计出现次数
grep -c "进程已退出" agents_hub.log

# 只显示匹配的部分
grep -o "pid=[0-9]*" agents_hub.log
```

### 4.2 JSONL 文件查询

```bash
# 格式化单行 JSON（需要 jq）
tail -1 messages.jsonl | jq .

# 提取特定字段
cat agent_calls.jsonl | jq -r 'select(.status=="running") | .call_id'

# 按条件过滤
cat messages.jsonl | jq 'select(.send_from=="manager")'
```

### 4.3 实时监控

```bash
# 实时查看日志
tail -f local_data/logs/agents_hub.log

# 实时查看并过滤
tail -f local_data/logs/agents_hub.log | grep "ERROR"

# 实时查看 agent_calls.log
tail -f local_data/teams/<project>/<group_id>/agent_calls.log
```

### 4.4 进程管理

```bash
# 查看进程
ps aux | grep python
ps aux | grep codex
ps aux | grep claude

# 查看进程树
pstree -p <pid>

# 强制终止进程
kill -9 <pid>
```

## 5. 相关资源

### 5.1 核心文档
- **架构文档**: `docs/ARCHITECTURE.md`
- **Spec 索引**: `docs/specs/index.md`
- **Flow 索引**: `docs/flows/index.md`
- **Bug 索引**: `docs/history-bugs/index.md`
- **编码规则**: `docs/coding-rules/index.md`

### 5.2 关键代码位置
- **Agent 执行**: `agents_hub/core/agent/base_agent.py`
- **消息路由**: `agents_hub/core/communication/message_router.py`
- **GroupChat 编排**: `agents_hub/core/orchestration/group_chat.py`
- **AgentBridge**: `agents_hub/agent_bridge/bridge.py`
- **Codex Executor**: `agents_hub/agent_bridge/executors/codex.py`
- **Claude Executor**: `agents_hub/agent_bridge/executors/claude.py`

### 5.3 常用命令

```bash
# 启动后端
python -m agents_hub.api.app

# 查看日志
tail -f local_data/logs/agents_hub.log

# 搜索 bug 记录
grep -r "关键字" docs/history-bugs/

# 运行测试
python -m pytest tests/ -v
```

## 6. 总结

### Debug 三步法
1. **读文档**（Spec + Flow）→ 理解设计和数据流
2. **看日志**（应该打印 vs 实际打印）→ 定位卡住位置
3. **加日志**（如果找不到）→ 缩小问题范围

### 记住
- 日志是你最好的朋友
- 文档是你的地图
- Bug 记录是你的经验库

### 最重要的原则
- 不要猜测，用日志证明
- 不要假设，用代码验证
- 不要忘记，用文档记录
