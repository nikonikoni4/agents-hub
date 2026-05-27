# DeerFlow 多Agent架构与消息机制

> Deep Exploration and Efficient Research Flow - 字节跳动开源的 Super Agent Harness
> 调研时间: 2026-05-24 | 基于 [DeerFlow](https://github.com/bytedance/deer-flow) 官方仓库分析

---

## 1. 项目概览

**DeerFlow 2.0** 是一次彻底重写。它把 **sub-agents**、**memory** 和 **sandbox** 组织在一起，再配合可扩展的 **skills**，让 agent 可以完成几乎任何事情。

- **技术栈**: Python 3.12+, FastAPI, LangGraph, LangChain, Next.js, TypeScript, SQLite/PostgreSQL, Docker, Nginx
- **核心特性**: Skills 与 Tools 系统、Sub-Agents 并行执行、Sandbox 与文件系统隔离、Context Engineering、长期记忆管理
- **支持的IM渠道**: 飞书(流式)、企业微信(流式)、Slack、Telegram、Discord、钉钉、微信公众号

## 2. 整体架构

DeerFlow 采用 **Harness/App 两层分离架构**，依赖方向单向：App 可以 import deerflow，但 deerflow 绝不能 import app。

```
前端层 (Next.js, 端口3000)
    ↓
Nginx 统一入口 (端口2026)
    ↓ /api/*
Gateway API 层 (FastAPI, 端口8001)
    ├── threads 路由
    ├── runs 路由
    ├── memory 路由
    ├── skills 路由
    └── 其他 12 个路由
    ↓
IM 渠道层 (飞书/企微/Slack/Telegram/...) → MessageBus
    ↓
Harness 核心层 (deerflow)
    ├── Agents 模块 (Lead Agent + SubAgents + 14+ Middlewares)
    ├── Runtime 运行时 (RunManager, StreamBridge, RunJournal)
    └── 支撑模块 (Skills, Tools, Sandbox, Memory, MCP)
    ↓
持久化层 (SQLite/PostgreSQL + LangGraph Checkpointer)
```

## 3. Nginx 与 Gateway

### 基础概念

- **Nginx** — 反向代理/流量调度：统一接收所有请求，根据 URL 路径转发给不同后端服务。类比：大楼前台。
- **Gateway** — API 网关：处理认证、鉴权、CSRF 防护、路由分发等公共逻辑。类比：公司门卫。

### 分工

**Nginx 管基础设施**（端口转发、负载均衡、SSL），**Gateway 管业务逻辑**（认证、鉴权、路由到具体处理函数）。

### 请求流转

```
浏览器 → Nginx(:2026) → /api/* → Gateway(:8001) → AuthMiddleware → CSRFMiddleware → Router → Handler
                       → 其他   → 前端(:3000)
```

### DeerFlow 中的 Nginx 配置 (`docker/nginx/nginx.local.conf`)

核心逻辑：以 `/api/` 开头的请求转给 Gateway，其他请求转给前端。

```nginx
upstream gateway { server 127.0.0.1:8001; }
upstream frontend { server 127.0.0.1:3000; }

server {
    listen 2026;

    # /api/langgraph/* → 去掉前缀后转给 Gateway
    location /api/langgraph/ {
        rewrite ^/api/langgraph/(.*) /api/$1 break;
        proxy_pass http://gateway;
    }

    # /api/models, /api/memory, /api/skills → 转给 Gateway
    location /api/models { proxy_pass http://gateway; }
    location /api/memory { proxy_pass http://gateway; }
    location /api/skills { proxy_pass http://gateway; }

    # /api/threads/*/uploads → 允许 100M 上传
    location ~ ^/api/threads/[^/]+/uploads {
        proxy_pass http://gateway;
        client_max_body_size 100M;
    }

    # 兜底：其他 /api/* 全转给 Gateway
    location /api/ { proxy_pass http://gateway; }

    # 其他所有请求 → 转给前端
    location / { proxy_pass http://frontend; }
}
```

### Gateway 实现 (`backend/app/gateway/app.py`)

Gateway 是一个 FastAPI 应用，核心职责：注册中间件 + 注册路由。

```python
def create_app() -> FastAPI:
    app = FastAPI(title="DeerFlow API Gateway")

    # 注册中间件（请求进来时按顺序执行）
    app.add_middleware(AuthMiddleware)   # 1. 验证身份
    app.add_middleware(CSRFMiddleware)   # 2. CSRF 防护
    app.add_middleware(CORSMiddleware)   # 3. 跨域处理

    # 注册路由
    app.include_router(auth.router)         # /api/v1/auth/*
    app.include_router(thread_runs.router)  # /api/threads/*/runs/*
    app.include_router(models.router)       # /api/models/*
    app.include_router(mcp.router)          # /api/mcp/*
    app.include_router(memory.router)       # /api/memory/*
    app.include_router(skills.router)       # /api/skills/*
    # ... 还有 agents, uploads, artifacts 等路由
    return app
```

### AuthMiddleware (`auth_middleware.py`)

```python
class AuthMiddleware:
    async def dispatch(self, request, call_next):
        # 1. 公开路径直接放行
        if _is_public(request.url.path):
            return await call_next(request)
        # 2. 没有 access_token cookie → 401
        if not request.cookies.get("access_token"):
            return JSONResponse(status_code=401)
        # 3. 验证 JWT，解析出用户
        user = await get_current_user_from_request(request)
        # 4. 把用户信息挂到 request 上
        request.state.user = user
        return await call_next(request)
```

### 一次完整请求的旅程

```
浏览器 → POST /api/threads/123/runs/stream
  → Nginx (匹配 /api/ → 转给 gateway)
  → Gateway → AuthMiddleware (检查cookie → 验证JWT → 解析用户)
  → Router (匹配 POST /{thread_id}/runs/stream)
  → @require_permission 检查权限
  → start_run() 启动 Agent
  → SSE 流式响应 返回
```

## 4. Agent 与 SubAgent 设计

### 类层次结构

- **AgentState**: messages: list[BaseMessage]
- **ThreadState**(继承AgentState): sandbox, thread_data, title, artifacts, todos, uploaded_files, viewed_images
- **AgentMiddleware**: before_agent(), before_model(), after_model(), wrap_tool_call(), after_agent()
  - 子类: ThreadDataMiddleware, SandboxMiddleware, MemoryMiddleware, SubagentLimitMiddleware, ClarificationMiddleware
- **SubagentConfig**: name, description, system_prompt, tools, skills, model, max_turns, timeout_seconds
- **SubagentResult**: task_id, trace_id, status, result, error, cancel_event
- **SubagentExecutor**: execute(task), execute_async(task), cancel()

### 中间件链执行顺序（20层）

```
[0]  ThreadDataMiddleware       — 创建线程目录
[1]  UploadsMiddleware          — 注入上传文件列表
[2]  SandboxMiddleware          — 获取/创建沙箱
[3]  DanglingToolCallMiddleware — 修补中断导致的悬空 tool_call
[4]  LLMErrorHandlingMiddleware — LLM 调用异常→可恢复错误
[5]  GuardrailMiddleware        — (可选) 工具调用授权
[6]  SandboxAuditMiddleware     — 沙箱操作审计
[7]  ToolErrorHandlingMiddleware— 工具异常→错误 ToolMessage
[8]  DynamicContextMiddleware   — 注入日期+memory 到首条 HumanMessage
[9]  SummarizationMiddleware    — (可选) 上下文压缩
[10] TodoMiddleware             — (可选) plan_mode 任务跟踪
[11] TokenUsageMiddleware       — (可选) token 用量记录
[12] TitleMiddleware            — 自动生成会话标题
[13] MemoryMiddleware           — 会话→记忆更新队列
[14] ViewImageMiddleware        — (可选) 图片 base64 注入
[15] DeferredToolFilterMiddleware — (可选) 延迟工具 schema 隐藏
[16] SubagentLimitMiddleware    — (可选) 并行子 agent 限制
[17] LoopDetectionMiddleware    — 重复调用检测
[18] SafetyFinishReasonMiddleware — (可选) 安全终止处理
[19] ClarificationMiddleware    — 始终最后，拦截 ask_clarification
```

### SubAgent 生命周期

```
[*] → PENDING(创建) → RUNNING(提交到线程池) → COMPLETED/FAILED/CANCELLED/TIMED_OUT(15min) → [*]
```

### SubAgent 并发执行模型

用户请求 → Lead Agent LLM 分析任务并拆分 → 并行提交多个 SubAgent → 各自独立执行 → 汇总结果返回用户。

## 5. Middleware 机制详解

### 什么是 Middleware？

**Middleware 是包裹在 Agent 循环外部的拦截层。** DeerFlow 的 Agent 本质是一个单节点 LangGraph 图，运行着 `model call → tool execution → model call → ...` 的循环。Middleware 不参与业务决策，而是在这个循环的每个阶段注入**横切关注点**——错误处理、沙箱管理、记忆注入、安全审计等。

可以把 Agent 循环想象成一条流水线，Middleware 就是流水线两侧的质检工位：产品（消息）在流水线上流动，每个工位检查、修改或记录产品状态，但工位本身不决定产品是什么。

### Middleware 挂钩点

```
before_agent() → before_model() → LLM调用 → after_model() → wrap_tool_call() → 工具执行 → after_model() → after_agent()
```

| 钩子 | 触发时机 | 典型用途 |
|------|---------|---------|
| `before_agent()` | Agent 循环启动前 | 创建线程目录、获取沙箱 |
| `before_model()` | 每次 LLM 调用前 | 注入记忆上下文、注入图片 base64、上下文压缩 |
| `after_model()` | 每次 LLM 返回后 | 记录 token 用量、生成标题、检测循环 |
| `wrap_tool_call()` | 工具执行时（包裹调用） | 错误处理、安全审计、权限守卫 |
| `after_agent()` | Agent 循环结束后 | 记忆持久化、资源清理 |

### 20 层 Middleware 按职责分类

**基础设施层**: ThreadDataMiddleware, UploadsMiddleware, SandboxMiddleware

**安全与错误处理层**: DanglingToolCallMiddleware, LLMErrorHandlingMiddleware, ToolErrorHandlingMiddleware, GuardrailMiddleware, SandboxAuditMiddleware, SafetyFinishReasonMiddleware

**上下文工程层**: DynamicContextMiddleware, SummarizationMiddleware, ViewImageMiddleware, DeferredToolFilterMiddleware

**观测与记录层**: TokenUsageMiddleware, TitleMiddleware, MemoryMiddleware, TodoMiddleware

**流程控制层**: SubagentLimitMiddleware, LoopDetectionMiddleware, ClarificationMiddleware

### Lead Agent 记忆机制：读写分离的长期记忆

**默认只有 Lead Agent 挂载 DeerFlow 的长期记忆链路。** 主应用通过 `DynamicContextMiddleware` 读取并注入记忆，通过 `MemoryMiddleware` 在一轮对话结束后排队更新记忆。SubAgent 默认拥有独立 state 和消息列表，不会自动继承这套长期记忆。

**读记忆（进入 Agent 前）**: 读取 memory.json → format_memory_for_injection → 隐藏 system-reminder HumanMessage → Lead Agent LLM

**写记忆（Agent 结束后）**: 过滤用户输入+最终AI回复 → MemoryUpdateQueue → 30s防抖/摘要前立即flush → MemoryUpdater调用LLM抽取 → 更新summaries+facts → 保存memory.json

**记忆提取什么？** 不是完整聊天记录，而是从可复用上下文中提取出的结构化资料。输入会先过滤掉 tool call 中间消息、纯上传文件消息和临时上传路径。

**摘要型记忆**: workContext(工作背景), personalContext(偏好), topOfMind(近期关注), recentMonths(近期活动), earlierContext(历史模式), longTermBackground(长期背景)

**事实型记忆**: preference(偏好工具/风格), knowledge(技术和领域知识), context(项目/团队/角色), behavior(工作习惯), goal(目标/方向), correction(纠正过的误解)

**记忆为什么放在 HumanMessage，而不是 system prompt？** 当前实现把记忆放进隐藏的 `HumanMessage`，是为了保持静态 system prompt 不变，提升 provider prefix cache 的命中率。如果把用户记忆直接拼进 system prompt，每个用户、每个 Agent、每次记忆变化都会改变 prompt 前缀，缓存复用会明显变差。

注入形态示例:
```xml
<system-reminder>
  <memory>
    User Context:
    - Work: ...
    - Current Focus: ...
    History:
    - Recent: ...
    Facts:
    - [preference | 0.95] User prefers concise technical explanations
  </memory>
  <current_date>2026-05-25, Monday</current_date>
</system-reminder>
```

`<system-reminder>` 不是模型 API 的正式角色，而是一种提示标签约定，用来告诉模型"这段是运行时提醒，不是用户请求本身"。

### Middleware 与 MetaGPT Action SOP 的对比

两者都是**预定义、可重复执行的线性管道**，但解决的问题层级不同。

| 维度 | DeerFlow Middleware 链 | MetaGPT Action SOP |
|------|----------------------|-------------------|
| 组成单元 | Middleware（基础设施关注点） | Action（业务领域步骤） |
| 典型节点 | ErrorHandling, Memory, Guardrail, Sandbox | WritePRD, Design, WriteCode, SummarizeCode |
| 编排方式 | 线性链，append 顺序执行 | 线性链（BY_ORDER），顺序执行 |
| 关注层级 | **横切关注点** 基础设施：怎么跑 | **纵向业务流** 领域流程：做什么 |
| 产出物 | 无独立产出，修饰 Agent 行为 | 每步产出 Message / Artifact |
| 与 LLM 的关系 | Middleware 本身不调用 LLM，只拦截输入/输出 | Action 内部调用 LLM 完成具体业务 |
| 可复用性 | 跨场景通用，可插拔组合 | 按角色预定义，绑定特定 SOP |
| 类比 | 流水线两侧的质检工位 | 流水线上的加工工位 |

**核心区别**: MetaGPT 的 Action SOP 回答的是 **"先做什么、再做什么"**——写 PRD、做设计、写代码，每一步都产出业务制品。DeerFlow 的 Middleware 链回答的是 **"在做任何事之前/之后，环境需要准备什么、检查什么、记录什么"**——沙箱就绪了吗？记忆注入了吗？异常兜住了吗？

两者可以叠加：你可以在 MetaGPT 的某个 Action 内部跑一个 DeerFlow 风格的 Middleware 链，也可以在 DeerFlow 的 Agent 循环里调用一个 MetaGPT 风格的 Action 序列。

## 6. 完整链路与数据生命周期

**场景设定：** 用户在 Web 界面输入"帮我开发一个用户登录功能，包含前端页面和后端 API"，DeerFlow 需要拆分为前端 SubAgent 和后端 SubAgent 并行执行。

### 完整请求链路（12 步）

**Step 1-2：用户请求 → 前端 → Nginx**
用户在 Next.js 界面输入任务。前端将消息序列化为 `RunCreateRequest`，发送 `POST /api/threads/{thread_id}/runs/stream`。Nginx 匹配 `location /api/`，将请求转发到 Gateway :8001。

**Step 3：Gateway 认证层**
AuthMiddleware 检查 `access_token` cookie → 验证 JWT → 解析出 `user_id`，挂到 `request.state.user`。CSRFMiddleware 验证 Double Submit Cookie。CORSMiddleware 处理跨域。

**Step 4：Router → start_run()**
`thread_runs.py::stream_run()` 接收请求，调用 `start_run()`：
1. `run_mgr.create_or_reject()` → 创建 RunRecord（run_id, thread_id, status=pending）
2. `normalize_input()` → 将 dict 消息转为 LangChain Message 对象
3. `build_run_config()` → 注入 thread_id、recursion_limit=100
4. `merge_run_context_overrides()` → 注入 model_name、subagent_enabled=true 等
5. `asyncio.create_task(run_agent(...))` → 后台启动 Agent
6. 返回 StreamingResponse，绑定 SSE consumer

**Step 5-6：run_agent() → make_lead_agent()**
run_agent() 初始化 RunJournal、标记 status=running、快照 checkpoint（用于回滚）、构建 Runtime context、注入 LangChain 回调。然后调用 make_lead_agent(config)：解析模型名 → 组装 Middleware 链 → 获取 Tools → 调用 create_agent() 编译为 LangGraph StateGraph。

**Step 7：Middleware 链执行（before_agent 阶段）**
Agent 循环启动前，before_agent 挂钩按顺序执行：
1. ThreadDataMiddleware → 创建工作目录
2. UploadsMiddleware → 扫描上传文件列表注入 state
3. SandboxMiddleware → 获取沙箱实例，写入 sandbox_id
4. DynamicContextMiddleware → 从记忆系统读取用户偏好，注入 `<memory>` 标签 + 当前日期到首条 HumanMessage 前

**Step 8：Lead Agent LLM 决策**
LLM 收到系统提示 + 注入的记忆上下文 + 用户消息，分析后决定：
→ 调用 `task("实现后端登录API...", subagent_type="general-purpose")`
→ 调用 `task("实现前端登录页面...", subagent_type="general-purpose")`
两个 tool_call 在同一轮 AIMessage 中发出。

**Step 9：Middleware 链执行（wrap_tool_call 阶段）**
每个 tool_call 经过 wrap_tool_call 挂钩：
1. SubagentLimitMiddleware → 检查并行数（默认上限 3），截断超额调用
2. ToolErrorHandlingMiddleware → try/except 包裹工具执行，异常转为错误 ToolMessage
3. SandboxAuditMiddleware → 记录沙箱操作审计日志
4. GuardrailMiddleware → 可选的工具调用授权检查

**Step 10：task_tool() → SubAgent 执行**
task_tool() 为每个子任务：
1. 验证 subagent_type，提取父级上下文（sandbox_state, thread_data, trace_id）
2. 创建 SubagentExecutor，提交到线程池（3 workers）
3. execute_async() → 在独立 asyncio 事件循环中运行 _aexecute()
4. SubAgent 内部也有自己的 Middleware 链（ThreadData + Sandbox + ErrorHandling 等基础设施层）
5. Lead Agent 的 task_tool 轮询每 5 秒检查一次，通过 get_stream_writer() 将 SubAgent 进度推送给前端 SSE
6. 两个 SubAgent 并行执行，各自独立的沙箱和工作目录

**Step 11：结果汇总 → 最终响应**
两个 SubAgent 完成 → task_tool 返回 "Task Succeeded. Result: ..." 作为 ToolMessage。Lead Agent LLM 收到两个 ToolMessage，生成汇总响应。

**Step 12：收尾 → SSE 关闭**
after_agent 挂钩执行：MemoryMiddleware 入队记忆更新（30s 去抖后异步写入）、TitleMiddleware 自动生成会话标题。run_agent() flush journal、持久化 token 用量、同步标题到 thread_meta、发布 end 事件。sse_consumer() 流结束，HTTP 连接关闭。

### 关键数据的生命周期

#### RunRecord 状态流转

| 阶段 | 状态 | 关键字段变化 |
|------|------|------------|
| 创建 | pending | run_id 生成, thread_id 绑定, task=None |
| Agent 启动 | running | task = asyncio.Task 句柄, 开始统计 token |
| 执行中 | running | token 用量持续累加, abort_event 可被设置 |
| 正常完成 | success | token 用量最终快照, journal flush |
| 异常/超时/取消 | error/timeout/interrupted | checkpoint 用于回滚, error 信息记录 |

#### ThreadState 演变

```
初始状态: messages=[HumanMessage], sandbox=null, thread_data=null, artifacts=[], todos=null
    ↓
before_agent 阶段: ThreadDataMiddleware→设置工作目录, SandboxMiddleware→获取沙箱, DynamicContextMiddleware→注入记忆+日期
    ↓
第 1 轮 LLM: AIMessage with tool_calls=[task('后端'), task('前端')]
    ↓
工具执行: task_tool → SubAgent 并行 → 两个 ToolMessage
    ↓
第 2 轮 LLM: AIMessage 汇总
    ↓
after_agent 阶段: TitleMiddleware→生成标题, MemoryMiddleware→入队记忆更新, 写入 checkpoint
```

#### messages 列表示例

| # | 类型 | 来源 | 内容 |
|---|------|------|------|
| 1 | HumanMessage | DynamicContextMiddleware | `<memory>用户偏好...</memory> 当前日期: 2026-05-25` |
| 2 | HumanMessage | 用户输入 | "帮我开发一个用户登录功能，包含前端页面和后端 API" |
| 3 | AIMessage | Lead Agent LLM | tool_calls: [task("后端登录API"), task("前端登录页面")] |
| 4 | ToolMessage | 后端 SubAgent | "Task Succeeded. Result: 后端API包含登录/注册/JWT..." |
| 5 | ToolMessage | 前端 SubAgent | "Task Succeeded. Result: 前端页面包含表单/验证..." |
| 6 | AIMessage | Lead Agent LLM | "登录功能开发完成，后端包含...前端包含..." |

#### SubAgent 内部消息流（以后端 SubAgent 为例）

SubAgent 有自己独立的 state 和消息列表，与 Lead Agent 完全隔离：

| # | 类型 | 来源 | 内容 |
|---|------|------|------|
| 1 | SystemMessage | SubAgent 初始化 | 系统提示 + Skills 内容 |
| 2 | HumanMessage | task_tool 传入 | "实现后端登录API，包括JWT认证、用户表、登录注册接口" |
| 3 | AIMessage | SubAgent LLM | tool_calls: [write_file("auth.py", ...), write_file("models.py", ...)] |
| 4 | ToolMessage | write_file 工具 | "File written successfully" |
| 5 | AIMessage | SubAgent LLM | "后端登录 API 已完成"（返回给 Lead Agent） |

#### SSE 事件流

```
metadata → messages(chunk 1, AIMessage with tool_calls) → custom:task_started(×2) → custom:task_running(×2) → custom:task_completed(×2) → messages(chunk 2, ToolMessage×2) → messages(chunk 3, AIMessage 汇总) → end
```

#### Checkpoint 机制

LangGraph 的 Checkpointer 在**每一步**（每次 LLM 调用、每次工具执行）后自动保存 ThreadState 快照到数据库。
- 崩溃恢复：run_agent 崩溃后从最近 checkpoint 恢复
- Human-in-the-loop：用户暂停后可以从断点继续
- 回滚：run_agent 启动时快照 pre-run checkpoint，失败可回滚

### Middleware 在链路中的精确位置

```
HTTP 请求阶段（无Middleware）: Nginx → Gateway Auth/CSRF → start_run() → run_agent()
    ↓
before_agent 挂钩: ThreadData → Uploads → Sandbox → DynamicContext(注入记忆+日期)
    ↓
before_model 挂钩: Summarization(可选) → ViewImage(可选)
    ↓
LLM 调用
    ↓
after_model 挂钩: TokenUsage → LoopDetection → SubagentLimit
    ↓
wrap_tool_call 挂钩: ToolErrorHandling → SandboxAudit → Clarification(终止)
    ↓
SubAgent 执行: task_tool() → SubagentExecutor → SubAgent独立Middleware链 → SubAgent LLM+工具 → 结果返回
    ↓
LLM 调用(汇总)
    ↓
after_agent 挂钩: TitleMiddleware → MemoryMiddleware
    ↓
收尾: flush journal + 持久化token → 发布end SSE事件
```

### 数据流向全景

```
用户请求 → Nginx → Gateway → AuthMiddleware(→user_id)
    → start_run()(→RunRecord) → asyncio.create_task(run_agent)
    → make_lead_agent() → Middleware链×20
    → Lead Agent LLM ←读写→ ThreadState → 每步快照→Checkpoint DB
    → task_tool() → SubagentExecutor → 后端SubAgent/前端SubAgent(并行)
    → 结果→ToolMessage→Lead Agent→最终AIMessage
    → StreamBridge.publish → SSE事件→用户
    → after_agent → MemoryQueue → 30s去抖→memory.json
```

## 7. LangGraph 在 DeerFlow 中的真正角色

**核心结论：DeerFlow 用的是 LangGraph 的运行时基础设施，不是它的图编排能力。** Lead Agent 在 LangGraph 层面只有**一个节点**，SubAgent 不是图节点，是工具函数内部启动的独立线程。

### 为什么单节点还要用 LangGraph？

| LangGraph 提供的能力 | 不用 LangGraph 要自己写 |
|---------------------|----------------------|
| Checkpoint 自动持久化 | 状态快照+存储+恢复逻辑 |
| Interrupt/Resume (Human-in-the-loop) | 中断点管理+恢复上下文重建 |
| `add_messages` 状态合并器 | 消息去重、追加、替换的手动处理 |
| SSE 流式输出（3种模式） | 生产者-消费者+序列化+断线重连 |
| `create_agent()` 标准 ReAct 循环 | while 循环+tool_call 解析+错误重试 |
| Middleware 钩子系统 | before/after 拦截器链 |
| Checkpointer 插件化（SQLite/Postgres） | 适配不同存储后端 |

**LangGraph 在这里不是"图编排引擎"，而是"带状态持久化的 Agent 运行时"。**

### 真实的 LangGraph 图结构

```
编译后的图（CompiledStateGraph，单节点）:
START → agent_node → (有tool_call → agent_node) / (无tool_call → END)

agent_node 内部（ReAct 循环）:
LLM调用 → 有tool_calls? → 是 → 执行工具 → ToolMessage加入state → LLM调用
                        → 否 → 返回 AIMessage
```

### SubAgent 不是节点，是工具的副作用

SubAgent 的启动发生在 `task` 工具的 Python 函数内部，对 LangGraph 来说跟调用 `write_file` 或 `bash` 没有区别：

```
LangGraph引擎 → agent_node → LLM → tool_calls: [task("后端API")]
    → task_tool() → SubagentExecutor → 新线程 create_agent()
    → SubAgent实例（独立的LangGraph图、独立的state、独立的Middleware链）
    → 结果 → ToolMessage → checkpoint保存 → 下一轮
```

### Checkpoint 什么时候保存？

**每个节点每次执行完毕后保存一次。** 一次包含 2 次 LLM 调用的 run，产生 3 个 checkpoint：
- 第1轮: LLM → tool_calls → checkpoint①
- 第2轮: 工具执行 → ToolMessage → checkpoint②
- 第3轮: LLM → 最终AIMessage → checkpoint③

**Checkpoint 存了什么？** ThreadState 全量快照（messages、sandbox、artifacts、todos、title）+ 元数据（thread_id、step序号、时间戳）

### 与 MetaGPT 的图结构对比

| 维度 | MetaGPT | DeerFlow |
|------|---------|----------|
| 图的结构 | 多节点图（每个Role是一个节点） | 单节点图（ReAct循环） |
| 编排方式 | 显式：Environment广播→Role watch过滤 | 隐式：LLM通过tool_call决定 |
| 子任务执行 | Role是图节点，消息在节点间流动 | SubAgent是工具内部的线程，对图不可见 |
| 状态持久化 | 无内置checkpoint | LangGraph自动checkpoint |
| LangGraph的价值 | 不使用LangGraph | 用的是运行时，不是图编排 |

## 8. 消息机制

### MessageBus 架构

```
外部IM平台(飞书/Slack/Telegram/钉钉/企业微信)
    → publish_inbound() → Inbound Queue(asyncio.Queue)
    → get_inbound() → ChannelManager
    → Gateway API
    → publish_outbound() → Outbound Listeners(list of callbacks)
    → send() → 外部IM平台
```

### 消息数据结构

**InboundMessage**: channel_name, chat_id, user_id, text, msg_type(CHAT/COMMAND), thread_ts, topic_id, files, metadata, created_at

**OutboundMessage**: channel_name, chat_id, thread_id, text, artifacts(文件路径列表), attachments(list[ResolvedAttachment]), is_final(bool), thread_ts, metadata

**ResolvedAttachment**: virtual_path, actual_path, filename, mime_type, size, is_image(bool)

### 消息生命周期

```
外部平台 Webhook/WS → Channel.start → 构造 InboundMessage
    → MessageBus.inbound_queue → ChannelManager._dispatch_loop
    → 路由: COMMAND→_handle_command / CHAT→_handle_chat
    → 查询thread是否存在(否→创建新thread) → 获取thread_id
    → client.runs.stream/wait → Agent执行 → Gateway API
    → OutboundMessage → MessageBus.outbound_listeners
    → Channel._on_outbound → send → 外部平台
```

## 9. 数据模型

### ORM 模型关系

```
USERS: id, email, password_hash, system_role, created_at, oauth_provider, oauth_id
THREADS_META: thread_id, assistant_id, user_id(FK), display_name, status, metadata_json, created_at, updated_at
RUNS: run_id, thread_id(FK), assistant_id, user_id(FK), status, model_name, total_tokens, llm_call_count, created_at
RUN_EVENTS: id, thread_id(FK), run_id(FK), user_id(FK), event_type, category, content, seq, created_at
FEEDBACK: feedback_id, run_id(FK), thread_id(FK), user_id(FK), message_id, rating, comment, created_at

USERS 1→N THREADS_META / RUNS / RUN_EVENTS / FEEDBACK
THREADS_META 1→N RUNS / RUN_EVENTS
RUNS 1→N RUN_EVENTS / FEEDBACK
```

### 运行时内存模型

**RunRecord**: run_id, thread_id, status(RunStatus枚举), task(asyncio.Task句柄), abort_event(取消信号), Token用量统计字段

**ThreadState**: messages(对话消息列表), sandbox(SandboxState), thread_data(工作目录路径), artifacts(产出文件列表), todos(任务跟踪), uploaded_files(上传文件)

## 10. Runtime 运行时

### 核心组件

| 组件 | 职责 |
|------|------|
| RunManager | 运行记录的内存注册表 + 可选持久化 RunStore |
| RunRecord | 单次运行的可变记录（status, token用量, task引用等） |
| RunContext | 基础设施依赖打包（checkpointer, store, event_store） |
| run_agent() | 后台 agent 执行引擎 |
| RunJournal | LangChain 回调处理器，捕获事件写入 RunEventStore |
| StreamBridge | 生产者-消费者解耦（agent worker → SSE endpoint） |

### Run 状态机

```
[*] → pending → running → success/error/timeout/interrupted → [*]
```

### StreamBridge 数据流

```
Agent Worker(生产者): agent.astream → publish() → StreamBridge
    → 事件类型: metadata / values(完整状态快照) / messages(消息增量) / updates(节点写入) / custom(StreamWriter转发) / error(异常信息)
    → subscribe() → AsyncIterator → 客户端(消费者)
```

## 11. 关键设计模式

1. **Harness/App 分层**: persistence属于harness层，app/gateway属于应用层。依赖单向：app导入deerflow，反之禁止。
2. **双轨持久化**: LangGraph Checkpointer管图执行状态，应用ORM管业务元数据。共享物理数据库但代码完全独立。
3. **Repository模式+用户隔离**: 所有数据访问通过Repository抽象，user_id通过ContextVar自动传播，实现行级数据隔离。
4. **内存优先+Store兜底**: RunManager在内存维护活跃运行状态，同步持久化到Store，支持进程重启恢复。
5. **事件溯源**: RunEventStore以append-only方式记录，按seq全局递增，支持分页查询和审计。
6. **消息总线解耦**: MessageBus完全解耦Channel和Agent——Channel不知道哪个Agent处理消息，Agent不知道消息来自哪个平台。
