# Codex CLI 权限系统说明

## 概述

Codex CLI 的权限控制可以分成三层：

1. **Sandbox 模式**：控制 Codex 执行命令时能访问哪些文件和系统能力。
2. **Approval 策略**：控制 Codex 执行命令前是否需要用户确认。
3. **危险绕过参数**：通过 CLI 参数同时跳过 approval 和 sandbox。

本文基于当前本机 `codex --help`、`codex exec --help`、`codex sandbox --help` 输出整理。后续 Codex CLI 版本更新时，需要重新校验参数名称和语义。

---

## 一、常规运行权限

### 1.1 Sandbox 模式

Codex CLI 使用 `--sandbox` 参数选择命令执行沙箱：

```bash
codex --sandbox workspace-write
codex exec --sandbox workspace-write "执行任务描述"
```

可选值：

| 值 | 说明 |
| --- | --- |
| `read-only` | 只读模式。适合代码审查、分析、问答，不允许写入工作区。 |
| `workspace-write` | 工作区写入模式。允许在指定工作区内读写，是日常开发的推荐默认模式。 |
| `danger-full-access` | 高权限模式。放宽 sandbox 限制，但不等同于跳过所有确认。 |

### 1.2 Approval 策略

Codex CLI 使用 `--ask-for-approval` 参数配置命令审批策略：

```bash
codex --ask-for-approval on-request
codex exec --ask-for-approval never "执行任务描述"
```

可选值：

| 值 | 说明 |
| --- | --- |
| `untrusted` | 只允许可信命令无确认执行，其他命令需要用户批准。 |
| `on-request` | 由模型决定何时请求用户批准。适合交互式开发。 |
| `never` | 永不请求用户批准。命令失败会直接返回给模型，不会请求非沙箱执行。适合非交互式自动化，但仍受 sandbox 约束。 |
| `on-failure` | 已废弃。命令先无确认执行，失败后再请求非沙箱执行。当前帮助文本建议交互式使用 `on-request`，非交互式使用 `never`。 |

### 1.3 Sandbox 与 Approval 的关系

这两层是独立维度：

| 配置 | 含义 |
| --- | --- |
| `--sandbox read-only --ask-for-approval on-request` | 只读环境中运行，必要时请求批准。 |
| `--sandbox workspace-write --ask-for-approval on-request` | 日常开发常用组合，允许工作区写入，危险操作可请求批准。 |
| `--sandbox workspace-write --ask-for-approval never` | 自动化常用组合，不请求批准，但仍限制在工作区写入。 |
| `--sandbox danger-full-access --ask-for-approval never` | 高风险组合，放宽 sandbox 且不请求批准，但仍不是最高危险绕过参数。 |

关键点：`danger-full-access` 是 sandbox 模式；`never` 是 approval 策略。两者组合后风险很高，但仍不同于 `--dangerously-bypass-approvals-and-sandbox`。

---

## 二、CLI 危险绕过参数

### 2.1 完整 CLI 命令

```bash
codex --dangerously-bypass-approvals-and-sandbox
codex exec --dangerously-bypass-approvals-and-sandbox "执行任务描述"
```

### 2.2 命令含义

`--dangerously-bypass-approvals-and-sandbox` 会跳过所有确认提示，并且在无 sandbox 的情况下执行命令。

当前 CLI 帮助文本将它标注为极高风险，并说明它只应该用于外部环境已经提供隔离的场景。

### 2.3 与常规权限模式的区别

| 特性 | `--sandbox danger-full-access` + `--ask-for-approval never` | `--dangerously-bypass-approvals-and-sandbox` |
| --- | --- | --- |
| 是否跳过 approval | 是 | 是 |
| 是否跳过 sandbox | 否，只是选择最高 sandbox 模式 | 是，直接无 sandbox |
| 是否适合作为普通角色权限模式 | 不建议，但可作为高风险模式 | 不建议，应作为单独危险开关 |
| 推荐存储位置 | `role.json` 中的运行时权限字段 | `role.json` 中的显式危险布尔字段 |
| 推荐传递方式 | 转换为 `RoleConfig` 后由 executor 拼接 CLI 参数 | 转换为 `RoleConfig` 后由 executor 拼接 CLI 参数 |

---

## 三、config.toml 与 CLI 参数

### 3.1 config.toml 的定位

Codex 默认从 `$CODEX_HOME/config.toml` 读取配置。agents-hub 当前为每个角色复制独立的 `work_root/config.toml`，并通过 `CODEX_HOME` 让 Codex CLI 读取角色自己的配置目录。

`config.toml` 适合存放长期稳定的平台配置，例如模型、profile、环境策略、用户偏好等。

### 3.2 CLI 参数的定位

`--sandbox`、`--ask-for-approval`、`--dangerously-bypass-approvals-and-sandbox` 是 Codex CLI 启动参数。对 agents-hub 来说，它们属于角色运行时权限，而不是单纯的平台配置文件编辑。

