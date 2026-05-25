# Agents-hub 术语表

## 核心实体

### Agent（角色）
- 全局实体，不绑定特定项目
- 有头像、名称、能力标签、platform（claude/codex）、system_prompt、skills
- 配置存储在 `local_data/agents/<role_name>/role.json`

### Chat（对话/群聊）
- 绑定一个项目文件夹（project_path）
- 可以包含多个 Agent（群聊模式）或单个 Agent（单聊模式）
- MVP 阶段：一个群聊 = 一个项目文件夹

### Orchestrator（协调器）
- 群聊模式下的主 Agent
- 负责理解用户意图，拆解任务，分派给子 Agent
- 聚合子 Agent 产出并汇报结果

## 架构分层

### agent_bridge（纯执行层）
- 只负责调用 CLI 工具（Claude Code、Codex）
- 不关心业务逻辑、会话管理、权限控制
- 提供 `execute()` 和 `execute_stream()` 两个接口

### roles（角色管理层）
- 角色配置、skill 管理
- 为 agent_bridge 提供 RoleConfig

### chat（对话层）— 待设计
- 消息传递、群聊管理、Orchestrator 调度

## 配置分层

### role.json（业务配置）
- 面向用户/前端的配置
- 存储：name、avatar、abilities、platform、system_prompt、skills 等
- SSOT：角色数据唯一来源

### RoleConfig（系统内部配置）
- 面向 agent_bridge 的运行时配置
- 由 roles 模块从 role.json + 目录结构派生
- 包含：platform、codex_home / claude_config_dir
- 不包含 system_prompt 和 skills（由 CLI 从目录自动加载）

## 关键决策

1. 角色不绑定项目，群聊绑定项目
2. MVP 阶段先实现单 agent 配置，多 agent 交互模式后定
3. role.json 是业务配置，RoleConfig 是系统内部配置，由 role.json 派生
4. 一个角色绑定一个 platform（一对一），想要多平台就创建多个角色
5. system_prompt 不存 role.json，直接写进 CLAUDE.md（Claude）或 AGENTS.md（Codex），CLI 启动时自动加载
6. 角色发现机制：扫描 `local_data/agents/*/role.json`，不维护额外索引文件
7. RoleManager 负责角色 CRUD 和发现，Role 负责单个角色配置和构造 RoleConfig
