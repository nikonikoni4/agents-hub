# Windows asyncio subprocess NotImplementedError

**创建时间**: 2026-06-05  
**状态**: 已修复  
**严重程度**: 高（阻塞核心功能）

## 问题描述

在 Windows 平台上创建群聊时，后端返回 409 Conflict。实际错误是 `NotImplementedError`，来自 `asyncio.create_subprocess_exec()` 调用。

### 错误堆栈

```
File "agents_hub\agent_bridge\executors\claude.py", line 41, in execute
    process = await asyncio.create_subprocess_exec(...)
File "asyncio\base_events.py", line 539, in _make_subprocess_transport
    raise NotImplementedError
```

### 表现症状

- 前端创建群聊后，POST /api/v1/group-chats 返回 409 Conflict
- 测试端点显示事件循环类型为 `_WindowsSelectorEventLoop`
- 错误被包装为 `StateError`，导致返回 409 而不是 500

## 根本原因

### 1. 事件循环类型错误

Windows 平台上 asyncio 有两种事件循环：
- **SelectorEventLoop**: 不支持 subprocess 操作（会抛出 NotImplementedError）
- **ProactorEventLoop**: 支持 subprocess 操作

### 2. uvicorn reload 模式问题

使用 `uvicorn.run(..., reload=True)` 时：
1. uvicorn 启动一个主进程
2. 主进程启动子进程加载应用代码
3. 子进程会重置事件循环策略为默认值（SelectorEventLoop）
4. 即使在模块顶部设置了 `WindowsProactorEventLoopPolicy`，子进程也会丢失这个设置

## 解决方案

### 修改位置

`agents_hub/api/app.py`

### 关键修改

1. **在模块顶部设置事件循环策略**（在导入 FastAPI 之前）：

```python
import asyncio
import sys

# Windows: 必须在导入 FastAPI 之前设置 ProactorEventLoop
if sys.platform == "win32":
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
```

2. **禁用 reload 模式**：

```python
if __name__ == "__main__":
    import uvicorn
    # reload=True 会导致子进程重置事件循环策略
    uvicorn.run(app, host="0.0.0.0", port=8099, reload=False)
```

### 验证修复

测试端点返回：
```json
{
  "status": "success",
  "event_loop": "ProactorEventLoop",
  "returncode": "0"
}
```

## 触发条件

- 操作系统：Windows
- Python 版本：3.13.5（可能影响所有 Windows 上的 Python 3.8+）
- uvicorn reload 模式：启用
- 使用场景：任何需要 `asyncio.create_subprocess_exec()` 的操作
  - 群聊创建（需要启动 agent 子进程）
  - Agent 执行（Claude/Codex CLI 调用）

## 相关信息

### Python 版本兼容性

- **Python 3.13 及以下**：需要使用 `set_event_loop_policy()`
- **Python 3.14+**：`set_event_loop_policy()` 已弃用，但 `ProactorEventLoop` 会成为 Windows 默认值

### 弃用警告处理

```python
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### 开发环境建议

如果需要热重载功能，有两个选择：

1. **使用命令行启动**（不推荐，会失去 subprocess 支持）：
   ```bash
   uvicorn agents_hub.api.app:app --reload
   ```

2. **手动重启服务器**（推荐）：
   ```bash
   python -m agents_hub.api.app
   ```

## 参考资料

- [FastAPI + Playwright on Windows: NotImplementedError](https://stackoverflow.com/questions/79630534/fastapi-playwright-on-windows-notimplementederror-due-to-event-loop-incomp)
- [Running an Asyncio Subprocess in FastApi - Issue #4361](https://github.com/tiangolo/fastapi/issues/4361)
- [Python 3.14 Deprecations - Pending removal in 3.16](https://docs.python.org/sv/3/deprecations/pending-removal-in-3.16.html)
- [Uvicorn in Windows kills subprocesses on reload](https://github.com/encode/uvicorn/discussions/2292)

## 相关 Bug

- `2026-06-05-agent-member-info-init-timing.md`: Agent 初始化时序问题
- `2026-06-05-load-group-chat-triggers-agent-execute.md`: GroupChat.load() 触发 agent.execute()

## 经验教训

1. **Windows asyncio 的特殊性**：Windows 平台的事件循环实现与 Unix 系统不同，需要特别注意
2. **uvicorn reload 的限制**：reload 模式通过子进程实现，会重置很多运行时状态
3. **错误包装的隐患**：NotImplementedError 被包装为 StateError，导致返回错误的 HTTP 状态码
4. **模块导入顺序的重要性**：事件循环策略必须在导入 FastAPI 之前设置
5. **前瞻性警告**：虽然当前代码可用，但要注意 Python 3.14+ 的弃用情况
