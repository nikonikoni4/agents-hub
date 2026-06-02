# mcp启动
测试：uvicorn agents_hub.api.app:app --host localhost --port 8000
# claude mcp添加方式
1. 通过CLI添加claude mcp add --transport http agents-hub -- http://localhost:8001/mcp
2. 直接在settings.json内添加:
```json
{
"mcpServers": {
    "agents-hub": {
      "type": "http",
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

# codex mcp添加方法
测试来源：当前本机 `codex mcp --help`、`codex mcp add --help`、`codex mcp remove --help`。

## 1. 通过 CLI 添加 HTTP MCP

Codex 对 streamable HTTP MCP server 使用 `--url` 参数：

```bash
codex mcp add agents-hub --url http://localhost:8001/mcp
```

如果 HTTP MCP 需要 bearer token，可以指定环境变量名：

```bash
codex mcp add agents-hub --url http://localhost:8001/mcp --bearer-token-env-var AGENTS_HUB_MCP_TOKEN
```

## 2. 通过 CLI 添加 stdio MCP

stdio MCP 不使用 `--url`，而是在 `--` 后面传启动命令：

```bash
codex mcp add my-server -- npx -y my-mcp-server
```

如果 stdio MCP 需要环境变量，可以用 `--env`：

```bash
codex mcp add my-server --env API_KEY=xxx -- npx -y my-mcp-server
```

## 3. 查看和删除

```bash
codex mcp list
codex mcp list --json
codex mcp get agents-hub
codex mcp get agents-hub --json
codex mcp remove agents-hub
```

## 4. 直接修改 config.toml（待校验）

Codex 的 MCP 配置由 `CODEX_HOME/config.toml` 管理。agents-hub 角色隔离场景下，`CODEX_HOME` 指向角色的 `work_root`，因此 Codex 角色的 MCP 配置理论上应写入：

```text
local_data/agents/<role_name>/work_root/config.toml
```

参考格式可能是：

```toml
[mcp_servers.agents-hub]
url = "http://localhost:8001/mcp"
```

stdio 参考格式可能是：

```toml
[mcp_servers.my-server]
command = "npx"
args = ["-y", "my-mcp-server"]
env = { API_KEY = "xxx" }
```

注意：上面的 TOML 直写格式还需要用 `codex mcp add` 在临时 `CODEX_HOME` 下生成一次后确认。当前可确定的是 CLI 添加方式；正式实现前不要只凭这个参考格式写死解析器。
