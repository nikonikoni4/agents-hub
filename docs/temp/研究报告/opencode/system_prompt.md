# OpenCode 系统提示词动态配置

## 结论

可以通过 `OPENCODE_CONFIG_DIR` 环境变量动态指定配置目录，将 agent 文件作为系统提示词。

## 测试验证

### 配置目录结构

```
D:\测试\
├── agents/
│   ├── nico.md      # 内容: 你的名字是nico
│   └── asdfgh.md    # 内容: 你的名字是asdfgh
├── opencode.json
└── skills/
```

### 测试命令

```powershell
$env:OPENCODE_CONFIG_DIR="D:\测试"
opencode run --agent nico "你的名字是什么？"
opencode run --agent asdfgh "你的名字是什么？"
```

### 测试结果

| Agent   | 回答                          |
|---------|-------------------------------|
| nico    | 我的名字是 **nico**           |
| asdfgh  | 我的名字是 **asdfgh**         |

## 使用方法

1. 创建配置目录，包含 `agents/` 子目录
2. 在 `agents/` 下创建 `.md` 文件作为 agent（文件名即 agent 名称）
3. 文件内容即为该 agent 的系统提示词
4. 设置环境变量 `OPENCODE_CONFIG_DIR` 指向该目录
5. 使用 `--agent <名称>` 参数启动指定 agent

## 优先级

加载顺序：Global config → `.opencode` 目录 → `OPENCODE_CONFIG_DIR`（可覆盖前者）
