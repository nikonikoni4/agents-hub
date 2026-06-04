# Docker 沙箱隔离设计

**日期**：2026-06-02  
**状态**：设计阶段  
**目标**：为 agents-hub 提供可配置的 Docker 沙箱能力，实现 Agent 级别的文件系统隔离

---

## 一、背景与目标

### 1.1 核心问题

AI Agent（Claude Code、Codex）运行时存在权限管理问题：
- 应用层权限检查可以被绕过（`--dangerously-skip-permissions`）
- 需要可靠的内核级隔离方案防止 Agent 访问未授权文件

### 1.2 设计目标

1. **可配置的沙箱策略**：用户可以为每个 Agent 在每个群聊中独立配置是否使用 Docker
2. **非侵入式架构**：扩展现有 `AgentBridge` 架构，不修改核心业务逻辑
3. **最小资源开销**：Docker 容器本身开销可忽略（1-2 MB/容器）
4. **透明的网络访问**：容器内 Agent 可以访问本地 MCP 服务和互联网

---

## 二、核心设计

### 2.1 容器粒度

**Key = (agent_name, group_chat_id)**

- 每个 Agent 在每个群聊中拥有独立的 Docker 容器
- 最细粒度隔离，最大安全性
- 资源开销可忽略（1-2 MB/容器）

**示例**：
```
容器 1: ("小李", "群聊A") → container-小李-群聊A
容器 2: ("小赵", "群聊A") → container-小赵-群聊A  
容器 3: ("小李", "群聊B") → container-小李-群聊B
```

### 2.2 启动条件

Docker 沙箱只在**同时满足两个条件**时启用：

1. **配置启用**：`agent_member.json` 中 `use_docker = true`
2. **路径隔离**：`agent.cwd ≠ group_chat.path`（需要隔离）

**判断逻辑**：
```python
if use_docker == True and agent_cwd != group_chat_path:
    # 使用 Docker 执行
else:
    # 本地执行
```

**设计理由**：
- 如果 Agent 的工作目录就是群聊项目路径，Docker 隔离没有意义
- 只有当 Agent 在不同路径工作时（如 worktree），才需要隔离

### 2.3 生命周期管理

#### 懒启动（Lazy Start）
- 第一次调用时才创建容器
- 避免预占用资源

#### 延迟销毁（Delayed Cleanup）
- 容器空闲后等待 **10 分钟** 再销毁
- 资源开销小，等待时间可以更长
- 避免频繁重启容器

#### 引用计数
```python
每次 execute() → ref_count++
执行完成 → ref_count--
ref_count == 0 且超时 → 销毁容器
```

---

## 三、架构设计

### 3.1 模块结构

```
agents_hub/
├── core/
│   └── agent/
│       └── base_agent.py          # ← 添加 Docker 配置校验
│
└── agent_bridge/
    ├── bridge.py                  # ← 根据 use_docker 选择 Executor
    ├── executors/
    │   ├── claude.py              # ClaudeExecutor (本地)
    │   ├── codex.py               # CodexExecutor (本地)
    │   ├── docker_base.py         # ← 新增：DockerExecutor 基类
    │   ├── docker_claude.py       # ← 新增：DockerClaudeExecutor
    │   └── docker_codex.py        # ← 新增：DockerCodexExecutor
    │
    └── docker/                    # ← 新增：Docker 管理模块
        ├── manager.py             # DockerManager（容器池管理）
        ├── container.py           # DockerContainer（单个容器抽象）
        └── models.py              # 数据模型
```

### 3.2 执行流程

```
用户消息 → GroupChat
  ↓
Agent.run() 接收消息
  ↓
Agent._process_message()
  ↓
  ├─ _validate_docker_config()  ← 校验点：检查 use_docker 配置合理性
  │   ├─ use_docker == False → 通过
  │   ├─ use_docker == True && cwd != group_path → 通过
  │   └─ use_docker == True && cwd == group_path → 抛出 DockerConfigError
  ↓
Agent.execute(prompt, use_docker, group_chat_id)
  ↓
AgentBridge.execute(use_docker=True/False)
  ↓
  ├─ use_docker == False → ClaudeExecutor (本地)
  │                         ├─ 应用层权限检查
  │                         └─ 本地子进程执行
  │
  └─ use_docker == True → DockerClaudeExecutor (容器)
       ↓
     DockerManager.get_or_create_container(agent_name, group_chat_id)
       ↓
     docker exec -w /workspace \
       -e CLAUDE_CONFIG_DIR=/home/ai-user/.claude \
       --dangerously-skip-permissions \  ← 强制跳过权限
       container-{agent}-{group} \
       claude "prompt"
```

