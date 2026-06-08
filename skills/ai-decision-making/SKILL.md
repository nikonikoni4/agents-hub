---
name: ai-decision-making
description: 当用户面临技术决策、架构选择、实现路径不确定时使用。帮助用户梳理可能的方案、分析优缺点、记录知识负债（用户不了解的内容让 AI 判断的部分）和 AI 决策过程。触发词：决策、怎么选、哪个方案、不确定、不知道怎么做、实现路径、技术选型、架构选择。
---

## 核心目标

帮助用户做出知情决策，同时记录：
1. **知识负债**：用户不了解、让 AI 判断的内容
2. **AI 决策过程**：AI 的推理路径和方案对比

## 执行流程

```
1. 理解问题 → 收集上下文
2. 列出所有可能的实现路径
3. 分析每个方案的优缺点和适用场景
4. 读取用户决策习惯 → 了解用户偏好
5. 给出 AI 推荐 + 理由
6. 等待用户决策
7. 编写知识负债文档 + AI 决策记录
8. 双写：全局 + 项目级
```

## Step 1: 理解问题

确认以下信息：
- 决策的具体问题是什么
- 有哪些约束条件（时间、技术栈、团队能力等）
- 用户已经知道什么、不知道什么

如果问题不清晰，先向用户确认。

## Step 2: 列出实现路径

尽可能全面地列出所有可能的方案，包括：
- 常规方案（业界常用）
- 替代方案（不太常见但可行）
- 激进方案（创新或高风险）

每个方案需要说明：
- 具体如何实现
- 优点
- 缺点
- 适用场景

## Step 3: 读取用户决策习惯

读取以下文件了解用户偏好：
- `D:\desktop\quackDocs\my_notes\my-decisions\user-design-summary.md`
- `D:\desktop\quackDocs\my_notes\my-decisions\index.md`

根据用户的历史决策偏好，调整推荐理由。

## Step 4: 给出 AI 推荐

基于以下因素给出推荐：
1. 方案本身的优缺点
2. 用户的历史决策偏好
3. 当前项目的约束条件

明确说明推荐理由，以及为什么其他方案不适合。

## Step 5: 等待用户决策

不要替用户做决定。等待用户明确选择。

如果用户询问"你觉得呢"或"你推荐哪个"，给出推荐但强调这是建议。

## Step 6: 编写文档

用户做出决策后，编写两份文档：

### 知识负债文档

使用模板：[references/knowledge-debt-template.md](references/knowledge-debt-template.md)

记录：
- 用户在本次决策中暴露的知识盲区
- AI 代替用户做出的判断
- 需要后续验证的假设
- 知识补全建议

### AI 决策记录文档

使用模板：[references/ai-decision-record-template.md](references/ai-decision-record-template.md)

记录：
- 所有可能的实现路径
- 方案对比
- AI 推荐和理由
- 用户最终决策
- 决策过程中的关键讨论点

## Step 7: 双写规则

每次决策写入两个位置：

| 位置 | 路径 | 用途 |
|------|------|------|
| 全局级 | `D:\desktop\quackDocs\my_notes\my-knowledge-debt-and-ai-decisions\YYYY-MM-DD-{topic}\` | 跨项目积累 |
| 项目级 | `docs\ai-decision\YYYY-MM-DD-{topic}\` | 项目内参考 |

文件夹结构（以日期-主题命名）：
```
2026-06-08-pre-commit-config/
├── 2026-06-08-pre-commit-config-knowledge-debt.md
└── 2026-06-08-pre-commit-config-ai-decisions.md
```

写入后更新对应的 `index.md`：
- 全局级：`D:\desktop\quackDocs\my_notes\my-knowledge-debt-and-ai-decisions\index.md`
- 项目级：`docs\ai-decision\index.md`

全局级 index.md 格式：
```markdown
| YYYY-MM-DD | 主题 | 状态 | 项目名 | [知识负债](YYYY-MM-DD-topic/YYYY-MM-DD-topic-knowledge-debt.md) | [AI 决策](YYYY-MM-DD-topic/YYYY-MM-DD-topic-ai-decisions.md) |
```

项目名从当前工作目录的文件夹名推断。

## 与 write-decisions 的关系

- `ai-decision-making`：决策过程辅助，记录知识负债和 AI 推理过程
- `write-decisions`：决策结果记录，记录最终决策内容和原因

两者可以配合使用：
1. 先用 `ai-decision-making` 梳理方案、记录过程
2. 用户做出决策后，用 `write-decisions` 记录最终决策

## 注意事项

1. **不替用户做决定**：AI 只提供分析和推荐，最终决策权在用户
2. **记录知识负债**：诚实记录用户不了解的内容，不要假装用户知道
3. **方案要全面**：不要只列出 AI 认为好的方案，要尽可能全面
4. **引用用户偏好**：基于用户历史决策给出推荐，而非通用建议
