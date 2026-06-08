---
name: write-decisions
description: Use when 用户做出重大决策（架构调整、模块重构、新功能添加、旧功能删除）或用户出现决策疑问（不知道如何解决某个设计问题和非知识问答问题）时，需要记录具体决策内容
---

## 执行流程

1. 按 check-list 逐项确认
2. 满足条件才创建决策文档
3. 双写：项目级 + 全局级
4. 更新 index.md 和 user-design-summary.md

## Check-List

决策必须满足以下**全部条件**才创建：

- [ ] **难以逆转** —— 将来改变主意的成本是可观的
- [ ] **脱离上下文会令人惊讶** —— 未来的读者会疑惑"他们为什么这样做？"
- [ ] **真实权衡的结果** —— 存在真正的替代方案，并且出于特定原因选择了其中一个
- [ ] **信息来源明确** —— 决策依据来自对话内容或用户指定的文档，而非代码推断

决策不需要创建的场景：

- 只是执行常规操作，没有权衡
- 问题有唯一解，不存在替代方案
- 用户只是询问信息，没有做决策

## 信息来源规则（Not To Do）

决策内容**必须基于**：
- 用户在对话中明确表达的判断、偏好、选择
- 用户指定的文档、spec、设计稿
- 对话中讨论过的方案对比和权衡

决策内容**禁止基于**：
- 代码实现本身（代码可能由其他 AI 编写，不代表用户意图）
- 代码注释或 commit message（可能是 AI 生成的）
- 项目中已有的实现方式（不代表这是用户的决策，可能只是 AI 的选择）

如果用户没有指定文档，且对话中没有足够信息推断决策依据，**必须向用户确认**，不能自行推断。

## 双写规则

每次决策写入两个位置，内容相同：

| 位置 | 路径 | 用途 |
|------|------|------|
| 项目级 | `docs\design-decisions\YYYY-MM-DD-{具体内容}.md` | 团队和 agent 参考 |
| 全局级 | `D:\desktop\quackDocs\my_notes\my-decisions\YYYY-MM-DD-{具体内容}.md` | 跨项目积累 |

写入后更新对应的 `index.md`：
- 项目级：`docs\design-decisions\index.md`
- 全局级：`D:\desktop\quackDocs\my_notes\my-decisions\index.md`

全局级 index.md 格式：
```markdown
| YYYY-MM-DD | 决策标题 | decided\undecided | 项目名 | [详情](YYYY-MM-DD-{具体内容}.md) |
```

项目名从当前工作目录的文件夹名推断。

如果全局目录不存在，创建它。

## 决策文档编写

使用模板：[references\decision-template.md](references\decision-template.md)

模板中的各节按需保留，无内容的节直接删除。

## User Design Summary 编写

使用模板：[references\user-design-summary-template.md](references\user-design-summary-template.md)

双写位置：
- 项目级：`docs\design-decisions\user-design-summary.md`
- 全局级：`D:\desktop\quackDocs\my_notes\my-decisions\user-design-summary.md`

编写原则：
- 以批判性视角记录，不迎合用户观点
- 记录用户决策的判断方式，而非决策内容本身
- 如果认为决策不太可取，明确说明风险，让后续 agent 不要盲目参考
- 关联决策文档的链接格式：`[决策标题](.\YYYY-MM-DD-{具体内容}.md)`