---

## 四、关键实现细节

### 4.0 Docker Engine 可用性检查（方案 C）

**策略**：懒检查 + 清晰提示

#### 设计原则
1. **不在初始化时检查**：`DockerManager` 初始化时不检查 Docker Engine
2. **执行时懒检查**：每次 `get_or_create_container()` 时检查
3. **带缓存避免频繁检查**：30 秒 TTL，减少 `docker info` 调用
4. **清晰的错误提示**：告知用户问题和解决方案
5. **不自动降级**：不会默默切换到本地执行（安全优先）

#### 检查时机

```
Agent._process_message()
  ↓
Agent.execute(use_docker=True)
  ↓
AgentBridge.execute_stream(use_docker=True)
  ↓
DockerClaudeExecutor.execute()
  ↓
DockerManager.get_or_create_container()
  ↓
_is_docker_running() 检查（带 30 秒缓存）
  ↓ False
  ↓
抛出 DockerNotAvailableError
  ↓
Agent._process_message() 捕获
  ↓
agent_call_manager.update_status(FAILED)
  ↓
返回错误消息给用户
```

#### 错误提示示例

```
Docker Engine 未运行，无法启动沙箱容器。

解决方案：
1. 启动 Docker Desktop
2. 或在 agent_member.json 中设置 use_docker=false
   路径：local_data/teams/.../e2e_demo_chat/agent_member.json
   修改 '小李' 的 use_docker 字段
```

#### 为什么不选择其他方案？

**方案 A（严格模式）**：启动时检查，未运行则完全阻止
- ❌ 用户必须先启动 Docker 再启动应用
- ❌ Docker Desktop 可以在运行时启动，但应用无法感知

**方案 B（兼容模式）**：自动降级为本地执行
- ❌ 用户以为有沙箱保护，实际没有（安全风险）
- ❌ 日志中有警告，但用户可能不注意

**方案 C（懒检查）**：执行时检查 + 清晰提示 ✅
- ✅ Docker Desktop 可以在运行时启动
- ✅ 不会默默降级，安全可靠
- ✅ 错误提示清晰，用户知道如何解决

---

### 4.1 Agent 层校验

**位置**：`agents_hub/core/agent/base_agent.py`

```python
async def _process_message(self, msg: AgentMessage, prompt: str) -> AgentResult:
    """处理一条入站消息"""
    
    # 1. Docker 配置校验（新增）
    self._validate_docker_config()
    
    # 2. 原有逻辑
    self.agent_call_manager.update_status(msg.call_id, CallStatus.RUNNING)
    # ...

def _validate_docker_config(self):
    """
    校验 Docker 配置
    
    规则：如果配置了 use_docker=True，必须满足路径隔离条件
    
    Raises:
        DockerConfigError: Docker 配置不合理
    """
    session_info = self.group_chat_context.agent_member_info.get(self.name)
    if not session_info:
        return
    
    use_docker = getattr(session_info, 'use_docker', False)
    if not use_docker:
        return  # 未启用 Docker，无需校验
    
    # 启用了 Docker，检查路径条件
    agent_cwd = session_info.cwd
    
    # 获取群聊的项目路径（从 GroupChatRepository.project_path）
    group_chat_path = self.group_chat_context.repository.project_path
    
    if self._is_same_path(agent_cwd, group_chat_path):
        raise DockerConfigError(
            agent_name=self.name,
            group_chat_id=self.group_chat_context.group_chat_id,
            reason=(
                f"Docker 隔离不必要：Agent CWD 与群聊路径相同。\n"
                f"  Agent CWD: {agent_cwd}\n"
                f"  GroupChat Path: {group_chat_path}\n"
                f"建议：将 agent_member.json 中的 use_docker 改为 false"
            )
        )
```

### 4.2 权限策略

**Docker 模式下强制跳过权限检查**

**理由**：
- Docker 容器提供内核级文件系统隔离
- 容器内应该有完整权限，由挂载策略控制访问范围
- 应用层权限检查变得冗余

**实现**：
```python
# docker_claude.py
def _build_command(self, prompt, config, session_id):
    cmd = [
        "claude",
        "--dangerously-skip-permissions",  # ← 强制添加
        "--print",
        "--verbose",
        "--output-format", "stream-json",
        "--include-partial-messages",
    ]
    # ...
    return cmd

# docker_codex.py
def _build_command(self, prompt, config, session_id):
    cmd = [
        "codex",
        "--dangerously-bypass-approvals-and-sandbox",  # ← 强制添加
        "--print",
        "--output-format", "stream-json",
    ]
    # ...
    return cmd
```

