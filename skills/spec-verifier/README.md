# Spec Verifier Skill

验证主agent是否按照用户意图编写spec或计划文档。

## 功能概述

这个skill帮助用户验证AI生成的文档是否符合用户的原始需求和意图。通过分析会话历史，自动检测文档对用户需求的覆盖情况。

## 使用场景

- 验证spec文档是否符合用户需求
- 检查计划文档是否遗漏重要需求
- 审查AI生成的文档质量
- 确保AI理解了用户的真实意图

## 工作原理

1. **获取会话信息**: 从当前会话中提取session_id和CLAUDE_CONFIG_DIR
2. **读取会话历史**: 使用脚本读取会话文件，提取用户需求和AI文档
3. **智能匹配分析**: 对比用户需求与AI文档，计算需求覆盖率
4. **生成验证报告**: 输出详细的验证结果和改进建议

## 使用方法

### 触发方式

用户可以通过以下方式触发skill：

```
验证一下刚才写的spec
检查文档是否符合我的想法
审查计划文档
看看文档对不对
验证我的需求是否被满足
```

### 主agent工作流程

1. **获取当前会话信息**：
   ```bash
   echo $CLAUDE_SESSION_ID
   echo $CLAUDE_CONFIG_DIR
   ```

2. **启动subagent进行审查**：
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

3. **Subagent执行审查并生成报告**

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

### test_spec_verifier.py

测试spec-verifier skill的功能。

**用法**:
```bash
python skills/spec-verifier/scripts/test_spec_verifier.py
```

**输出**:
- 测试结果
- 功能验证

## 输出示例

```markdown
# 文档验证报告

## 审查概览
- 会话ID: test123
- 用户需求数量: 1
- 已覆盖需求数量: 1
- 未覆盖需求数量: 0

## 已覆盖的用户需求
- ✅ 我需要一个用户登录功能...

## 未覆盖的用户需求
- 无

## 整体评估
- 需求覆盖率: 100.0%
- 评价: 良好
```

## 文件结构

```
skills/spec-verifier/
├── SKILL.md                    # Skill主文件
├── README.md                   # 使用说明
├── scripts/                    # 脚本目录
│   ├── session_reader.py       # 会话读取脚本
│   ├── verify_spec.py          # 文档验证脚本
│   └── test_spec_verifier.py   # 测试脚本
├── references/                 # 参考文档
│   └── subagent_prompt.md      # Subagent提示词模板
└── examples/                   # 使用示例
    └── usage_example.md        # 使用示例文档
```

## 技术细节

### 匹配算法

- 使用关键词匹配算法分析用户需求与AI文档的对应关系
- 支持中文文本的智能分词和匹配
- 可配置匹配阈值（默认10%）

### 扩展性

- 支持自定义匹配规则
- 可集成更复杂的NLP分析
- 支持多种文档格式的解析

## 使用示例

### 基本用法

```
用户: 我需要一个用户登录功能
AI: [生成spec文档]
用户: 验证一下刚才写的spec
AI: [启动spec-verifier skill，生成验证报告]
```

### 高级用法

```
用户: 检查这个文档是否符合我的要求
AI: [读取指定文档，进行验证]
```

## 注意事项

- 确保会话文件存在且可读
- 需要Python 3.7+环境
- 建议在稳定的网络环境下使用
- 对于复杂的文档，可能需要更智能的NLP分析

## 故障排除

### 常见问题

1. **找不到会话文件**
   - 检查session_id是否正确
   - 确认CLAUDE_CONFIG_DIR路径是否正确

2. **匹配率过低**
   - 检查用户需求是否明确
   - 调整匹配阈值参数

3. **脚本运行错误**
   - 检查Python环境
   - 确认依赖包已安装

## 更新日志

- v1.0.0: 初始版本，支持基本的文档验证功能
- 支持中文文本匹配
- 提供详细的验证报告
