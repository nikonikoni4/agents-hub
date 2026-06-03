# Git Hotfix 工作流程

在开发过程中发现 bug，需要把修复应用到多个分支的推荐流程。

## 场景

- 在某个开发分支上发现 bug
- 这个 bug 需要修复并应用到 main 和其他开发分支

## 推荐流程

```
main ──────●──────●─────── merge hotfix ──→
            \              /
hotfix ────── fix commit ──
            \
dev-branch ──●──────●──── cherry-pick fix ──→
```

### 1. 从 main 创建 hotfix 分支

```bash
git checkout -b hotfix/fix-xxx main
```

### 2. 修复 bug 并提交

```bash
# 修复代码
git commit -m "fix: xxx"
```

### 3. merge 到 main

```bash
git checkout main
git merge hotfix/fix-xxx
```

### 4. cherry-pick 到需要的开发分支

```bash
git checkout dev-branch
git cherry-pick <fix-commit-hash>
```

## 为什么用 cherry-pick 而不是 rebase

| | rebase | cherry-pick |
|---|---|---|
| 历史 | 重写历史 | 保持原样 |
| 远程同步 | 需要 force push | 正常 push |
| 协作 | 影响其他人 | 无影响 |
| 灵活性 | 必须全量应用 | 只拿想要的提交 |

**简单说**：rebase 是"把我的分支重新放到 main 最新位置"，cherry-pick 是"只拿这一个修复过来"。只需要这一个修复时，cherry-pick 更精准。

## cherry-pick 常用语法

```bash
# 摘取单个提交
git cherry-pick <commit-hash>

# 摘取多个提交
git cherry-pick hash1 hash2 hash3

# 摘取一个范围（不包含 start）
git cherry-pick start..end

# 只应用修改，不自动提交（可以继续修改后再 commit）
git cherry-pick -n <commit-hash>
```

## 典型场景

1. **bug 修复**：bugfix 在开发分支上，想快速同步到生产分支
2. **功能迁移**：某个提交本来在 A 分支，现在想放到 B 分支
3. **撤销回退后的恢复**：回退了几个提交，但其中某个还想保留