### 4.3 容器挂载策略

**每个容器只挂载自己需要的目录（最小权限原则）**

```bash
# 容器：(小李, 群聊A)
docker run -d --name container-小李-群聊A \
  -v "<小李的work_root>:/home/ai-user/.claude:rw" \  # Agent 配置
  -v "<群聊A的cwd>:/workspace:rw" \                    # 工作目录
  -v "<project/.git>:/repo-git:rw" \                  # Git 元数据
  --network host \                                    # 透明网络访问
  ai-tools:latest \
  sleep infinity

# 执行时
docker exec \
  -w /workspace \                                     # 工作目录
  -e CLAUDE_CONFIG_DIR=/home/ai-user/.claude \        # 配置路径
  container-小李-群聊A \
  claude --dangerously-skip-permissions "prompt"
```

**网络策略**：使用 `--network host`
- 容器内可以访问 `localhost:8080` 等本地 MCP 服务
- 可以访问互联网（WebSearch 等功能）
- 文件系统仍然完全隔离（核心目标）

### 4.4 DockerManager 容器池管理

```python
# agent_bridge/docker/manager.py
import time

class DockerManager:
    def __init__(self):
        # 容器池：(agent_name, group_chat_id) → DockerContainer
        self._containers: dict[tuple[str, str], DockerContainer] = {}
        
        # 清理任务
        self._cleanup_tasks: dict[tuple[str, str], asyncio.Task] = {}
        
        # Docker Engine 状态缓存（避免频繁检查）
        self._docker_status_cache: tuple[bool, float] = (False, 0)
        self._cache_ttl = 30  # 缓存 30 秒
    
    async def get_or_create_container(
        self, 
        agent_name: str, 
        group_chat_id: str,
        work_root: str,
        cwd: str
    ) -> DockerContainer:
        """获取或创建容器（懒启动 + 懒检查）"""
        key = (agent_name, group_chat_id)
        
        # 1. 懒检查：Docker Engine 是否运行
        if not self._is_docker_running():
            raise DockerNotAvailableError(
                agent_name=agent_name,
                group_chat_id=group_chat_id,
                message=(
                    "Docker Engine 未运行，无法启动沙箱容器。\n\n"
                    "解决方案：\n"
                    "1. 启动 Docker Desktop\n"
                    "2. 或在 agent_member.json 中设置 use_docker=false\n"
                    f"   路径：local_data/teams/.../agent_member.json\n"
                    f"   修改 '{agent_name}' 的 use_docker 字段"
                )
            )
        
        # 2. 取消延迟销毁任务（如果存在）
        if key in self._cleanup_tasks:
            self._cleanup_tasks[key].cancel()
            del self._cleanup_tasks[key]
        
        # 3. 容器是否存在？
        if key in self._containers:
            # 复用现有容器
            return self._containers[key]
        
        # 4. 创建新容器
        self._containers[key] = await self._create_container(
            agent_name, group_chat_id, work_root, cwd
        )
        
        return self._containers[key]
    
    async def release_container(
        self, 
        agent_name: str, 
        group_chat_id: str
    ):
        """释放容器（启动延迟销毁）"""
        key = (agent_name, group_chat_id)
        
        async def cleanup():
            await asyncio.sleep(10 * 60)  # 等待 10 分钟
            
            if key in self._containers:
                container = self._containers[key]
                
                # 停止并删除容器
                await asyncio.create_subprocess_exec(
                    "docker", "stop", container.name
                )
                await asyncio.create_subprocess_exec(
                    "docker", "rm", container.name
                )
                
                del self._containers[key]
                logger.info(f"容器 {container.name} 已销毁（10分钟空闲）")
        
        self._cleanup_tasks[key] = asyncio.create_task(cleanup())
    
    def _is_docker_running(self) -> bool:
        """检查 Docker Engine 是否运行（带缓存，避免频繁检查）"""
        now = time.time()
        cached_status, cached_time = self._docker_status_cache
        
        # 缓存有效（30 秒内）
        if now - cached_time < self._cache_ttl:
            return cached_status
        
        # 重新检查 Docker Engine
        try:
            result = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False
            )
            status = result.returncode == 0
        except Exception:
            status = False
        
        # 更新缓存
        self._docker_status_cache = (status, now)
        return status
    
    async def _create_container(
        self, 
        agent_name: str, 
        group_chat_id: str,
        work_root: str,
        cwd: str
    ) -> DockerContainer:
        """创建新容器"""
        container_name = f"container-{agent_name}-{group_chat_id}"
        
        # 检查容器是否已存在（避免重复创建错误）
        if await self._container_exists(container_name):
            # 先删除旧容器
            await asyncio.create_subprocess_exec("docker", "rm", "-f", container_name)
        
        # 构建 docker run 命令（不使用 --rm）
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-v", f"{work_root}:/home/ai-user/.claude:rw",
            "-v", f"{cwd}:/workspace:rw",
            "-v", f"{self._get_git_dir()}:/repo-git:rw",
            "--network", "host",
            "ai-tools:latest",
            "sleep", "infinity"  # 容器持续运行
        ]
        
        # 启动容器
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.wait()
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise DockerStartError(
                container_name=container_name,
                reason=stderr.decode()
            )
        
        return DockerContainer(container_name, agent_name, group_chat_id)
    
    async def _container_exists(self, container_name: str) -> bool:
        """检查容器是否已存在"""
        process = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a",
            "--filter", f"name={container_name}",
            "--format", "{{.Names}}",
            stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return bool(stdout.strip())
```

