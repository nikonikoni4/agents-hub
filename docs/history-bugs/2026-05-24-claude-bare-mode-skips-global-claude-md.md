# Claude CLI --bare 模式跳过全局 CLAUDE.md 和 skills

- 发现时间：2026-05-24
- 影响范围：使用 `--bare` 模式执行 Claude CLI 时，CLAUDE_CONFIG_DIR 中的 CLAUDE.md 不会被加载，导致角色隔离失效
- 状态：已修复（从测试脚本中移除 `--bare`）

## 问题描述

在测试 `CLAUDE_CONFIG_DIR` profile 隔离功能时，使用了 `--bare` 模式执行 Claude CLI：

```python
result = subprocess.run(
    ["claude", "-p", "--bare", prompt],
    ...
)
```

测试目录结构：
```
claude-test/
  nico/
    CLAUDE.md    -> "你是nico，你的任务是后端开发"
    settings.json
  xiaoli/
    CLAUDE.md    -> "你是xiaoli，你的任务是前端设计"
    settings.json
```

预期：两个角色分别回答"后端开发"和"前端设计"。
实际：两个角色回答相同，CLAUDE.md 中的角色定义未生效。

## 根因

`--bare` 模式的设计意图是最小化启动，跳过以下内容的自动加载：

- 全局 CLAUDE.md（`~/.claude/CLAUDE.md` 或 `CLAUDE_CONFIG_DIR/CLAUDE.md`）
- 全局 skills
- hooks
- LSP
- 插件同步
- keychain 读取
- auto-memory

`--bare` **不跳过**项目级 CLAUDE.md（工作目录下的 `CLAUDE.md`）。

当 `CLAUDE_CONFIG_DIR` 指向 `claude-test/nico/` 时，该目录下的 `CLAUDE.md` 对于 Claude CLI 来说是"全局 CLAUDE.md"（因为它在 config dir 根目录），`--bare` 会跳过它。

## 解决方案

从测试脚本中移除 `--bare` 标志：

```python
# Before
result = subprocess.run(
    ["claude", "-p", "--bare", prompt],
    ...
)

# After
result = subprocess.run(
    ["claude", "-p", prompt],
    ...
)
```

## 加载行为总结

| 内容 | 默认模式 | `--bare` 模式 |
|------|---------|-------------|
| 全局 CLAUDE.md（config dir 根目录） | ✅ 加载 | ❌ 跳过 |
| 项目级 CLAUDE.md（工作目录） | ✅ 加载 | ✅ 加载 |
| 全局 skills | ✅ 加载 | ❌ 跳过 |
| hooks | ✅ 执行 | ❌ 跳过 |
| 插件 | ✅ 同步 | ❌ 跳过 |
| settings.json | ✅ 加载 | ✅ 加载 |

## 注意事项

- `--bare` 适合不需要全局指令和插件的场景（如 CI、纯脚本调用）
- 如果依赖 `CLAUDE_CONFIG_DIR` 中的 `CLAUDE.md` 做角色定义，不能使用 `--bare`
- 如果需要角色隔离 + 最小化启动，应该用 `--setting-sources` 控制加载源，而不是 `--bare`
