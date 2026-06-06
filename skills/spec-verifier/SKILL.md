---
name: spec-verifier
description: 验证主agent是否按照用户意图编写spec或计划文档。当用户说"验证spec"、"检查文档"、"审查计划"、"验证我的想法"、"看看文档对不对"时触发。通过获取session信息，让subagent审查文档内容是否符合用户观点。
---

# Spec Verifier

验证主agent是否按照用户意图编写spec或计划文档。

## 工作流程

### 1. 获取会话信息

主agent需要获取以下信息：

```bash
# 获取session_id（从Claude Code内部）
echo $CLAUDE_SESSION_ID

# 获取CLAUDE_CONFIG_DIR
echo $CLAUDE_CONFIG_DIR
```

### 2. 启动Subagent审查

使用Agent工具启动subagent，传递以下参数：

```python
Agent(
    description="验证文档是否符合用户意图",
    prompt=f"""
请验证当前会话中生成的文档是否符合用户的原始意图。

会话信息：
- session_id: {session_id}
- CLAUDE_CONFIG_DIR: {config_dir}

用户原始需求：
{user_requirements}

当前文档：
{current_document}

请执行以下步骤：
1. 使用脚本读取会话历史: python skills/spec-verifier/scripts/session_reader.py {session_id} {config_dir}
2. 分析用户意图和需求
3. 对比当前文档与用户需求
4. 生成详细的验证报告

报告格式请参考: skills/spec-verifier/references/subagent_prompt.md
"""
)
```

### 3. Subagent审查流程

Subagent执行以下步骤：

1. **定位会话文件**: 使用`session_reader.py`脚本读取会话内容
2. **分析用户意图**: 从会话历史中提取用户的原始需求
3. **审查生成文档**: 检查当前生成的spec或计划文档
4. **对比需求覆盖**: 验证文档是否覆盖了用户的所有需求
5. **生成审查报告**: 提供详细的验证结果

## 使用示例

```
用户: 验证一下刚才写的spec
用户: 检查文档是否符合我的想法
用户: 审查计划文档
```

## 脚本说明

### session_reader.py

读取Claude Code会话内容，提取关键信息。

**用法**:
```bash
python skills/spec-verifier/scripts/session_reader.py <session_id> <claude_config_dir>
```

**输出**:
- 会话内容的JSON格式摘要
- 用户消息列表
- AI生成的文档列表

### verify_spec.py

验证spec或计划文档是否符合用户意图。

**用法**:
```bash
python skills/spec-verifier/scripts/verify_spec.py <session_id> <claude_config_dir> [--document <document_path>]
```

**输出**:
- 验证报告
- 需求覆盖率统计
- 整体评估

## 输出格式

审查报告包含：

- ✅ 符合用户意图的部分
- ❌ 不符合或遗漏的部分
- 💡 改进建议
- 📊 整体符合度评分（需求覆盖率、意图符合度、约束遵守度）
