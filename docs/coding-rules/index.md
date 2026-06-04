## 后端编码风格规范
 - updated_at: 2026-05-27
 - path: docs/coding-rules/backend-style.md
 - 触发规则：编写后端代码时，需要创建或选择数据类型文件（types.py/models.py/schemas.py）,需要编写错误处理相关内容时
 - 内容摘要：定义数据类型文件的命名规范，明确 types.py（跨模块共享基础类型）、models.py（模块内数据模型）、schemas.py（配置验证）的使用场景和判断标准。明确错误处理的编写规范

## core runtime 边界规则
 - updated_at: 2026-06-04
 - path: docs/coding-rules/core-runtime-boundary.md
 - 触发规则：修改 core/orchestration、core/context、MCP tool、API service 中的群聊状态读取或消息流转代码时
 - 内容摘要：规定 GroupChatManager 必须通过 GroupChat.runtime 获取内存状态，禁止绕过 runtime 读写 repository；统一 user 身份判断、AgentCall 闭环和群聊公开发言边界。
