# Spec Verifier 快速入门

## 什么是Spec Verifier？

Spec Verifier是一个Claude Code skill，用于验证AI生成的文档是否符合用户的原始需求和意图。

## 为什么需要Spec Verifier？

- 确保AI理解了用户的真实需求
- 验证文档是否覆盖了所有需求点
- 提供客观的验证报告
- 帮助用户快速了解文档质量

## 如何使用？

### 1. 触发方式

在Claude Code中，使用以下命令触发skill：

```
验证一下刚才写的spec
检查文档是否符合我的想法
审查计划文档
```

### 2. 工作流程

1. **主agent获取会话信息**
   - 获取session_id
   - 获取CLAUDE_CONFIG_DIR

2. **启动subagent进行审查**
   - 读取会话历史
   - 分析用户需求
   - 对比AI文档

3. **生成验证报告**
   - 需求覆盖率
   - 符合度评分
   - 改进建议

### 3. 输出示例

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

## 整体评估
- 需求覆盖率: 100.0%
- 评价: 良好
```

## 文件结构

```
skills/spec-verifier/
├── SKILL.md                    # Skill主文件
├── README.md                   # 详细使用说明
├── QUICK_START.md              # 快速入门指南
├── scripts/                    # 脚本目录
│   ├── session_reader.py       # 会话读取脚本
│   ├── verify_spec.py          # 文档验证脚本
│   ├── test_spec_verifier.py   # 单元测试
│   ├── e2e_test.py             # 端到端测试
│   └── validate_skill.py       # Skill验证脚本
├── references/                 # 参考文档
│   └── subagent_prompt.md      # Subagent提示词模板
└── examples/                   # 使用示例
    └── usage_example.md        # 使用示例文档
```

## 技术细节

### 匹配算法

- 使用关键词匹配算法
- 支持中文文本智能分词
- 可配置匹配阈值（默认10%）

### 扩展性

- 支持自定义匹配规则
- 可集成更复杂的NLP分析
- 支持多种文档格式

## 故障排除

### 常见问题

1. **找不到会话文件**
   - 检查session_id是否正确
   - 确认CLAUDE_CONFIG_DIR路径

2. **匹配率过低**
   - 检查用户需求是否明确
   - 调整匹配阈值参数

3. **脚本运行错误**
   - 检查Python环境
   - 确认依赖包已安装

## 测试

运行测试验证skill功能：

```bash
# 单元测试
python skills/spec-verifier/scripts/test_spec_verifier.py

# 端到端测试
python skills/spec-verifier/scripts/e2e_test.py

# Skill验证
python skills/spec-verifier/scripts/validate_skill.py
```

## 获取帮助

- 查看README.md了解详细使用说明
- 查看examples/usage_example.md了解使用示例
- 查看references/subagent_prompt.md了解审查流程