推荐链路：

```text
role.json
  -> RoleConfig
  -> CodexExecutor 构造 argv
  -> codex exec --sandbox ... --ask-for-approval ...
```

这样做的好处：

1. 前端可以用统一字段展示和修改角色权限。
2. executor 是唯一拼接 CLI 参数的地方，符合 SSOT。
3. 高风险绕过参数可以被单独标记、提示和审计。
4. 不需要让前端理解 Codex `config.toml` 的全部细节。

### 3.3 `--config key=value` 覆盖

Codex CLI 也支持 `-c, --config <key=value>` 临时覆盖 `config.toml` 中的配置：

```bash
codex -c model="o3"
codex -c shell_environment_policy.inherit=all
```

这个能力适合临时覆盖普通配置，但不建议作为角色权限模式的主要实现方式。角色权限应该用明确字段建模，再由 executor 转成 CLI 参数。

---

## 四、建议的 role.json 字段

为了和 Claude Code 的权限体系保持可理解的一致性，同时保留 Codex 自身语义，建议在 `role.json` 增加运行时权限字段，而不是把它们直接藏在 `config.toml` 中。

示例：

```json
{
  "name": "codex_dev",
  "platform": "codex",
  "permission": {
    "sandbox": "workspace-write",
    "approval": "on-request",
    "bypass_approvals_and_sandbox": false
  }
}
```

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `permission.sandbox` | string | Codex sandbox 模式：`read-only` / `workspace-write` / `danger-full-access`。 |
| `permission.approval` | string | Codex approval 策略：`untrusted` / `on-request` / `never`。不建议新建角色使用已废弃的 `on-failure`。 |
| `permission.bypass_approvals_and_sandbox` | bool | 是否启用最高风险绕过参数。为 true 时 executor 应传入 `--dangerously-bypass-approvals-and-sandbox`。 |

推荐默认值：

```json
{
  "permission": {
    "sandbox": "workspace-write",
    "approval": "on-request",
    "bypass_approvals_and_sandbox": false
  }
}
```

### 4.1 参数生成规则

当 `bypass_approvals_and_sandbox=false`：

```bash
codex exec --sandbox <sandbox> --ask-for-approval <approval> --json
```

当 `bypass_approvals_and_sandbox=true`：

```bash
codex exec --dangerously-bypass-approvals-and-sandbox --json
```

建议此时不要同时传 `--sandbox` 和 `--ask-for-approval`，避免语义混乱。

---

## 五、最佳实践建议

### 5.1 日常开发角色

```json
{
  "permission": {
    "sandbox": "workspace-write",
    "approval": "on-request",
    "bypass_approvals_and_sandbox": false
  }
}
```

适合需要写代码、跑测试、偶尔安装依赖或执行敏感命令的开发型角色。

### 5.2 只读审查角色

```json
{
  "permission": {
    "sandbox": "read-only",
    "approval": "on-request",
    "bypass_approvals_and_sandbox": false
  }
}
```

适合 code review、架构分析、文档阅读等场景。

### 5.3 自动化执行角色

```json
{
  "permission": {
    "sandbox": "workspace-write",
    "approval": "never",
    "bypass_approvals_and_sandbox": false
  }
}
```

适合非交互式任务。它不会请求用户确认，但仍受 workspace sandbox 约束。

### 5.4 外部沙箱中的高风险自动化角色

```json
{
  "permission": {
    "sandbox": "danger-full-access",
    "approval": "never",
    "bypass_approvals_and_sandbox": true
  }
}
```

只建议在外部已经有明确隔离的环境中使用，例如容器、虚拟机、一次性 CI runner。不要把它作为普通用户默认选项。

---

## 六、常见问题

### Q1: Codex 是否有类似 Claude `--dangerously-skip-permissions` 的参数？

有。Codex 的对应参数是：

```bash
--dangerously-bypass-approvals-and-sandbox
```

它同时绕过确认和 sandbox，风险等级最高。

### Q2: `danger-full-access` 是否等于最高危险绕过？

不是。`danger-full-access` 是 sandbox 的一个模式；最高危险绕过是 `--dangerously-bypass-approvals-and-sandbox`。

### Q3: `approval=never` 是否等于无权限限制？

不是。`approval=never` 只是永不请求用户批准，仍然受当前 sandbox 模式限制。

### Q4: 这些配置应该写进 `config.toml` 还是 `role.json`？

对 agents-hub 来说，建议写进 `role.json`，再传入 `RoleConfig`，最终由 executor 转成 CLI 参数。因为这些字段决定角色启动时的运行权限，是角色业务配置的一部分。

### Q5: 是否还需要支持直接编辑 `config.toml`？

需要。直接编辑 `config.toml` 适合高级用户修改 Codex 原生配置。但权限模式切换应该优先走结构化字段，避免前端和用户直接操作复杂原生配置。
