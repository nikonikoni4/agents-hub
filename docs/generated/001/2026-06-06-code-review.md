## 代码审查报告

- **审查范围**：`feat_front_design` 分支 vs `main` 分支（360 个文件变更）
- **审查日期**：2026-06-06

---

### 发现的问题

#### Critical

| # | 文件 | 问题 |
|---|------|------|
| 1 | `agents_hub/api/routes/group_chat.py:112-164` | **测试端点暴露在生产环境** — `/test/bridge-execute` 和 `/test/subprocess` 两个测试路由没有访问控制，且硬编码了本地路径 `D:\desktop\软件开发\agents-hub\...`，应删除或移到独立的测试 router 并加环境守卫 |
| 2 | `agents_hub/api/app.py:107-113` | **开发环境泄露异常详情** — `is_dev` 时返回 `str(exc)` 可能泄露内部路径、堆栈等敏感信息，建议只返回 error type，详细信息仅写日志 |
| 3 | `frontend/src/shared/components/MarkdownRenderer/MarkdownRenderer.tsx:12` | **XSS 风险** — `ReactMarkdown` 默认不 sanitize HTML，若消息内容含恶意 `<script>` 或事件属性可能被执行，需添加 `rehype-sanitize` |

#### Warning

| # | 文件 | 问题 |
|---|------|------|
| 4 | `agents_hub/core/orchestration/group_chat_manager.py:28-42` | **单例线程安全** — `__new__` + `_initialized` 模式在多线程环境下存在竞态（两个线程同时进入 `__new__`），应加锁或使用模块级实例 |
| 5 | `agents_hub/core/context/group_chat_runtime.py:287` | **生产代码中的 assert** — `assert session.messages == ...` 在 Python `-O` 模式下会被跳过，且不应在生产代码中断言内部一致性 |
| 6 | `agents_hub/mcp/server.py:30-44` | **Monkey-patch 第三方库** — 直接修改 `JSONRPCMessage.model_dump_json` 可能在库升级时失效，且影响全局所有实例，建议使用自定义 serializer |
| 7 | `tests/api/services/test_group_chat_service.py:540` | **测试未同步** — 测试仍使用 `offset=0` 参数，但 service 已改为 `before` 游标分页，测试应已失败或需要更新 |
| 8 | `agents_hub/core/agent/base_agent.py:51-56` | **property 重复计算** — `agent_token` 和 `agent_cwd` 每次访问都从 `group_chat_context` 查询，高频调用时可能有性能影响 |

#### Suggestion

| # | 文件 | 问题 |
|---|------|------|
| 9 | 多个后端文件 | **日志过于密集** — 大量 `logger.debug` 在消息处理热路径上（`_process_message`、`send_message` 等），建议用 `logging.DEBUG` 级别控制，或在高频路径减少日志量 |
| 10 | `agents_hub/core/orchestration/group_chat.py:509-543` | **Heartbeat 可配置化** — `_heartbeat_interval` 硬编码 1200 秒，建议从 config 读取 |
| 11 | `frontend/src/layouts/ChatArea/ChatArea.tsx:88-99` | **乐观更新无回滚** — `handleSend` 中本地消息添加后若 API 失败没有移除，用户会看到"已发送"但实际未送达 |
| 12 | `frontend/src/features/chat/hooks/useChatMessages.ts:62-70` | **loadMore 缺少防抖** — 快速滚动可能触发多次 `loadMore`，虽然有 `loadingMore` 守卫，但建议加 debounce |
| 13 | `agents_hub/bootstrap.py:51-72` | **默认角色创建静默失败** — `except Exception` 捕获所有异常只 warning，若数据库/文件系统问题会导致系统启动但缺少 manager 角色 |

---

### 总结

**整体评价**：分支完成了群聊系统的重大功能迭代（游标分页、@mention、heartbeat、单例管理器、前端 UI 重构），代码结构清晰，日志覆盖充分。

**主要风险**：
1. **安全**：测试端点暴露 + Markdown XSS 是必须在合并前修复的问题
2. **稳定性**：单例线程安全 + assert 语句可能在生产环境引发问题
3. **测试**：部分测试用例与实现不同步（offset vs before），需确认测试是否通过

**建议**：
- 合并前至少修复 Critical 1-3
- 删除或隔离测试端点
- 为 MarkdownRenderer 添加 sanitize
- 运行完整测试套件确认测试同步状态
