# 多分支并行测试指南

当需要同时测试多个分支时，可以通过环境变量配置不同端口避免冲突。

## 快速开始

### 1. 创建分支环境配置

```bash
cd frontend
cp .env.branch-example .env.branch-feature-a
```

### 2. 修改端口配置

编辑 `.env.branch-feature-a`：

```env
VITE_DEV_PORT=5174      # 前端开发服务器端口
VITE_API_PORT=8100      # 后端 API 端口
```

### 3. 启动后端（指定端口）

```bash
# 分支 A（默认端口）
python agents_hub/api/app.py

# 分支 B（自定义端口）
uvicorn agents_hub.api.app:app --port 8100
```

### 4. 启动前端（指定模式）

```bash
cd frontend

# 分支 A（使用默认配置）
pnpm dev

# 分支 B（使用分支配置）
pnpm dev --mode branch-feature-a
```

## 端口分配建议

| 分支类型 | 前端端口 | 后端端口 |
|---------|---------|---------|
| 主分支/开发 | 5173 | 8099 |
| 功能分支 A | 5174 | 8100 |
| 功能分支 B | 5175 | 8101 |
| 功能分支 C | 5176 | 8102 |

## 配置文件说明

- `.env.development` - 默认开发配置（pnpm dev 默认使用）
- `.env.branch-example` - 分支配置示例（可提交到 git）
- `.env.branch-<name>` - 具体分支配置（已加入 .gitignore，不会提交）

## WebSocket 自动配置

WebSocket URL 会根据 `VITE_API_PORT` 自动构建，无需手动配置。

如需自定义，可在分支配置中添加：

```env
VITE_WS_BASE_URL=ws://localhost:8100/api/v1
```

## 同时运行多个分支

```bash
# 终端 1：分支 A
cd /path/to/branch-a
python agents_hub/api/app.py  # 端口 8099
cd frontend && pnpm dev       # 端口 5173

# 终端 2：分支 B
cd /path/to/branch-b
uvicorn agents_hub.api.app:app --port 8100  # 端口 8100
cd frontend && pnpm dev --mode branch-b     # 端口 5174
```

## 常见问题

### Q: 如何查看当前使用的端口？

启动时 Vite 会显示：
```
  VITE v5.x.x  ready in 300ms

  ➜  Local:   http://localhost:5174/
```

### Q: 修改配置后不生效？

1. 确认环境变量名正确（VITE_ 前缀）
2. 重启开发服务器（Vite 不会热重载 .env 文件）
3. 检查是否有语法错误

### Q: 后端端口如何查看？

访问健康检查端点：`http://localhost:<端口>/health`

返回 `{"status": "ok"}` 表示正常。
