# 前端静态检查配置说明

> ⚠️ **ESLint 9.x 使用扁平配置格式**  
> 本项目使用 ESLint 9.x（最新版本），配置文件为 `eslint.config.js`（取代旧的 `.eslintrc.json`）

## 📦 已配置的工具

### 对标后端工具链

| 后端 (Python) | 前端 (TypeScript/React) | 配置文件 | 作用 |
|--------------|------------------------|---------|------|
| **mypy** | **TypeScript Compiler** | `tsconfig.json` | 类型检查 |
| **ruff** | **ESLint + Prettier** | `.eslintrc.json` + `.prettierrc.json` | 代码规范 + 格式化 |
| **pytest** | **Vitest** | `vitest.config.ts` | 单元测试 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 运行静态检查

```bash
# 类型检查（对标 mypy）
npm run type-check

# 代码规范检查（对标 ruff check）
npm run lint

# 格式检查（对标 ruff format --check）
npm run format:check

# 运行测试（对标 pytest）
npm run test

# 完整 CI 流程（对标后端的 CI）
npm run ci
```

### 3. 自动修复

```bash
# 自动修复代码规范问题
npm run lint:fix

# 自动格式化代码
npm run format
```

---

## 📋 配置文件说明

### TypeScript 配置 (`tsconfig.json`)

严格的类型检查，包括：
- ✅ `strict: true` - 启用所有严格模式
- ✅ `noUnusedLocals` - 禁止未使用的局部变量
- ✅ `noUnusedParameters` - 禁止未使用的参数
- ✅ `noUncheckedIndexedAccess` - 索引访问需要检查 undefined
- ✅ 路径别名 `@/*` → `./src/*`

### ESLint 配置 (`eslint.config.js`)

**ESLint 9.x 扁平配置格式**

规则集：
- ✅ TypeScript 推荐规则
- ✅ React 推荐规则（自动检测版本）
- ✅ React Hooks 规则
- ✅ 未使用变量警告（支持 `_` 前缀忽略）
- ⚠️ `any` 类型警告（不禁止，但会提示）
- ⚠️ `console.log` 警告（保留 `console.warn/error`）

### Prettier 配置 (`.prettierrc.json`)

格式化规则：
- 单引号
- 分号
- 2 空格缩进
- 行宽 100 字符

### Vitest 配置 (`vitest.config.ts`)

测试环境：
- ✅ jsdom 环境（模拟浏览器）
- ✅ 覆盖率报告（v8 provider）
- ✅ 全局 API（`describe`, `it`, `expect` 等）

---

## 🔧 集成到开发流程

### Git Hooks（推荐）

可以添加 Husky + lint-staged 在提交前自动检查：

```bash
npm install -D husky lint-staged
npx husky init
```

`.husky/pre-commit`:
```bash
#!/usr/bin/env sh
cd frontend && npm run lint-staged
```

`package.json` 添加：
```json
{
  "lint-staged": {
    "src/**/*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ]
  }
}
```

### VS Code 集成（推荐）

创建 `.vscode/settings.json`：
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "node_modules/typescript/lib"
}
```

推荐扩展 `.vscode/extensions.json`：
```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "vitest.explorer"
  ]
}
```

---

## 📊 CI 脚本对比

### 后端 CI（假设）
```bash
mypy backend/
ruff check backend/
ruff format --check backend/
pytest
```

### 前端 CI（现在可用）
```bash
cd frontend
npm run type-check  # 对标 mypy
npm run lint        # 对标 ruff check
npm run format:check # 对标 ruff format --check
npm run test        # 对标 pytest
```

或者一键运行：
```bash
npm run ci
```

---

## 🎯 规则严格度对比

| 检查项 | 后端 (mypy/ruff) | 前端 (tsc/eslint) |
|-------|-----------------|------------------|
| 类型检查 | ✅ 严格 | ✅ 严格 (`strict: true`) |
| 未使用变量 | ✅ 报错 | ✅ 报错 |
| 代码格式 | ✅ 自动修复 | ✅ 自动修复 |
| `any` 类型 | ✅ 禁止 | ⚠️ 警告（可调整） |

---

## 🔍 故障排查

### 类型检查失败

```bash
# 查看详细错误
npm run type-check

# 常见问题：
# 1. 路径别名不生效 → 检查 tsconfig.json paths 和 vite.config.ts alias 是否一致
# 2. 类型定义缺失 → npm install -D @types/xxx
```

### ESLint 报错

```bash
# 查看具体问题
npm run lint

# 自动修复
npm run lint:fix

# 忽略特定规则（谨慎使用）
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const data: any = ...;
```

### Prettier 格式不一致

```bash
# 自动格式化所有文件
npm run format

# 检查哪些文件需要格式化
npm run format:check
```

---

## 📚 扩展阅读

- [TypeScript 手册](https://www.typescriptlang.org/docs/)
- [ESLint 规则](https://eslint.org/docs/rules/)
- [Vitest 文档](https://vitest.dev/)
- [Prettier 配置](https://prettier.io/docs/en/options.html)
