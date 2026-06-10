## ARCHITECTURE.md 一致性检查报告
- 检查日期：2026-06-10

### 一致的部分

1. **后端目录结构**：文档描述的主要目录（core/、mcp/、api/、realtime/、skills/、teams/、agent_bridge/、roles/、config/、utils/）均存在
2. **Core 层分层结构**：foundation/、communication/、context/、agent/、orchestration/ 五个子目录结构正确
3. **API 层结构**：routes/、schemas/、services/、websocket/ 子目录结构正确
4. **Agent Bridge 结构**：executors/、parsers/、docker/ 子目录结构正确
5. **前端目录结构**：core/、features/、shared/、layouts/ 和 App.tsx 结构正确
6. **各层导出的类和模块**：文档中提到的核心类（MessageRouter、AgentCallManager、GroupChatContext、Agent、GroupChat 等）均存在

### 不一致的部分

#### 1. Foundation 层"零依赖"声明违反
- **位置**：Core 层分层架构 → 各层职责说明 → foundation/
- **文档描述**：foundation/ 是基础层，**零依赖**
- **实际情况**：`foundation/__init__.py` 导入了：
  - `agents_hub.exceptions.StateError`
  - `agents_hub.roles.Role` 和 `agents_hub.roles.RoleConfig`
- **严重程度**：Critical
- **建议修复**：将 `StateError` 移至 foundation/exceptions.py，将 Role 相关类移至 foundation 或重新设计依赖关系

#### 2. Context 层依赖超出声明
- **位置**：Core 层分层架构 → 依赖关系图
- **文档描述**：context/ 只依赖 foundation
- **实际情况**：`context/group_chat_context.py` 导入了 `agents_hub.agent_bridge`
- **严重程度**：Warning
- **建议修复**：通过接口或依赖注入解耦 context 对 agent_bridge 的直接依赖

#### 3. Agent 层依赖 context 违反设计原则
- **位置**：Core 层分层架构 → 关键设计原则
- **文档描述**：agent/ 依赖 foundation + communication，**不依赖 context**
- **实际情况**：`agent/base_agent.py` 导入了 `agents_hub.core.context`
- **严重程度**：Critical
- **建议修复**：重新设计 Agent 类，通过接口或组合模式避免直接依赖 context

#### 4. 文档未提及的外部依赖
- **位置**：整个文档
- **文档描述**：未提及对 `agents_hub.utils`、`agents_hub.config`、`agents_hub.roles`、`agents_hub.realtime` 的依赖
- **实际情况**：
  - communication 层依赖 `agents_hub.utils.logger`
  - orchestration 层依赖 `agents_hub.config`、`agents_hub.roles`、`agents_hub.realtime`
- **严重程度**：Warning
- **建议修复**：在文档中补充这些依赖关系说明

#### 5. 根目录 exceptions.py 未在目录结构中体现
- **位置**：后端架构详解 → 目录结构
- **文档描述**：目录结构中列出了 `exceptions.py`
- **实际情况**：文件存在，但文档的树形结构中位置不明确
- **严重程度**：Info
- **建议修复**：在目录结构图中明确标注位置

### 文档缺失覆盖

#### 1. channels 模块（重要遗漏）
- **代码位置**：`agents_hub/channels/`
- **包含内容**：微信渠道实现（wechat/channel.py、wechat/client.py、wechat/message.py 等）
- **严重程度**：Critical
- **建议**：在目录结构和模块说明中添加 channels 模块

#### 2. core/utils 模块
- **代码位置**：`agents_hub/core/utils/`
- **包含内容**：markdown_injector.py、path_utils.py
- **严重程度**：Warning
- **建议**：在 Core 层结构中添加 utils 说明

#### 3. 前端额外目录
- **代码位置**：`frontend/src/styles/`、`frontend/src/tests/`
- **严重程度**：Info
- **建议**：在前端目录结构中补充

### 总结

**一致性评分**：65/100

**主要问题**：
1. **Core 层依赖关系严重违反设计原则**（Critical）：foundation 不是零依赖，agent 依赖了 context，context 依赖了 agent_bridge
2. **重要模块遗漏**（Critical）：channels 模块完全未在文档中体现
3. **依赖关系描述不完整**（Warning）：多个层对 utils、config、roles 等模块的依赖未说明

**建议优先修复顺序**：
1. 补充 channels 模块到架构文档
2. 重新审视 Core 层的依赖关系设计，要么调整代码使其符合文档描述，要么更新文档反映实际设计
3. 补充所有外部依赖关系的说明
