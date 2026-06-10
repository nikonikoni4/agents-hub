现在我有了完整的变更内容。让我进行详细的代码审查。

## 代码审查报告
- **审查范围**：最近 5 次提交（`d61970c` → `d2f9ab8`）+ 未提交的工作区变更
- **审查日期**：2026-06-10

---

### 发现的问题

#### Critical

**1. `file_snapshot.py` — `git_diff_range` 正则验证被过度放宽**
`agents_hub/core/foundation/file_snapshot.py:44-47`

```python
# 旧：只接受 SHA-1/SHA-256 格式
pattern = r"^[0-9a-f]{7,64}\.\.[0-9a-f]{7,64}$"
# 新：接受任意 git ref
pattern = r"^[a-zA-Z0-9\-_/.~^:]+\.\.[a-zA-Z0-9\-_/.~^:]+$"
```

虽然注释说"防止命令注入"，但新正则允许的字符集（`/`, `~`, `^`, `:`）非常宽泛。虽然仍限制在 `subprocess.run` 的参数列表中（非 shell 模式），不会直接导致命令注入，但应考虑：
- 该正则允许 `HEAD~999999..HEAD` 这类可能耗时巨大的 ref 范围
- 建议添加长度上限或限制最大 ref 层数

**2. `commander.py` — 会话内存泄漏，无过期清理机制**
`agents_hub/channels/wechat/commander.py:41`

```python
self._sessions: dict[str, UserSession] = {}
```

`Commander` 是长生命周期单例，`_sessions` 字典只增不减。微信用户量增长后会导致内存持续膨胀。建议添加 TTL 过期清理或 LRU 淘汰机制。

**3. `commander.py` — `_ask_assistant` 和 `_forward_to_agent` 存在代码重复**
`agents_hub/channels/wechat/commander.py:84-95` 和 `commander.py:96-111`

两个方法几乎完全相同（都是流式收集 text_delta），违反 DRY 原则。应提取为公共方法。

#### Warning

**4. `app.py` — `wechat_task.result()` 未处理异常**
`agents_hub/api/app.py:118`

```python
wechat_channel = wechat_task.result() if wechat_task.done() else None
```

如果 `_start_wechat_channel` 抛出未预期的异常，`wechat_task.result()` 会重新抛出，导致 lifespan 清理阶段崩溃。应包裹 try/except。

**5. `channel.py` — `_is_allowed` 的 `allow_from=["*"]` 设计过于宽松**
`agents_hub/channels/wechat/channel.py:120-124` + `config.py:17`

`WechatConfig` 默认 `allow_from` 为空列表（拒绝所有），但在 `app.py:146` 中创建时传入 `allow_from=["*"]`，即默认允许所有微信用户。对于一个连接到微信的 channel，这存在安全风险——任何用户都可以触发 Agent 执行任务。

**6. `send_message_and_wait` — 消息计数逻辑存在竞态条件**
`agents_hub/api/services/group_chat_service.py:473-530`

```python
before_count = len(group_chat.runtime.get_message_dicts(limit=0))
await self.send_message(...)
# 循环等待...
messages = group_chat.runtime.get_message_dicts(limit=0)
new_msgs = messages[before_count:]
```

如果在 `get_message_dicts` 和 `send_message` 之间有其他消息写入，`before_count` 可能不准确。此外 `limit=0` 的语义需要确认（是否返回全部消息）。

**7. `auth.py` — QR 登录轮询没有退避策略**
`agents_hub/channels/wechat/auth.py:98`

```python
await asyncio.sleep(1)
```

固定 1 秒轮询，如果网络状况不佳或 API 限流，可能触发过多请求。建议添加指数退避或至少增加间隔。

**8. `client.py` — `BASE_INFO` 硬编码为所有 POST 请求注入**
`agents_hub/channels/wechat/client.py:48-49`

```python
if "base_info" not in payload:
    payload["base_info"] = BASE_INFO
```

并非所有 API 都需要 `base_info`，无条件注入可能导致某些 API 行为异常。建议只在明确需要的请求中注入。

**9. `role.py` — skill 名称强制使用文件夹名可能破坏已有配置**
`agents_hub/roles/role.py:181`

```python
# 旧：name = frontmatter.get("name", skill_dir.name)
# 新：name = skill_dir.name
```

忽略 frontmatter 中的 `name` 字段。如果现有 skill 的 frontmatter `name` 与文件夹名不一致，会导致引用该 skill 的配置失效。这是一个 breaking change。

#### Suggestion

**10. 未提交变更主要是格式化（formatting-only）**

未提交的变更中，`app.py`、`client.py`、`channel.py`、`exceptions.py`、`message.py`、`base_agent.py`、`group_chat_runtime.py`、`dependencies.py` 的变更几乎全部是代码格式化（换行、缩进调整）。这些应该由 `ruff format` 或类似的自动格式化工具统一处理，而非手动修改，以减少 diff 噪音。

**11. `README.md` 引用了 `gifs/` 目录下的 GIF 文件**

未提交变更中 README 引用了多个 GIF 文件（如 `gifs/agentshub助手.gif`）。需确认这些文件是否已提交到仓库，否则 README 中会出现 broken images。

**12. `video2gif.py` — `palette.png` 临时文件写入工作目录**
`scripts/video2gif.py:29-30`

```python
"palette.png",
```

临时调色板文件写入当前工作目录而非临时目录。虽然 `finally` 中有清理，但如果进程被中断，文件会残留。建议使用 `tempfile.NamedTemporaryFile`。

**13. `commander.py` — `_dispatch_command` 中 lambda 闭包捕获问题**

```python
"/agent": lambda: self._cmd_agent(user_id, arg),
```

这些 lambda 实际上没有闭包问题（`user_id` 和 `arg` 在同一作用域），但使用 `functools.partial` 会更清晰。

---

### 总结

**整体评价**：这批提交新增了微信 channel 模块和前端 Docker 确认对话框，功能完整度较好。主要问题集中在：

1. **安全**：微信 channel 默认 `allow_from=["*"]` 开放所有用户，需评估是否为预期行为
2. **内存**：`Commander._sessions` 无清理机制，长期运行会泄漏
3. **可靠性**：`send_message_and_wait` 存在竞态条件，QR 登录无退避策略
4. **Breaking change**：skill 名称忽略 frontmatter `name` 字段，可能影响已有配置

**建议优先修复**：
1. `Commander._sessions` 添加 TTL 过期机制
2. 确认 `allow_from=["*"]` 是否为预期默认值
3. 为 `_start_wechat_channel` 的 result() 调用添加异常保护
