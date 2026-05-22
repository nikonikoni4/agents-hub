# Agent Bridge 架构方案对比研究报告

**研究日期**: 2026-05-23  
**研究目标**: 对比两种 agent_bridge 模块的架构设计方案  
**研究范围**: 架构设计、职责划分、扩展性、可维护性

---

## 一、背景与需求

### 1.1 项目背景

agents-hub 需要一个统一的 agent_bridge 模块，用于调用不同的 AI 平台 CLI 工具（Claude Code、Codex）。

### 1.2 核心需求

| 需求项 | 说明 |
|--------|------|
| **配置管理** | 角色配置固定（system prompt、skill 选择），作为初始化参数传入 |
| **输出模式** | 只采用流式输出 |
| **模块定位** | 纯执行层（启动 CLI、解析输出） |
| **会话管理** | session_id 由调用方传入 |
| **错误处理** | 留白，之后实现 |

### 1.3 期望的调用接口

```python
# 初始化
config = RoleConfig(
    platform="claude",
    system_prompt="你是一个代码审查专家",
    skills=["code-review"]
)
agent = AgentBridge(config)

# 流式调用
async for event in agent.execute_stream(user_prompt="审查代码", session_id="session_123"):
    print(event)
```

---

## 二、方案 A：继承架构

### 2.1 设计思路

**核心理念**：一个 Agent 类 = 完整的执行单元（包含执行 + 解析）

### 2.2 目录结构

```
backend/agent_bridge/
├── config.py          # RoleConfig（配置数据类）
├── base.py            # BaseAgent（抽象基类）
├── claude.py          # ClaudeAgent（继承 BaseAgent）
├── codex.py           # CodexAgent（继承 BaseAgent）
└── bridge.py          # AgentBridge（统一封装）
```

### 2.3 职责划分

| 模块 | 职责 |
|------|------|
| **BaseAgent** | 定义接口契约（抽象方法） |
| **ClaudeAgent** | 实现完整流程：构建命令 + 启动进程 + 解析输出 |
| **CodexAgent** | 实现完整流程：构建命令 + 启动进程 + 解析输出 |
| **AgentBridge** | 根据 platform 选择对应的 Agent，代理调用 |

### 2.4 关键特点

- 使用抽象类定义接口
- 每个平台一个完整的 Agent 类
- 通过继承实现多态
- 按平台分文件组织代码

---

## 三、方案 B：扁平化架构

### 3.1 设计思路

**核心理念**：执行和解析分离，通过组合而非继承实现复用

### 3.2 目录结构

```
backend/agent_bridge/
├── config.py          # RoleConfig
├── protocols.py       # Executor, Parser 协议定义
├── executors/
│   ├── claude.py      # ClaudeExecutor
│   └── codex.py       # CodexExecutor
├── parsers/
│   ├── claude.py      # ClaudeParser
│   └── codex.py       # CodexParser
└── bridge.py          # AgentBridge
```

### 3.3 职责划分

| 模块 | 职责 |
|------|------|
| **Executor** | 构建命令 + 启动进程 + 返回原始输出流 |
| **Parser** | 解析原始输出 + 转换为统一格式 |
| **AgentBridge** | 根据 platform 选择 Executor 和 Parser，组装流程 |

### 3.4 关键特点

- 使用 Protocol 定义接口（而非抽象类）
- 执行和解析分离为独立组件
- 通过组合实现功能
- 按职责分目录组织代码

---

