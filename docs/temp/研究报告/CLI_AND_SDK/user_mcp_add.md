## MCP 服务器配置指南

### 配置文件位置

- **用户级配置**: `C:\Users\15535\.claude.json`（所有项目共享）
- **项目级配置**: `C:\Users\15535\.claude.json` 中按项目路径存储（如 `D:/desktop/软件开发/websearch`）

### 作用域说明

| 作用域 | 参数 | 适用范围 | 存储位置 |
|--------|------|----------|----------|
| 本地/local | `-s local` | 仅当前项目 | 项目路径下的 mcpServers |
| 用户/user | `-s user` | 所有项目 | 用户目录 .claude.json |

### 添加命令

#### 项目级别（默认）
```bash
claude mcp add <name> <url> -t http -H "Header: Value"
```

#### 用户级别（全局）
```bash
claude mcp add <name> <url> -t http -s user -H "Header: Value"
```

### 删除命令

```bash
# 删除项目级别
claude mcp remove <name> -s local

# 删除用户级别
claude mcp remove <name> -s user
```

### 查看配置

```bash
# 列出所有 MCP 服务器
claude mcp list

# 查看详情
claude mcp get <name>
```

### 示例：添加阿里云搜索 MCP

```bash
# 添加到用户级别（全局可用）
claude mcp add iqs-mcp-server-search https://iqs-mcp.aliyuncs.com/mcp-servers/iqs-mcp-server-search -t http -s user -H "X-API-Key: YOUR_API_KEY"
```
