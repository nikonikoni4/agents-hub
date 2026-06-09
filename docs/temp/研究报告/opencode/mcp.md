# OpenCode MCP 配置指南

## 配置文件位置

OpenCode 使用 `opencode.json` 作为主配置文件，位于项目根目录。

## 配置方式

{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "agents-hub": {
      "type": "remote",
      "url": "http://localhost:8765/mcp",
      "enabled": true
    }
  }
}