---
name: user-workflow
description: 用户工作流概览，每次会话加载。简洁展示用户的 skill 体系和使用时机，让 Claude 主动询问是否需要使用某个 skill。
---

# User Workflow

**每次会话加载此文档**，了解用户的工作流和可用 skill。

---

## 工作流概览

```
想法收集 → 规则建立 → 深度决策 → 任务执行 → 任务交接 → 错误追踪 → 知识沉淀
   ↓           ↓           ↓           ↓           ↓           ↓           ↓
progress   write-      deep-       执行任务    hand-off    ai-mistake  knowledge-
-tracker   project     answer                  hand-on     recorder    crystallizer
           -rules
```

---

## Skill 触发时机

| 时机 | Skill | 主动询问示例 |
|------|-------|--------------|
| 用户表达想法 | `progress-tracker` | "要记录这个想法吗？" |
| 需要建立/审查规则 | `write-project-rules` | "需要为这个模块创建规则吗？" |
| 遇到开放性问题 | `deep-answer` | "这个问题需要深度分析吗？" |
| 任务完成/中断 | `hand-off` | "需要生成交接文档吗？" |
| 接手他人任务 | `hand-on` | "有交接文档需要接手吗？" |
| 发现 AI 犯错 | `ai-mistake-recorder` | "需要记录这个错误吗？" |
| 成功经验可复用 | `knowledge-crystallizer` | "这个经验值得沉淀吗？" |
| 遇到问题/调试 | `knowledge-crystallizer` | "要查一下知识库有没有相关经验吗？" |
| 需要 CI 检查 | `ci-check` | "提交前跑一下检查？" |
| 做出重要决策 | `write-decisions` | "这个决策需要记录吗？" |

---

## 使用原则

1. **主动询问**：识别到相关场景时，主动询问用户是否需要使用 skill
2. **不强制**：用户可以说"不用"，直接跳过
3. **简洁提示**：询问时一句话，不解释 skill 细节
