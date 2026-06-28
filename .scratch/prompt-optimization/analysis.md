# Agent 指令遵循问题分析与解决方案

## 问题描述

Agent 在接收带有明确指令（如 "**必须使用 local-code-review skill**"）的消息时，经常忽略指令，直接用简化流程完成任务。

## 根因分析

### 当前消息结构

```xml
<runtime>
  <type>群聊</type>
  <agent_token>tok_e9a19b7094c43f21fb98f3e38176d0c5</agent_token>
  <group_chat_id>4a3a4cbb-49d9-4efb-a1e8-ff5fe3405548</group_chat_id>
  <team_members>manager, architect, 通用执行助手, PRD</team_members>
  <agent_call call_id="5f225bcb" from="manager" content_head="请审核 Issue 05 的提交，**必" need_response="true" />
  <user_pin_message>
    1. [user]: @manager 后续issue的启动你直接它完成之后，你直接开始就可以了，不用再询问我
  </user_pin_message>
</runtime>

<incoming_message>
[Agents Hub 平台消息]
call_id: 5f225bcb
来自：manager
发送给：2号通用审查助手（你）
类型：task
内容：请审核 Issue 05 的提交，**必须使用 local-code-review skill**。

**背景**：飞书 Channel 集成，Issue 05 Session 映射与同步状态管理。代码已提交（commit 0666a72）。

**需要阅读的文档**：
- 架构约束：.scratch/feishu-channel/architecture.md
- PRD：.scratch/feishu-channel/PRD.md
- Issue：.scratch/feishu-channel/issues/05-session-mapping-sync.md
...
</incoming_message>
```

### 问题点

1. **关键指令位置靠后**：强调的 `**必须使用 local-code-review skill**` 出现在第 16 行
2. **元数据噪音**：前面有大量技术元数据（token、group_chat_id、call_id 等）
3. **信息密度低**：`<runtime>` 占据大量空间但对任务执行价值不高
4. **视觉干扰**：XML 标签、重复的 call_id（出现 2 次）

## 解决方案

### 方案 1：精简 Runtime（推荐）

**核心思路**：只保留任务执行必需的信息，其他元数据移到文档末尾或完全移除。

#### 优化后结构

```xml
<incoming_message>
[任务]
来自：manager
**关键要求**：必须使用 local-code-review skill

**背景**：飞书 Channel 集成，Issue 05 Session 映射与同步状态管理。代码已提交（commit 0666a72）。

**需要阅读的文档**：
- 架构约束：.scratch/feishu-channel/architecture.md
- PRD：.scratch/feishu-channel/PRD.md
- Issue：.scratch/feishu-channel/issues/05-session-mapping-sync.md

**提交的文件**：
- agents_hub/channels/feishu/session.py (新增)
- tests/channels/feishu/test_session.py (新增)
...

**审核要求**：
1. 使用 local-code-review skill 进行完整审查
2. 对照 Issue 中的 Acceptance criteria 逐项验证
3. 检查代码质量和架构一致性
</incoming_message>

<runtime>
  <!-- 技术元数据：供 MCP 工具使用，非任务关键信息 -->
  <agent_token>tok_e9a19b7094c43f21fb98f3e38176d0c5</agent_token>
  <group_chat_id>4a3a4cbb-49d9-4efb-a1e8-ff5fe3405548</group_chat_id>
  <call_id>5f225bcb</call_id>
  <team_members>manager, architect, 通用执行助手, PRD</team_members>
</runtime>
```

#### 修改点

1. **任务内容前置**：`<incoming_message>` 放在最前面
2. **关键要求突出**：使用 `**关键要求**` 标题，紧跟任务来源
3. **元数据后置**：`<runtime>` 移到末尾，标注为"技术元数据"
4. **去重**：call_id 只在 runtime 中出现一次
5. **简化标签**：移除 `[Agents Hub 平台消息]`，使用更简洁的 `[任务]`

### 方案 2：分离关键指令

**核心思路**：将关键指令提取为独立的 `<critical_instructions>` 区块。

```xml
<critical_instructions>
**必须遵守的执行要求**：
1. 必须使用 local-code-review skill 进行完整审查
2. 不得跳过 skill 定义的任何步骤
3. 需要启动 Haiku Agent 收集上下文
4. 需要 8 个并行 Agent 独立审查
</critical_instructions>

<incoming_message>
[任务] 审核 Issue 05 的提交
来自：manager

**背景**：飞书 Channel 集成...
</incoming_message>

<runtime>...</runtime>
```

### 方案 3：使用 System Prompt 强化

在 Agent 的 system prompt（ROLE_INSTRUCTIONS）中添加：

```markdown
## 指令遵循规则

当收到的任务中包含以下标记时，必须严格遵守：
- "**必须使用 XXX skill**" → 调用指定 skill，不得用其他方式替代
- "**禁止 XXX**" → 绝对不能执行该操作
- "**关键要求**" 标题下的所有内容 → 逐条验证完成

如果你发现自己想跳过某个明确要求的步骤，必须：
1. 停下来
2. 重新阅读任务中的关键要求
3. 确认为什么设计了这个要求（通常 skill 的多步骤设计是有理由的）
4. 按要求执行
```

## 实施建议

### 短期（立即可做）

1. **修改 `renderer.py:render_for_llm()`**：
   - 将 `[Agents Hub 平台消息]` 改为 `[任务]`
   - 移除重复的 call_id
   - 简化格式

2. **修改 `agent_context.py:build_user_prompt()`**：
   - 调整拼接顺序：`<incoming_message>` 在前，`<runtime>` 在后
   - 在 `<runtime>` 前添加注释说明这是技术元数据

3. **修改各 Agent 的 `ROLE_INSTRUCTIONS`**：
   - 添加"指令遵循规则"章节
   - 强调带 `**必须**` 标记的指令不可忽略

### 中期（需测试验证）

1. **引入 `<critical_instructions>` 区块**：
   - 在 MCP tool `call_agent()` 中检测内容是否包含 "必须" 等关键词
   - 自动提取为 `<critical_instructions>`
   - 修改 `build_user_prompt()` 支持该区块

2. **压缩 Runtime 信息**：
   - 移除对任务执行无用的字段（如 `team_members` 对 Worker 无用）
   - 按角色差异化注入（Manager 看全量，Worker 看精简版）

### 长期（架构优化）

1. **提示词分层**：
   - Layer 1: Critical Instructions（强制要求）
   - Layer 2: Task Content（任务内容）
   - Layer 3: Context（上下文）
   - Layer 4: Metadata（元数据）

2. **动态提示词压缩**：
   - 根据任务类型动态调整 Runtime 内容
   - 简单任务（如审查）移除无关字段
   - 复杂任务（如编排）保留完整信息

## 预期效果

- **指令遵循率提升**：关键要求前置后，Agent 更容易注意到
- **响应质量提升**：减少元数据噪音，Agent 注意力集中在任务本身
- **Token 消耗降低**：精简后每条消息节省 50-100 tokens

## 风险

1. **MCP 工具依赖 Runtime**：需确保移动 Runtime 位置后，工具仍能正确提取 agent_token 等信息
   - **缓解**：Runtime 依然存在，只是位置后移，工具应该不受影响
2. **现有 Agent 适应期**：修改提示词结构后，需重新测试所有 Agent
   - **缓解**：分阶段推出，先在单个 Agent 测试
