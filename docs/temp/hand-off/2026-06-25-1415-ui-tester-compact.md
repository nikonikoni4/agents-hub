# Context Compact - ui-tester - 2026-06-25T14:15:59.436517

## 原 Session
- session_id: 5321dcd6-2e80-4282-95af-8963327e40d9
- context_usage: 0K tokens

## 摘要
## 工作上下文总结

### 1. 已完成的工作
- 刚被引入团队，尚未执行具体任务

### 2. 当前状态
- 空闲，等待 manager 分配任务

### 3. 核心职责
前端 UI 测试专家，负责：
- **UI 截图**：Playwright 截图前端界面
- **功能验证**：测试前端功能是否正常
- **行为调试**：调试 UI 交互，捕获浏览器日志
- **视觉检查**：对比 UI 变化，验证优化效果

### 4. 工具与方法
- 使用 `webapp-testing` 技能进行 Playwright 自动化测试
- Mock 数据：修改 `frontend/.env.development` 开启 Mock 模式
- 脚本组织：`scripts/webapp-test/[模块名]/`
- 配置文件：`config.py`、`utils.py`

### 5. 重要约束
- **headless 模式**：必须使用无头浏览器
- **等待加载**：截图前等待 networkidle
- **Mock 位置**：Mock 数据必须放在 API 层（`src/core/api/`），使用 `mockableRequest` 包装
- **不可变性**：Mock 数据必须 `const`
- **阻塞反馈**：遇到阻塞立即反馈，不死磕

### 6. 项目上下文
- 项目：Agents Hub 多 Agent 协作平台
- 前端位置：`frontend/`，使用 Vite
- 团队：manager、PRD、architect、通用执行助手、审查助手、ui-designer、ui-tester（我）

---

**总结**：等待 manager 分配具体 UI 测试任务。

## 新 Session
- session_id: c386edb5-03b9-46dd-9f19-e943aa84690b
