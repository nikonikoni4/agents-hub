# 任务报告

## 基本信息
- **任务名称**：AI 完成任务后的文件/diff 组件
- **Work Tree**：`.claude/worktrees/task-3-file-diff`
- **分支名**：`task-3-file-diff`
- **冲突等级**：中
- **可并行任务**：无（依赖任务 1 完成）

## 任务目标
当 Agent 完成代码工作后，发送的消息应包含修改的文件地址和 diff 信息。前端消息下方以组件形式展示修改的文件列表，支持：
- 显示修改的文件地址
- 点击可以预览文件内容
- 点击可以查看 diff
- 组件以卡片形式呈现在消息气泡下方

## 可能修改的文件

### 后端
- `agents_hub/core/foundation/message.py`：AgentMessage 增加文件元数据字段（modified_files、diff_summary）
- `agents_hub/api/schemas/group_chats.py`：MessageInfo schema 增加文件相关字段
- `agents_hub/api/services/group_chat_service.py`：消息保存时处理文件元数据
- `agents_hub/core/agent/base_agent.py`：Agent 完成任务后自动附加文件信息（可能）

### 前端
- `frontend/src/shared/types/api-schemas.ts`：新增文件元数据类型（ModifiedFile、DiffSummary）
- `frontend/src/shared/types/domain.ts`：可能新增相关 domain 类型
- `frontend/src/layouts/ChatArea/ChatArea.tsx`：MessageBubble 下方增加文件组件展示
- `frontend/src/layouts/ChatArea/ChatArea.module.css`：文件组件样式
- `frontend/src/shared/components/`：可能新增 FileCard、DiffPreview 等组件
- `frontend/src/layouts/RightSidebar/RightSidebar.tsx`：预览和 diff 占位符替换为真实组件
- `frontend/src/core/api/groupChatApi.ts`：获取文件内容/diff 的 API 函数

## 不可变内容
以下文件在本次任务中不应修改：
- `agents_hub/core/communication/agent_call.py`
- `agents_hub/core/communication/agent_call_manager.py`
- `agents_hub/core/communication/task.py`
- `agents_hub/core/communication/task_manager.py`
- `frontend/src/layouts/RightSidebar/AgentCallsPanel.tsx`
- `frontend/src/layouts/RightSidebar/TasksPanel.tsx`

## 依赖关系
- 依赖任务：任务 1（消息模型扩展）
- 被依赖：无
