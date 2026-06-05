# set_agent_token_and_default_cwd 中 AI 自作主张的目录拼接规则

- 发现时间：2026-06-05
- 影响范围：所有新建群聊的 Agent（cwd 路径末尾多了 `/m`、`/测` 等错误子目录）
- 状态：已修复

## 问题描述

创建群聊后，Agent 的 `agent_cwd` 路径末尾多了一段奇怪的子目录。例如 `manager` 的 cwd 变成了 `project_path/m`，而非预期的 `project_path`。

## 根因

`set_agent_token_and_default_cwd` 实现时，spec 和 plan 只说了"设置 cwd"，没有定义具体规则。AI 自行发明了一套「首字母 + 末尾数字」的目录拼接逻辑：

```python
# AI 自作主张的实现
agent_lower = agent_name.lower()                        # "manager" → "manager"
first_char = agent_lower[0]                             # "m"
trailing_digits = "".join(c for c in reversed(agent_lower) if c.isdigit())[::-1]  # ""
agent_dir = first_char + trailing_digits                # "m"
cwd = f"{self.project_path}/{agent_dir}"                # "project_path/m"
```

这个规则是为 "Worker1" → "w1" 设计的，但对纯字母名称只取首字母，产生无意义的路径。

实际行为：
| Agent 名称 | 错误 cwd | 预期 cwd |
|-----------|---------|---------|
| Worker1 | project_path/w1 | project_path |
| manager | project_path/m | project_path |
| 测试 | project_path/测 | project_path |

## 教训

**spec/plan 没有定义的行为，AI 不应自行发明规则。** 不确定时应询问用户，而非自己编一个"看起来合理"的逻辑。越是"看起来聪明"的设计，越可能是 AI 幻觉。

## 修复方案

直接使用 `project_path` 作为 cwd，不做任何拼接：

```python
# 修复后
agent_member_info = self.get_or_create_agent_member_info(agent_name)
agent_member_info.token = token
agent_member_info.cwd = self.project_path
```

## 涉及文件

- `agents_hub/core/context/group_chat_runtime.py` - set_agent_token_and_default_cwd 简化逻辑
