# Code Review Report

**审查范围**: 当前未提交的所有修改（3 个功能点）
**审查时间**: 2026-06-28T19:00:00+08:00
**变更文件**: 8 个代码文件 + 若干文档 key_function 行号同步

## 变更摘要

| 功能 | 文件 | 说明 |
|------|------|------|
| @bot name 过滤 | `channel.py`, `config.py`, `config/config.py`, `role_manager.py` | 注册飞书机器人名为保留角色名；on_message 中过滤行首 @bot_name |
| chat ID 安全泄露 | `channel.py`, `prompt_file.py` | send_to_feishu 中正则过滤 oc_xxx 和 Markdown 格式；提示词安全约束重组 |
| cwd 参数透传 | `server.py`, `service.py`, `prompt_file.py`, `docs/specs/2026-06-27-feishu-admin-mcp.md` | MCP create_single_chat → Service → CreateSingleChatRequest 链路增加 cwd 参数 |

## 审查结果

Found 3 issues:

### Issue 1: 内联 `import re` 重复导入

- **类型**: Code Quality
- **置信度**: 85
- **位置**: `agents_hub/channels/feishu/channel.py:267` 和 `:344`
- **详情**: `on_message()` 和 `send_to_feishu()` 方法内各自 `import re`，而不是在文件顶部导入。`re` 是新增代码引入的依赖，应统一放在文件顶部。
- **建议**: 移除两处内联 `import re`，在文件顶部添加 `import re`

### ~~Issue 2: Markdown 内联代码过滤删除内容~~（已确认：设计意图）

- **类型**: ~~Security / Code Quality~~ → 已确认
- **状态**: 有意为之。反引号内内容被删除是预期行为——飞书不渲染 Markdown 格式，内联代码块显示为原始文本会造成视觉混乱。提示词已要求助手不使用 Markdown，此过滤为防御性兜底。

### ~~Issue 3: @bot_name 过滤仅匹配行首~~（已确认：设计意图）

- **类型**: ~~Code Quality~~ → 已确认
- **状态**: 设计如此。`^` 锚点限定行首匹配，避免误删消息正文中出现的机器人名字。此限制已记录到 `docs/known-constraints/feishu-bot-name-filter.md`。

## 正向确认

以下方面审查后无问题：

1. **cwd 参数透传链路完整** — MCP → Service → CreateSingleChatRequest → SingleChatManager 调用链全部正确传递 `cwd`，底层已有 `cwd or agent_info.cwd or Path.cwd()` 回退逻辑
2. **RoleManager.reserved_role_names** — 类级别 `set` 设计合理，多实例共享，`bot_names` 去重由 set 天然保证
3. **chat ID 过滤** — `oc_[a-zA-Z0-9]+` 正则可覆盖当前飞书 chat_id 格式，替换为 "[已隐藏]" 而非空字符串是好的 UX 选择
4. **Markdown 粗体/斜体正则顺序** — `**` 先于 `*` 处理，避免 `\*(.+?)\*` 意外匹配 `**` 的部分
5. **提示词 cwd 确认流程** — 工作流程第 5 步要求先问用户确认 cwd 再调用工具，UX 合理
