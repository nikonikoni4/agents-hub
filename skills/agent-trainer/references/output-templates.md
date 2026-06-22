# 输出模板

本文档定义训练过程中各阶段的交付物格式。

## Agent 角色定义

```markdown
- Agent 名称: [名称]
- 目标平台: [Claude Code / Codex / OpenCode]
- 主要领域: [编程/视频剪辑/内容创作/法律/金融等]
- 核心职责:
  - [职责 1]
  - [职责 2]
  - [职责 3-5]
- 边界清单（不做什么）:
  - [边界 1]
  - [边界 2]
  - [边界 3]
- 协作对象: [开发者/创作者/客户等]
- 成功标准: [什么样算好？]
```

## 项目风格摘要（仅模式 B）

```markdown
### 行为风格
- 文档风格: [详细 vs 简洁]
- 注释密度: [高 / 中 / 低]
- 代码风格: [严谨 / 灵活]

### 决策倾向
- 架构演进: [保守 vs 激进]
- 实现策略: [简洁 vs 完备]
- 歧义处理: [询问 vs 自主]

### 关键术语
- [术语 1]: [含义]
- [术语 2]: [含义]

### 推荐 Checklist 项
- [ ] [项目特定检查项 1]
- [ ] [项目特定检查项 2]
```

## 知识需求清单

```markdown
### 元规则类别
- 执行前 Checklist: [需要哪些检查项？]
- 决策风格: [需要定义哪些决策准则？]
- 执行后自检: [需要哪些验证标准？]

### 领域知识类别
- [类别 1]: [说明]
- [类别 2]: [说明]

### 搜索关键词
- [关键词 1]
- [关键词 2]
```

## 证据收集报告

```markdown
### 高可信度发现（Tier A/B 支持）
- **[主题 1]**: [发现内容]
  - 来源: [URL]
  - 质量等级: Tier A / B

### 条件性发现（单一来源或 Tier C）
- **[主题]**: [发现内容]
  - 来源: [URL]
  - 质量等级: Tier C
  - 备注: 需要进一步验证

### 信息缺口
- [缺失的知识领域 1]
- [缺失的知识领域 2]

### 来源摘要
- Tier A: [数量]
- Tier B: [数量]
- Tier C: [数量]
- Tier D: [数量]（已排除）
```

## 提取的规则清单

```markdown
### 元规则（放入 CLAUDE.md）

#### 执行前 Checklist
- [ ] [检查项 1]
- [ ] [检查项 2]

#### 决策风格
- [决策准则 1]
- [决策准则 2]

#### 执行后自检
- [ ] [自检项 1]
- [ ] [自检项 2]

### 领域知识（放入 knowledge/）
- **fundamentals.md**: [主题]
- **best-practices.md**: [主题]
- **pitfalls.md**: [主题]

### 冲突项及解决方案
- **冲突**: [描述]
  - 来源 A: [观点]
  - 来源 B: [观点]
  - 建议: [如何解决]

### 排除的内容
- [内容]: 原因 - 证据不足
```

## 训练总结

```markdown
### 基本信息
- Agent 名称: [名称]
- 目标平台: [平台]
- 训练模式: [通用 / 项目专用]
- 版本: v[N]

### 创建的文件
- `work_root/CLAUDE.md` (或 AGENTS.md)
- `work_root/knowledge/fundamentals.md`
- `work_root/knowledge/best-practices.md`
- `work_root/knowledge/pitfalls.md`（如有）
- `work_root/.training-metadata.json`

### 关键元规则
- 执行前: [N] 项检查
- 决策风格: [N] 条准则
- 执行后: [N] 项自检

### 知识覆盖范围
- [领域 1]: 已覆盖
- [领域 2]: 已覆盖
- [领域 3]: 部分覆盖

### 已知局限
- [局限 1]
- [局限 2]

### 后续步骤
1. [建议步骤 1]
2. [建议步骤 2]
```

## 更新总结

```markdown
### 更新信息
- 更新类型: [增量 / 重构 / 修正]
- 更新时间: [时间戳]
- 版本: v[N-1] → v[N]

### 变更内容
- **新增**: [内容]
- **修改**: [内容]
- **删除**: [内容]

### 备份位置
- `.training-history/v[N-1]-backup/`

### 回滚命令
如需回滚，使用备份恢复。
```

## .training-metadata.json 格式

```json
{
  "mode": "domain-generic" | "project-specific",
  "project_path": "/path/to/project" | null,
  "created_at": "2026-06-22T10:00:00Z",
  "updated_at": "2026-06-22T10:00:00Z",
  "version": 1,
  "platform": "claude" | "codex" | "opencode",
  "update_history": [
    {
      "version": 1,
      "type": "create" | "incremental" | "refactor" | "fix",
      "timestamp": "2026-06-22T10:00:00Z",
      "summary": "初始训练 / 添加了 XX / 重构了 XX / 修正了 XX"
    }
  ]
}
```
