## 后端编码风格规范
 - updated_at: 2026-05-27
 - path: docs/coding-rules/backend-style.md
 - 触发规则：编写后端代码时，需要创建或选择数据类型文件（types.py/models.py/schemas.py）,需要编写错误处理相关内容时
 - 内容摘要：定义数据类型文件的命名规范，明确 types.py（跨模块共享基础类型）、models.py（模块内数据模型）、schemas.py（配置验证）的使用场景和判断标准。明确错误处理的编写规范

<<<<<<< HEAD
<<<<<<< HEAD
## core runtime 边界规则
 - updated_at: 2026-06-04
 - path: docs/coding-rules/core-runtime-boundary.md
 - 触发规则：修改 core/orchestration、core/context、MCP tool、API service 中的群聊状态读取或消息流转代码时
 - 内容摘要：规定 GroupChatManager 必须通过 GroupChat.runtime 获取内存状态，禁止绕过 runtime 读写 repository；统一 user 身份判断、AgentCall 闭环和群聊公开发言边界。
## 前端样式与颜色层级规则
 - updated_at: 2026-06-05
 - path: docs/coding-rules/frontend-style-layers.md
 - 触发规则：编写前端组件样式时，特别是涉及背景色、容器、卡片等布局元素
 - 内容摘要：定义三层颜色关系（底色层、容器层、卡片层），明确 CSS 变量使用规范，禁止硬编码颜色和跳层使用，确保全局视觉风格统一

## 前端测试文件放置规范
 - updated_at: 2026-06-04
 - path: frontend/CLAUDE.md（"测试文件放置规则"章节）
 - 触发规则：编写前端测试代码时
 - 内容摘要：测试文件必须共置在源码旁边（`xxx.test.ts`），禁止集中放 `tests/` 目录或 `__tests__/` 子目录。全局 setup 和跨模块集成测试除外