---

## 五、数据模型

### 5.1 agent_member.json 扩展

```json
{
  "Leader": {
    "main_session": "2f644498-f847-4d4b-a735-a2f805ff1277",
    "btw_session": [],
    "context_state": {
      "last_loaded_compact_index": 0,
      "last_loaded_message_index": 0
    },
    "token": "tok_89ad01cd57b711db8da464356fef5035",
    "cwd": "local_data",
    "use_docker": false  ← 新增字段
  },
  "小李": {
    "main_session": "69bfee3c-1111-4db0-9e39-ddb71a16f920",
    "btw_session": [],
    "context_state": {
      "last_loaded_compact_index": 0,
      "last_loaded_message_index": 0
    },
    "token": "tok_ad5a0ff8577d0d9d97e5a144f4e0ce24",
    "cwd": "explore/worktree-feature-a",
    "use_docker": true  ← 新增字段
  }
}
```

### 5.2 新增异常类

```python
# agents_hub/core/foundation/exceptions.py

class DockerConfigError(ValidationError):
    """Docker 配置错误"""
    
    def __init__(self, agent_name: str, group_chat_id: str, reason: str):
        self.agent_name = agent_name
        self.group_chat_id = group_chat_id
        self.reason = reason
        super().__init__(
            f"Agent '{agent_name}' 在群聊 '{group_chat_id}' 中的 Docker 配置不合理：\n{reason}"
        )

class DockerNotAvailableError(ExternalServiceError):
    """Docker Engine 不可用"""
    
    def __init__(self, agent_name: str, group_chat_id: str, message: str):
        self.agent_name = agent_name
        self.group_chat_id = group_chat_id
        super().__init__(
            service="Docker",
            reason=message
        )

class DockerStartError(ExternalServiceError):
    """Docker 容器启动失败"""
    
    def __init__(self, container_name: str, reason: str):
        self.container_name = container_name
        self.reason = reason
        super().__init__(
            service="Docker",
            reason=f"容器 '{container_name}' 启动失败：{reason}"
        )
```

---

## 六、安全性分析

### 6.1 隔离边界

| 场景 | 路径关系 | use_docker | 执行方式 | 权限 | 隔离性 |
|------|---------|-----------|---------|------|--------|
| Leader 协调 | CWD == 项目路径 | false | 本地执行 | 应用层权限检查 | 无隔离 |
| Leader 协调 | CWD == 项目路径 | true | ❌ 配置错误 | - | - |
| Worker 开发 | CWD ≠ 项目路径 | true | Docker 执行 | 跳过权限 + 内核隔离 | ✅ 完全隔离 |
| Worker 开发 | CWD ≠ 项目路径 | false | 本地执行 | 应用层权限检查 | 无隔离 |

### 6.2 隔离验证

**测试场景**：容器内 Agent 尝试访问主仓库文件

```bash
# 主仓库有文件：MAIN_REPO_ONLY.md
# 容器只挂载了 worktree

# 测试 1：读取 worktree 文件
docker exec container-小李-群聊A claude "Read README.md"
✅ 成功

# 测试 2：读取主仓库文件
docker exec container-小李-群聊A claude "Read MAIN_REPO_ONLY.md"
❌ 失败：文件不存在（Docker 隔离有效）

# 测试 3：相对路径跳出
docker exec container-小李-群聊A claude "Read ../../../MAIN_REPO_ONLY.md"
❌ 失败：文件不存在（无法跳出容器）
```

