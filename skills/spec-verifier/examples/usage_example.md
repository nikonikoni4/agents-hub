# Spec Verifier 使用示例

## 场景描述

用户要求AI创建一个用户登录功能的spec文档，然后想要验证这个文档是否符合自己的原始需求。

## 使用流程

### 1. 用户提出需求

```
用户: 我需要一个用户登录功能，包括用户名密码登录、记住登录状态、忘记密码功能
```

### 2. AI生成spec文档

```
AI: ## User Login Spec

### 功能需求
- 用户名密码登录
- 记住登录状态
- 忘记密码功能

### 技术实现
- 使用JWT token进行身份验证
- 支持"记住我"功能
- 密码重置流程
```

### 3. 用户触发验证

```
用户: 验证一下刚才写的spec
```

### 4. 主agent获取会话信息

```bash
# 获取session_id
echo $CLAUDE_SESSION_ID
# 输出: abc123

# 获取CLAUDE_CONFIG_DIR
echo $CLAUDE_CONFIG_DIR
# 输出: C:\Users\15535\.claude
```

### 5. 主agent启动subagent

```python
Agent(
    description="验证文档是否符合用户意图",
    prompt=f"""
请验证当前会话中生成的文档是否符合用户的原始意图。

会话信息：
- session_id: abc123
- CLAUDE_CONFIG_DIR: C:\Users\15535\.claude

用户原始需求：
我需要一个用户登录功能，包括用户名密码登录、记住登录状态、忘记密码功能

当前文档：
## User Login Spec

### 功能需求
- 用户名密码登录
- 记住登录状态
- 忘记密码功能

### 技术实现
- 使用JWT token进行身份验证
- 支持"记住我"功能
- 密码重置流程

请执行以下步骤：
1. 使用脚本读取会话历史: python skills/spec-verifier/scripts/session_reader.py abc123 C:\Users\15535\.claude
2. 分析用户意图和需求
3. 对比当前文档与用户需求
4. 生成详细的验证报告

报告格式请参考: skills/spec-verifier/references/subagent_prompt.md
"""
)
```

### 6. Subagent执行审查

Subagent会：

1. 使用`session_reader.py`读取会话历史
2. 提取用户需求和AI文档
3. 对比需求覆盖情况
4. 生成验证报告

### 7. 输出验证报告

```markdown
# 文档验证报告

## 审查概览
- 会话ID: abc123
- 用户需求数量: 3
- 已覆盖需求数量: 3
- 未覆盖需求数量: 0

## 已覆盖的用户需求
- ✅ 用户名密码登录
- ✅ 记住登录状态
- ✅ 忘记密码功能

## 未覆盖的用户需求
- 无

## 整体评估
- 需求覆盖率: 100.0%
- 评价: 良好
```

## 高级用法

### 验证特定文档

如果用户想要验证特定的文档文件，可以使用`--document`参数：

```bash
python skills/spec-verifier/scripts/verify_spec.py abc123 C:\Users\15535\.claude --document path/to/document.md
```

### 自定义匹配阈值

如果需要调整匹配阈值，可以修改`verify_spec.py`中的阈值参数：

```python
# 在compare_requirements_with_documents函数中
if len(req_keywords) > 0 and len(matched_keywords) / len(req_keywords) > 0.1:  # 调整这个阈值
    covered = True
```

## 注意事项

1. 确保会话文件存在且可读
2. 需要Python 3.7+环境
3. 建议在稳定的网络环境下使用
4. 对于复杂的文档，可能需要更智能的NLP分析
