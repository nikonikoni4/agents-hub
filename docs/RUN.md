# 启动文档

本文档说明如何启动 Agents Hub 系统，包括后端和前端的启动方式、Mock 数据配置以及端口说明。

---

## 1. 启动后端

### 前置条件

- Python >= 3.10
- 安装依赖：`pip install -e .`（在项目根目录执行）

### 启动方式

**方式一：直接运行（推荐开发时使用）**

```bash
python agents_hub/api/app.py
```

**方式二：使用 uvicorn（支持热重载）**

```bash
uvicorn agents_hub.api.app:app --reload --host 0.0.0.0 --port 8099
```

> ⚠️ **注意**：在 Windows 上使用 `--reload` 可能会导致子进程（如 Agent 执行）失败。如果需要执行 Agent 任务，建议使用方式一。

### 启动后验证

访问健康检查端点：`http://localhost:8099/health`

返回 `{"status": "ok"}` 表示启动成功。

---

## 2. 启动前端

### 前置条件

- Node.js >= 18
- 包管理器：pnpm（推荐）或 npm

### 启动方式

```bash
cd frontend
pnpm install  # 首次运行需要安装依赖
pnpm dev
```

或者使用 npm：

```bash
cd frontend
npm install
npm run dev
```

### 启动后验证

浏览器访问：`http://localhost:5173`

---

## 3. 前端 Mock 数据配置

### 开启 Mock 模式

在 `frontend/.env.development` 文件中设置：

```env
VITE_USE_MOCK=true
```

### 关闭 Mock 模式（连接真实后端）

```env
VITE_USE_MOCK=false
```

### Mock 工作原理

- 前端使用 `mockableRequest` 函数封装 API 请求
- 当 `VITE_USE_MOCK=true` 时，返回预定义的静态测试数据
- 当 `VITE_USE_MOCK=false` 时，发送真实请求到后端

**代码示例**：

```typescript
import { mockableRequest } from '@/core/api/client';

export async function listRoles(): Promise<Role[]> {
  return mockableRequest(
    () => apiClient.get<Role[]>('/roles'),
    MOCK_ROLES  // 预定义的测试数据
  );
}
```

### Mock 数据位置

Mock 数据定义在各 API 文件中（`frontend/src/core/api/` 目录下），以 `MOCK_` 前缀命名的常量。

---

## 4. 端口说明

| 服务 | 默认端口 | 配置文件 | 配置项 |
|------|----------|----------|--------|
| **后端 API** | 8099 | `agents_hub/api/app.py` | `uvicorn.run(..., port=8099)` |
| **前端 Dev Server** | 5173 | `frontend/vite.config.ts` | `server.port: 5173` |
| **MCP Server** | 8765 | `agents_hub/config/config.py` | `mcp_port: 8765` |

### 修改端口

**修改后端端口**：

编辑 `agents_hub/api/app.py`：

```python
uvicorn.run(app, host="0.0.0.0", port=8099, reload=False)  # 修改这里的 8099
```

**修改前端端口**：

编辑 `frontend/vite.config.ts`：

```typescript
server: {
  port: 5173,  // 修改这里的 5173
  proxy: {
    '/api': {
      target: 'http://localhost:8099',  // 同步修改代理目标端口
      changeOrigin: true,
    },
  },
},
```

**修改 MCP 端口**：

编辑 `agents_hub/config/config.py` 中的默认配置：

```python
_default_config: dict = {
    "mcp_port": 8765,  # 修改这里的 8765
}
```

或者通过 `config.yaml` 配置文件覆盖（开发环境路径：`local_data/config/config.yaml`）：

```yaml
mcp_port: 9999
```

---

## 5. 前后端联调配置

### API 代理

前端开发服务器已配置代理，将 `/api` 请求转发到后端：

```typescript
// frontend/vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8099',
    changeOrigin: true,
  },
},
```

### WebSocket 连接

WebSocket 连接地址在 `frontend/.env.development` 中配置：

```env
VITE_WS_BASE_URL=ws://localhost:8099/api/v1
```

---

## 6. Pre-commit 配置

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

## 7. 常见问题

### Q: 启动后端报错 `ModuleNotFoundError: No module named 'agents_hub'`

A: 确保在项目根目录执行 `pip install -e .` 安装开发模式依赖。

### Q: 前端启动后页面空白

A: 检查是否开启了 Mock 模式（`VITE_USE_MOCK=true`），或者确认后端已启动。

### Q: WebSocket 连接失败

A: 确认后端已启动，并检查 `VITE_WS_BASE_URL` 配置是否正确。

### Q: Windows 上 Agent 执行失败

A: 使用方式一（`python agents_hub/api/app.py`）启动后端，避免使用 `--reload`。
