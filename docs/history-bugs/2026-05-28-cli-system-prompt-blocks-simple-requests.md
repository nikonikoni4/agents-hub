# Codex CLI Prompt 换行符导致解析错误

## Bug 信息

- **发现日期**: 2026-05-28
- **影响平台**: Codex CLI（Claude CLI 未受影响）
- **严重程度**: 高
- **状态**: 已修复

## 问题描述

当通过 Codex CLI 发送包含换行符的 prompt 时，CLI 无法正确解析 prompt 内容，导致返回错误信息或执行失败。

## 触发条件

1. 使用 Codex CLI 执行任务
2. Prompt 中包含换行符（`\n`）
3. 换行符导致 CLI 命令行解析错误

## 复现步骤

```python
# 创建一个 Codex 角色
role_manager.create_role(
    "llm_call_codex",
    AgentPlatform.CODEX,
    type=RoleType.LEADER
)

# 发送包含换行符的 prompt
prompt = """请总结以下对话内容：

对话记录：
[Leader]: 你好！
[小李]: 你好！我负责前端开发。

请输出 JSON 格式..."""

result = await agent.execute(prompt)
```

## 实际结果

Codex 无法正确解析 prompt，返回错误或不符合预期的结果。

## 测试验证

通过 `tests/explore/多agent架构/debug_llm_call.py` 测试发现：

- **带换行符的 prompt**: 返回错误或不完整结果
- **无换行符的 prompt**: 正常执行，返回正确结果
- **去掉换行符的 prompt**: 正常执行，返回正确结果

## 预期结果

无论 prompt 是否包含换行符，都应该正确执行并返回预期结果。

## 根本原因

Codex CLI 在命令行参数解析时，对换行符的处理存在问题：

1. 当 prompt 通过命令行参数传递时，换行符会干扰命令行解析
2. 换行符可能导致 prompt 被截断或错误分割
3. Claude CLI 对换行符的处理更加健壮，不受此问题影响

## 解决方案

### 方案 1：在 CodexExecutor 中自动移除换行符（推荐）

在 `agents_hub/agent_bridge/executors/codex.py` 的 `execute()` 方法中，对 prompt 进行预处理：

```python
async def execute(self, prompt: str, config: RoleConfig) -> AgentResult:
    # 移除换行符，避免命令行解析错误
    prompt = prompt.replace('\n', ' ').replace('\r', ' ')
    
    # ... 其余代码
```

### 方案 2：使用 Claude CLI

Claude CLI 对换行符的处理更加健壮，可以直接使用：

```python
role_manager.create_role(
    "llm_call",
    AgentPlatform.CLAUDE,  # 使用 Claude 而不是 Codex
    type=RoleType.LEADER
)
```

## 影响范围

- **受影响**：所有使用 Codex CLI 且 prompt 包含换行符的场景
- **不受影响**：
  - Claude CLI（对换行符处理更健壮）
  - 不包含换行符的 prompt

## 相关代码位置

- `agents_hub/agent_bridge/executors/codex.py` - Codex CLI 执行器，需要添加换行符处理
- `tests/explore/多agent架构/debug_llm_call.py` - 用于验证此 bug 的测试文件
- `tests/explore/多agent架构/team.py:511-616` - `compact_messages()` 方法，受此 bug 影响

## 经验教训

1. **CLI 参数传递的脆弱性**：命令行参数对特殊字符（如换行符）敏感，需要预处理
2. **不同平台的差异**：Codex 和 Claude 对相同输入的处理方式可能不同
3. **测试的重要性**：通过对比测试（带换行符 vs 无换行符）快速定位问题
4. **直接测试 CLI**：当代码调用失败时，直接在控制台测试 CLI 命令可以帮助区分是代码问题还是 CLI 问题

## 后续改进建议

1. ✅ 在 CodexExecutor 中自动移除换行符（已实现）
2. 为其他特殊字符添加处理（如制表符、回车符等）
3. 在文档中说明不同平台对特殊字符的处理差异
4. 添加单元测试验证特殊字符处理
