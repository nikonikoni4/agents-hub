# 启动文档

本文档说明如何启动 Agents Hub 系统，包括后端和前端的启动方式、端口配置以及多分支并行测试。

---

## 1. 快速启动

### 一键启动（推荐）

```powershell
# 使用默认端口（后端 8099，前端 5173）
.\dev.ps1

# 自定义端口
.\dev.ps1 -BackendPort 8100 -FrontendPort 5174

# 使用分支配置
.\dev.ps1 -Mode branch-feature-a
```

### 分别启动

**后端**：

```bash
# 方式一：直接运行（推荐）
python agents_hub/api/app.py

# 方式二：uvicorn（支持自定义端口）
uvicorn agents_hub.api.app:app --host 0.0.0.0 --port 8099
```

**前端**：

```bash
cd frontend
pnpm install  # 首次运行需要安装依赖
pnpm dev
```

---

## 2. 前置条件

### 后端

- Python >= 3.10
- 安装依赖：`pip install -e .`（在项目根目录执行）

### 前端

- Node.js >= 18
- 包管理器：pnpm（推荐）或 npm

---

## 3. 端口配置

### 默认端口

| 服务 | 默认端口 | 配置方式 |
|------|----------|----------|
| 后端 API | 8099 | `uvicorn --port <端口>` |
| 前端 Dev Server | 5173 | `VITE_DEV_PORT` 环境变量 |
| MCP Server | 8765 | `config.yaml` 中 `mcp_port` |

### 通过环境变量配置端口

前端支持通过环境变量配置端口，创建 `frontend/.env.local` 文件：

```env
VITE_DEV_PORT=5174
VITE_API_PORT=8100
```

或使用 `.env.[mode]` 文件：

```env
# frontend/.env.branch-a
VITE_DEV_PORT=5174
VITE_API_PORT=8100
```

然后通过 `pnpm dev --mode branch-a` 启动。

### 启动后验证

- 后端健康检查：`http://localhost:<端口>/health` → 返回 `{"status": "ok"}`
- 前端访问：`http://localhost:<端口>`

---

## 4. 多分支并行测试

当需要同时测试多个分支时，使用不同端口避免冲突。

### 端口分配建议

| 分支类型 | 前端端口 | 后端端口 |
|---------|---------|---------|
| 主分支/开发 | 5173 | 8099 |
| 功能分支 A | 5174 | 8100 |
| 功能分支 B | 5175 | 8101 |
| 功能分支 C | 5176 | 8102 |

### 创建分支配置

```bash
cd frontend
cp .env.branch-example .env.branch-<分支名>
```

编辑 `.env.branch-<分支名>`，修改端口：

```env
VITE_DEV_PORT=5174
VITE_API_PORT=8100
```

### 同时运行多个分支

```powershell
# 终端 1：分支 A
.\dev.ps1 -BackendPort 8099 -FrontendPort 5173

# 终端 2：分支 B
.\dev.ps1 -BackendPort 8100 -FrontendPort 5174 -Mode branch-b
```

或分别启动：

```bash
# 分支 A 后端
uvicorn agents_hub.api.app:app --port 8099

# 分支 A 前端
cd frontend && pnpm dev

# 分支 B 后端（另一个终端）
uvicorn agents_hub.api.app:app --port 8100

# 分支 B 前端（另一个终端）
cd frontend && pnpm dev --mode branch-b
```

---

## 5. Mock 数据配置

在 `frontend/.env.development` 或 `.env.local` 中设置：

```env
# 开启 Mock 模式
VITE_USE_MOCK=true

# 关闭 Mock 模式（连接真实后端）
VITE_USE_MOCK=false
```

### Mock 工作原理

- 前端使用 `mockableRequest` 函数封装 API 请求
- `VITE_USE_MOCK=true` 时，返回预定义的静态测试数据
- `VITE_USE_MOCK=false` 时，发送真实请求到后端

### Mock 数据位置

Mock 数据定义在各 API 文件中（`frontend/src/core/api/` 目录下），以 `MOCK_` 前缀命名的常量。

---

## 6. 前后端联调配置

### API 代理

前端开发服务器已配置代理，将 `/api` 请求转发到后端：

```typescript
// frontend/vite.config.ts
proxy: {
  '/api': {
    target: `http://localhost:${apiPort}`,  // 根据 VITE_API_PORT 自动配置
    changeOrigin: true,
  },
}
```

### WebSocket 连接

WebSocket URL 根据 `VITE_API_PORT` 自动构建，无需手动配置。

如需自定义，在 `.env.local` 中设置：

```env
VITE_WS_BASE_URL=ws://localhost:8100/api/v1
```

---

## 7. dev.ps1 脚本说明

`dev.ps1` 是项目根目录下的一键启动脚本。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-BackendPort` | int | 8099 | 后端 API 端口 |
| `-FrontendPort` | int | 5173 | 前端开发服务器端口 |
| `-Mode` | string | development | Vite 启动模式 |

### 示例

```powershell
# 默认配置
.\dev.ps1

# 自定义端口
.\dev.ps1 -BackendPort 8100 -FrontendPort 5174

# 使用分支配置
.\dev.ps1 -Mode branch-feature-a

# 组合使用
.\dev.ps1 -BackendPort 8100 -FrontendPort 5174 -Mode branch-feature-a
```

### 功能

- 自动备份和恢复 `.env.local`
- 后端后台启动，前端前台运行
- `Ctrl+C` 停止前端时自动清理后端

---

## 8. Pre-commit 配置

### Hook 位置

- **core.hookPath**: 使用默认设置（`.git/hooks/`）
- **pre-commit 脚本**: `项目根目录/.git/hooks/pre-commit`

> ⚠️ **重要**: 不要使用 husky 或 lint-staged，所有 pre-commit 检查统一通过 Makefile 执行。

### 检查命令

**后端检查**（Python 文件变更时触发）：
```bash
make format    # 自动修复格式
make lint      # 检查 lint
make type      # 类型检查
```

**前端检查**（frontend/ 目录文件变更时触发）：
```bash
make frontend-format  # 自动修复格式
make frontend-lint    # 检查 lint
make frontend-type    # 类型检查
make frontend-test    # 运行测试
```

### 手动运行完整检查

```bash
make check           # 后端完整检查
make frontend-check  # 前端完整检查
make all             # 前后端完整检查
```

---

## 9. 常见问题

### Q: 启动后端报错 `ModuleNotFoundError: No module named 'agents_hub'`

A: 确保在项目根目录执行 `pip install -e .` 安装开发模式依赖。

### Q: 前端启动后页面空白

A: 检查是否开启了 Mock 模式（`VITE_USE_MOCK=true`），或者确认后端已启动。

### Q: WebSocket 连接失败

A: 确认后端已启动，并检查 `VITE_API_PORT` 配置是否正确。WebSocket URL 会根据此端口自动构建。

### Q: Windows 上 Agent 执行失败

A: 使用 `python agents_hub/api/app.py` 启动后端，避免使用 `uvicorn --reload`。

### Q: 如何查看当前使用的端口？

A: 启动时 Vite 和 uvicorn 都会显示监听的端口。也可以访问 `http://localhost:<端口>/health` 验证后端。

### Q: 修改环境变量后不生效？

A: 重启开发服务器。Vite 不会热重载 `.env` 文件，需要重启才能生效。

### Q: 多个分支同时运行时如何区分？

A: 使用不同端口，并在浏览器中通过 `http://localhost:<端口>` 访问对应的分支。