**结论**：
- ✅ Docker 提供内核级隔离，应用层无法突破
- ✅ 即使使用 `--dangerously-skip-permissions`，仍然无法访问未挂载的文件
- ✅ 相对路径跳出无效

---

## 七、资源开销评估

### 7.1 单个容器开销

| 资源类型 | 空闲容器 | 运行 Claude Code 时 |
|---------|---------|-------------------|
| **内存** | 1-2 MB (仅容器进程) | 200-500 MB (主要是 Claude Code 进程) |
| **CPU** | 0% | 根据任务（10%-100%） |
| **磁盘** | 0 MB (使用挂载卷) | 临时文件 < 100 MB |
| **启动时间** | 200-500 ms | - |

**说明**：
- **容器本身**开销极小（1-2 MB），可忽略
- **主要开销**来自 Claude Code 进程（200-500 MB）
- 无论是本地执行还是 Docker 执行，Claude Code 进程开销相同

### 7.2 实际场景

#### 场景 1：3 个群聊，每个 2 个 Docker Agent
```
容器数量：3 × 2 = 6 个
纯容器开销：6 × 2 MB = 12 MB 内存
Claude Code 进程：6 × 300 MB = 1.8 GB 内存（执行时）

总计：~12 MB (空闲) / ~1.8 GB (执行时)
```

#### 场景 2：10 个群聊，50% 使用 Docker
```
容器数量：10 × 1 = 10 个（平均每个群聊 1 个 Docker Agent）
纯容器开销：10 × 2 MB = 20 MB 内存
延迟销毁后：~5 个活跃容器 = 10 MB 内存

总计：~10-20 MB
```

**结论**：容器本身开销完全可忽略，主要开销来自 Claude Code 进程

### 7.3 Docker Engine 检查开销

**检查频率**：
- 每次 `get_or_create_container()` 调用时检查
- 带缓存（30 秒 TTL）

**单次检查开销**：
- `docker info` 命令：~50ms
- 缓存命中：0ms

**实际影响**：
- 平均每 30 秒检查一次
- 对用户体验无感知

---

## 八、实施计划

### Phase 1: Docker 基础设施（1 周）
- [ ] 实现 `DockerManager`（容器池管理）
- [ ] 实现 `DockerContainer`（单容器抽象）
- [ ] 实现 `DockerExecutor` 基类
- [ ] 单元测试：容器创建、销毁、引用计数

### Phase 2: Executor 集成（1 周）
- [ ] 实现 `DockerClaudeExecutor`
- [ ] 实现 `DockerCodexExecutor`
- [ ] `AgentBridge` 选择逻辑
- [ ] 集成测试：本地 vs Docker 执行

### Phase 3: Agent 层集成（3 天）
- [ ] `Agent._validate_docker_config()` 实现
- [ ] `agent_member.json` 数据模型扩展
- [ ] 异常类实现
- [ ] 集成测试：配置校验

### Phase 4: 端到端测试（3 天）
- [ ] 测试隔离效果（访问主仓库文件）
- [ ] 测试 MCP 服务访问
- [ ] 测试资源清理（延迟销毁）
- [ ] 性能测试（启动时间、资源占用）

### Phase 5: 文档与部署（2 天）
- [ ] 用户文档：如何配置 Docker 模式
- [ ] 开发文档：如何扩展 Executor
- [ ] 更新 ARCHITECTURE.md
- [ ] 部署到测试环境

---

## 九、未来扩展

### 9.1 容器镜像优化
- 使用 Alpine 基础镜像（更小）
- 预安装常用工具（git、Node.js、Python）

### 9.2 资源限制
```bash
docker run -d \
  --memory="512m" \    # 限制内存
  --cpus="1.0" \       # 限制 CPU
  ai-tools:latest
```

### 9.3 多容器编排
- 支持 Docker Compose（多服务协作）
- 支持 Kubernetes（云原生部署）

### 9.4 安全增强
- 只读挂载（`:ro`）对于不需要修改的目录
- Seccomp profile（限制系统调用）
- AppArmor/SELinux profile

---

## 十、参考资料

- [Docker 沙箱隔离研究报告](../../temp/研究报告/docker/docker-sandbox-report.md)
- [Docker 官方文档](https://docs.docker.com/)
- [Linux Namespace](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [现有 AgentBridge 架构](../../specs/2026-05-23-agent-bridge.md)
