# Slice 8: 更新 CONTEXT.md

**类型**: HITL  
**状态**: Ready for implementation

## Parent

PRD: Agent 循环执行功能（Loop）
文件路径: `docs/temp/loop-feature-prd.md`

## What to build

更新项目术语表 CONTEXT.md，添加所有 Loop 相关的术语定义。这是一个文档维护任务，需要人工 review 确保术语定义准确、简洁、与实现一致。

更新以下章节：

1. **核心实体章节**（## 核心实体）：
   - 添加 Loop（循环）定义
   - 添加 LoopNode（循环节点）定义
   - 添加 LoopExecutor（循环执行器）定义
   - 添加 LoopManager（循环管理器）定义

2. **枚举类型章节**（## 枚举类型）：
   - 添加 LoopNodeType（循环节点类型）定义
   - 添加 LoopStatus（循环状态）定义
   - 添加 MessageType.LOOP_MESSAGE 说明

3. **通信系统章节**（## 通信系统 - AgentMessage）：
   - 更新 MessageType 枚举（新增 LOOP_MESSAGE）
   - 更新 AgentMessage.metadata 字段说明
   - 添加循环消息的 metadata 结构示例

4. **渲染层章节**（## 渲染层 - 三个表面）：
   - 更新 render_for_chat() 函数签名（新增 is_loop_message、loop_iteration 参数）
   - 更新 jsonl / UI 群聊串的格式说明（循环消息特殊格式）
   - 添加循环消息特殊渲染规则到核心约束

5. **XML 标签工具**（## 渲染层 - XML 标签工具）：
   - 添加循环上下文相关的 XML 标签常量（LOOP_NODE_ROLE、LOOP_OUTPUT_SCHEMA、PREVIOUS_NODE_OUTPUT、LOOP_TERMINATION_CHECK）

6. **AgentMemberInfo**（## 上下文管理 - AgentMemberInfo）：
   - 更新 status 字段说明（添加 "in_loop" 值，说明为字符串类型）
   - 添加 current_loop_id 字段说明

## Acceptance criteria

- [ ] CONTEXT.md 包含所有 Loop 相关术语定义
- [ ] Loop 术语定义包含：属性、不变量、生命周期、隔离性、退出条件
- [ ] LoopNode 术语定义包含：属性、节点类型、职责描述、输出校验、重试机制
- [ ] LoopExecutor 术语定义包含：职责、持有的组件、位置
- [ ] LoopManager 术语定义包含：职责、持久化路径、位置
- [ ] MessageType 包含 LOOP_MESSAGE 枚举值的定义
- [ ] LoopNodeType 和 LoopStatus 枚举类型定义清晰（每个枚举值的含义）
- [ ] AgentMessage.metadata 的循环消息结构示例准确
- [ ] render_for_chat() 函数签名更新正确
- [ ] 循环消息渲染格式示例正确（`[循环-节点{agent}-第{iteration}轮] @{to} {content}`）
- [ ] XML 标签常量列表完整
- [ ] AgentMemberInfo 的字段更新准确
- [ ] 所有术语定义与 PRD 一致
- [ ] 所有术语定义与实现代码一致
- [ ] 文档格式符合 CONTEXT.md 的现有风格
- [ ] 文档通过人工 review

## Blocked by

Slice 1: 基础数据模型和持久化

## Notes

- CONTEXT.md 路径：`D:\desktop\软件开发\agents-hub\CONTEXT.md`
- 术语定义要简洁，避免实现细节
- 使用项目现有的术语风格（属性、职责、不变量、位置）
- 参考 PRD 的术语更新章节（Further Notes - 术语更新）
- 实现完成后（Slice 1-7）再次检查术语定义是否与代码一致
- 文档更新需要人工 review，标记为 HITL
