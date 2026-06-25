# Context Compact - ui-tester - 2026-06-25T14:10:12.036669

## 原 Session
- session_id: 7b289bab-a3a4-437c-9bdb-6bcc6e4ca8f7
- context_usage: 0K tokens

## 摘要
## 工作上下文总结

### 1. 已完成的工作
- 刚刚被引入团队，尚未执行具体任务

### 2. 当前状态
- 空闲状态，等待 manager 分配任务

### 3. 核心职责
作为前端 UI 测试专家，主要工作包括：
- **UI 截图**：使用 Playwright 截图前端界面
- **功能验证**：测试前端功能是否正常
- **行为调试**：调试 UI 交互，捕获浏览器日志
- **视觉检查**：对比 UI 变化，验证优化效果

### 4. 工具与方法
- 使用 `webapp-testing` 技能进行 Playwright 自动化测试
- 需要 Mock 数据时，修改 `frontend/.env.development` 开启 Mock 模式
- 脚本按模块组织到 `scripts/webapp-test/` 目录
- 配置文件：`config.py`、`utils.py`

### 5. 重要约束
- 必须使用 headless 模式运行浏览器
- 截图前等待 networkidle
- Mock 数据必须放在 API 层（`src/core/api/`），使用 `mockableRequest` 包装
- Mock 数据必须 `const` 不可变
- 遇到阻塞立即反馈，不死磕

### 6. 项目上下文
- 这是 Agents Hub 多 Agent 协作平台项目
- 前端在 `frontend/` 目录，使用 Vite
- 当前团队：manager、PRD、architect、通用执行助手、2号通用审查助手、ui-designer、ui-tester

**总结**：等待 manager 分配具体 UI 测试任务。

## 新 Session
- session_id: 5321dcd6-2e80-4282-95af-8963327e40d9
