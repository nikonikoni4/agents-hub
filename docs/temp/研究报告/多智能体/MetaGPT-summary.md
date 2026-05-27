# MetaGPT 深度分析汇总

> 基于源码验证 · Agent 编排机制 · 类关系 · 记忆系统 · 三合一

---

## 目录

- [1. 概述与架构](#1-概述与架构)
- [2. 核心数据结构](#2-核心数据结构)
- [3. Action 与工具调用机制](#3-action-与工具调用机制)
- [4. 消息过滤机制](#4-消息过滤机制)
- [5. Agent 角色列表](#5-agent-角色列表)
- [6. 三种反应模式](#6-三种反应模式)
- [7. 消息处理机制](#7-消息处理机制)
- [8. 记忆机制全景](#8-记忆机制全景)
- [9. TeamLeader 调度机制](#9-teamleader-调度机制)
- [10. 与其他框架的对比](#10-与其他框架的对比)

---

## 1. 概述与架构

MetaGPT 是一个基于 LLM 的多 Agent 协作框架，将软件开发过程中的不同角色（产品经理、架构师、工程师等）抽象为独立 Agent，通过消息传递和 SOP 任务流程实现自动化开发。

> **核心设计理念：** 采用"公司化"组织结构，Agent 视为公司中的不同角色。TeamLeader 作为项目经理负责整体协调，各专业角色专注于自己的领域。通过标准化消息协议和 SOP 流程实现高效协作。

**关键指标：**
- 6+ 核心 Agent 角色
- 3 种反应模式
- 8 个核心数据结构
- Pub-Sub 消息架构

### 四层架构

| 层级 | 说明 |
|------|------|
| **Team（团队层）** | 最高层容器，管理所有角色和环境。负责 hire（雇佣）角色、投资预算管理（investment）、项目启动和运行控制、use_mgx 控制是否使用 MGX 模式 |
| **Environment（环境层）** | 消息传递和角色协调的中枢。发布-订阅消息系统、消息路由和分发（is_send_to）、角色状态管理、并行调度（asyncio.gather） |
| **Role（角色层）** | 各种 Agent 的基类，定义行为模式。观察-思考-行动循环（_observe → _think → _act）、记忆管理（Memory）、动作执行（Action）、支持三种反应模式 |
| **Action（动作层）** | 角色执行的具体任务单元。原子化任务执行、LLM 调用封装（_aask）、ActionNode 支持结构化输出、结果输出为 Message |

---

## 2. 核心数据结构（最小知识集）

理解 MetaGPT 的编排机制，只需理解以下 8 个核心类。

> **类关系总览：** Team 持有 Environment → Environment 持有多个 Role → 每个 Role 持有多个 Action → Action 执行后产生 Message → Message 通过 Environment 路由到其他 Role 的 MessageQueue → Role 的 _observe 过滤后存入 Memory

```
Team
 └─ Environment
     ├─ history: Memory
     ├─ roles: dict[str, Role]
     └─ Role
         ├─ actions: list[Action]
         │   └─ Action
         │       ├─ llm: BaseLLM
         │       └─ run() → Message
         └─ rc: RoleContext
             ├─ msg_buffer: MessageQueue  ← 私有收件箱
             ├─ memory: Memory            ← 已处理的消息
             ├─ watch: set[str]           ← 订阅的 Action 类名
             ├─ todo: Action | None       ← 当前要执行的 Action
             ├─ state: int                ← 当前 action 索引
             └─ env: Environment          ← 反向引用
```

### Team

**字段：**
- `env`: Optional[Environment] = None
- `investment`: float = 10.0
- `idea`: str = ""
- `use_mgx`: bool = True ← 控制 MGX 模式

**方法：**
- `hire(roles: list[Role])`
- `run_project(idea, send_to="")`
- `run(n_round=3, idea="", send_to="", auto_archive=True)`
- `invest(investment: float)`

### Environment

**字段：**
- `roles`: dict[str, Role] ← 不是 list，是 dict
- `member_addrs`: Dict[Role, Set]
- `history`: Memory

**方法：**
- `publish_message(msg)` → 遍历 member_addrs 做路由匹配
- `run(k=1)` → asyncio.gather 并行执行所有非 idle Role
- `is_idle` → 所有 Role 都空闲时返回 True
- `add_role(role)` / `add_roles(roles)`

### Role

**字段：**
- `name`: str = ""
- `profile`: str = ""
- `goal`: str = ""
- `constraints`: str = ""
- `actions`: list[Action] = []
- `rc`: RoleContext
- `addresses`: set[str]
- `planner`: Planner ← PLAN_AND_ACT 模式使用

**核心方法：**
- `run(with_message=None)` → Message
- `react()` → 路由到 _react() 或 _plan_and_act()
- `_observe()` → int（从 msg_buffer 取消息并过滤）
- `_think()` → bool（选择下一个 Action）
- `_act()` → Message（执行 Action）
- `_react()` → Message（REACT/BY_ORDER 共用循环）
- `_plan_and_act()` → Message（PLAN_AND_ACT 独立循环）
- `_watch(actions)` ← 订阅 Action 类型

### RoleContext (rc)

**字段（定义在 roles/role.py 中）：**
- `env`: BaseEnvironment
- `msg_buffer`: MessageQueue
- `memory`: Memory
- `working_memory`: Memory ← HTML 未提及
- `watch`: set[str] // 存的是字符串，不是类对象
- `todo`: Action | None
- `state`: int = -1 // -1 = 初始/终止态
- `react_mode`: RoleReactMode = REACT
- `max_react_loop`: int = 1
- `news`: list[Message]

**属性：**
- `history` → memory.get()（返回全部消息）

### Action

**字段：**
- `name`: str
- `i_context`: Any // 输入上下文
- `prefix`: str // system prompt
- `node`: ActionNode = None
- `desc`: str = ""

**方法：**
- `run(*args)` → Message | str
- `_aask(prompt, system_msgs=None)` → str
- `_run_action_node(*args)` // node 存在时委托给它

**子类示例：** WritePRD · WriteDesign · WriteCode · WriteTest · WriteTasks · SummarizeCode · ...

### Message

**字段（定义在 schema.py）：**
- `id`: str // 自动生成 uuid
- `content`: str // 消息正文
- `cause_by`: str // 产生此消息的 Action 类名（全限定名）
- `sent_from`: str // 发送者
- `send_to`: set[str] = {"<all>"} // 接收者集合
- `instruct_content`: BaseModel | None
- `role`: str = "user"
- `metadata`: Dict[str, Any] = {}

**子类：** AIMessage · UserMessage · SystemMessage

### MessageQueue

**定义在 schema.py 中：**

**字段：**
- `_queue`: asyncio.Queue（私有）

**方法：**
- `push(msg)`
- `pop()` → Message | None
- `pop_all()` → list[Message]
- `empty()` → bool

### Memory

**字段：**
- `storage`: list[Message]
- `index`: DefaultDict[str, list[Message]] // 按 cause_by 倒排索引

**核心方法：**
- `add(msg)` / `add_batch(msgs)`
- `get(k=0)` → list[Message] // k=0 返回全部
- `get_by_actions(actions)` → list[Message]
- `try_remember(keyword)` → list[Message]
- `find_news(observed, k=0)`
- `delete(msg)` / `clear()` / `count()`

### 消息传递流程（PM → Architect 为例）

```
1. env.publish_message — Team.run_project() 发布用户需求
   Message(content="需求", cause_by=UserRequirement, send_to=ALL)
   ↓
2. 路由匹配 — 遍历 member_addrs，is_send_to() 检查地址
   for role, addrs in member_addrs: if is_send_to(msg, addrs): role.put_message(msg)
   ↓
3. msg_buffer.push — 消息进入各角色私有队列
   ↓
4. role._observe() — 取出 + 兴趣过滤
   news = msg_buffer.pop_all() → 过滤: (cause_by in watch OR name in send_to) AND not in old_messages
   ↓
5. role._think() — 选择要执行的 Action
   BY_ORDER: state += 1 | REACT: LLM 选 state | PLAN_AND_ACT: 走 _plan_and_act()
   ↓
6. role._act() — 执行 Action，产出 Message
   response = await todo.run(history) → msg = AIMessage(cause_by=todo, sent_from=self)
   ↓
7. publish_message — 结果发回环境，触发下游 → 回到步骤 2
```

---

## 3. Action 与工具调用机制

Action 是 MetaGPT 中"做事情"的基本单元。普通 Role 和 Leader 使用 Action 的方式完全不同。

### 普通 Role 的 Action — 预定义工作流

```python
# 普通 Role 的 Action 是预定义的具体类
class WritePRD(Action):
    async def run(self, context):
        result = await self._aask(prompt)
        return result

# ProductManager 的 actions 列表
self.set_actions([PrepareDocuments, WritePRD])
# _think 时按 BY_ORDER 顺序选择：先 PrepareDocuments，再 WritePRD
```

### Leader 的 Action — tool_execution_map（工具调用）

> **关键区别：** Leader 的 self.actions 只有一个空壳 RunCommand。它的真正动作空间是 tool_execution_map — 一个命令名→函数的映射表。LLM 在 _think 阶段输出 JSON 命令数组，_act 阶段解析 JSON 并调用对应函数。

```python
# Leader 的 _act 不调用 action.run()，而是直接解析 LLM 输出的 JSON 命令
commands = json.loads(self.command_rsp)  # LLM 输出的命令数组
for cmd in commands:
    if cmd["command_name"] in self.tool_execution_map:
        result = await self.tool_execution_map[cmd["command_name"]](**cmd["args"])
```

### TeamLeader 的完整工具集

**Plan 管理：**
- `Plan.append_task`
- `Plan.reset_task`
- `Plan.replace_task`
- `Plan.finish_current_task`（特殊命令）

**团队调度：**
- `TeamLeader.publish_team_message`
- `TeamLeader.publish_message`（别名）
- `RoleZero.ask_human`
- `RoleZero.reply_to_human`
- `end`（终止，特殊命令）

**浏览器工具（10 个）：**
- `Browser.goto` / `click` / `type`
- `Browser.scroll` / `go_back` / `close_tab`
- `Browser.select` / `scroll_to_text`
- `Browser.get_page_html` / `get_all_text`

**编辑器工具（16 个）：**
- `Editor.create_file` / `write` / `read`
- `Editor.open_file` / `edit_file_by_replace`
- `Editor.search_file` / `search_dir`
- `Editor.write` / `open` / `create` ...

### 本质对比

| 维度 | 普通 Role 的 Action | Leader 的 tool_execution_map |
|------|---------------------|------------------------------|
| **选择范围** | self.actions 列表（2-3 个） | tool_execution_map（20+ 个命令） |
| **选择方式** | _think 中 LLM 返回数字编号 | _think 中 LLM 输出 JSON 命令数组 |
| **执行方式** | action.run(history) | tool_execution_map[name](**args) |
| **本质** | Action 可能包含复杂逻辑（内嵌 LLM 调用） | 更接近标准 tool calling（直接函数调用） |
| **共同点** | 都是"从有限工具集中选择并执行"，Agent 不能调用未注册的工具 |

---

## 4. 消息过滤机制（cause_by + watch + _observe）

MetaGPT 的消息过滤是一个事件驱动的发布-订阅系统。cause_by 记录"刚才发生了什么动作"，watch 是每个角色的"触发列表"。

> **核心概念纠偏：** cause_by 不是"下一步该执行的 Action"，而是"上一步刚完成的 Action"。比如 PM 执行完 WritePRD 后，消息的 cause_by=WritePRD。Architect 的 watch={WritePRD} 表示"当 WritePRD 发生时，触发我开始工作"。这是事件触发机制，不是指令传递机制。

### 一、cause_by 与 watch 的本质

**cause_by — "刚才发生了什么"**

每条消息都有 cause_by 字段，记录产生这条消息的 Action **全限定类名**。

```python
# role.py — _act() 中自动设置
msg = AIMessage(
    content=response.content,
    cause_by=self.rc.todo,  # 自动转为类名字符串
    sent_from=self,
)
# 例: cause_by = "metagpt.actions.write_prd.WritePRD"
```

**关键：** cause_by 记录的是"已经发生的动作"，存储为全限定类名字符串。

**watch — "什么事件触发我"**

每个 Role 声明自己关心哪些 Action 产生的消息：

```python
# _watch() 将 Action 类转为字符串集合
def _watch(self, actions):
    self.rc.watch = {any_to_str(t) for t in actions}

# ProductManager
self._watch([UserRequirement, PrepareDocuments])
# Architect
self._watch({WritePRD})
```

**本质：** watch 是一个事件触发列表——"当 X Action 完成时，触发我开始工作"。

> **类比理解：** 就像基于 topic 的消息队列（如 Kafka）：cause_by = topic（消息标签），watch = subscription（订阅列表），Environment = message broker（消息代理），_observe() = consumer filter（消费者过滤器）。

### 二、两层过滤机制

**第一层：Environment 路由（地址匹配）**

```python
# base_env.py — Environment.publish_message()
def publish_message(self, message):
    for role, addrs in self.member_addrs.items():
        if is_send_to(message, addrs):     # send_to 与角色地址有交集？
            role.put_message(message)       # 是 → 推入该角色的 msg_buffer
    self.history.add(message)

# is_send_to() — utils/common.py
def is_send_to(message, addresses):
    if MESSAGE_ROUTE_TO_ALL in message.send_to:
        return True  # send_to={"<all>"} → 所有人匹配
    for i in addresses:
        if i in message.send_to:
            return True
    return False
```

这一层只做地址匹配，是纯内存操作（微秒级），不涉及 LLM 调用。

**第二层：_observe 兴趣过滤（事件匹配）**

```python
# role.py — Role._observe()
async def _observe(self) -> int:
    news = self.rc.msg_buffer.pop_all()
    old_messages = [] if not self.enable_memory else self.rc.memory.get()

    self.rc.news = [
        n for n in news
        if (n.cause_by in self.rc.watch     # 条件A：事件匹配
            or self.name in n.send_to)       # 条件B：精确匹配
        and n not in old_messages             # 条件C：去重
    ]
    self.rc.memory.add_batch(self.rc.news)
    return len(self.rc.news)
```

- **条件 A：cause_by in watch** — 消息的 cause_by 是否在我的 watch 中。这是发布-订阅的核心：发送者不管谁接收，接收者自己声明关心什么。
- **条件 B：name in send_to** — 消息的 send_to 是否包含我的名字。用于点对点发送场景，如 TeamLeader 的 publish_team_message。

### 三、两种消息路由方式

**广播 + 事件过滤（经典 SOP 模式）：**
- 消息 send_to={"<all>"}，所有人收到
- 各角色通过 cause_by in watch 自行过滤
- 只有匹配的角色被唤醒执行
- 新增角色只需声明 watch，不改现有代码

**精确指定接收者（MGX 模式 TeamLeader）：**
- 消息 send_to={"Bob"}，只有 Bob 收到
- 通过条件 B（name in send_to）匹配
- 不依赖 watch 机制
- TL 的 LLM 动态决定发给谁

### 四、各角色 watch 订阅表（源码验证）

| 事件（cause_by） | 产生者 | 触发谁（watch 匹配） | 含义 |
|------------------|--------|---------------------|------|
| `UserRequirement` | 用户输入 | ProductManager, TeamLeader | 用户发需求 → PM/TL 开始工作 |
| `PrepareDocuments` | ProductManager | ProductManager | 项目初始化 → PM 继续写 PRD（BY_ORDER 链内） |
| `WritePRD` | ProductManager | Architect | PRD 完成 → Architect 开始设计 |
| `WriteDesign` | Architect | ProjectManager | 设计完成 → PM 开始拆任务 |
| `WriteTasks` | ProjectManager | Engineer | 任务列表完成 → Engineer 开始写代码 |
| `WriteCode` | Engineer | Engineer（自己） | 代码写完 → 继续总结 |
| `SummarizeCode` | Engineer | Engineer + QaEngineer | 代码总结完成 → QA 开始测试 |

### 五、本质：事件驱动的 Workflow

**传统 Workflow（显式定义下一步）：**
```
Step1: PM 执行 WritePRD → next = Architect
Step2: Architect 执行 WriteDesign → next = PM
Step3: PM 执行 WriteTasks → next = Engineer
```

**MetaGPT（事件触发）：**
```
PM 执行 WritePRD → 发布事件 cause_by=WritePRD
    → Architect 的 watch 包含 WritePRD → 被触发
Architect 执行 WriteDesign → 发布事件 cause_by=WriteDesign
    → PM 的 watch 包含 WriteDesign → 被触发
```

结果一样，但机制不同。传统 Workflow 是"我告诉你去找谁"，MetaGPT 是"我广播我做了什么，谁关心谁来接"。好处是解耦——新增角色只需声明 watch，不改现有代码。

---

## 5. Agent 角色列表与职责（源码验证）

| 角色名称 | 类名 | 继承 | 职责 | watch | react_mode |
|---------|------|------|------|-------|------------|
| **Mike**（TeamLeader） | `TeamLeader` | RoleZero → Role | 团队协调、任务分发、进度跟踪 | UserRequirement（默认） | react max_loop=3 |
| **Alice**（ProductManager） | `ProductManager` | RoleZero → Role | 需求分析、PRD 编写 | UserRequirement, PrepareDocuments | BY_ORDER（use_fixed_sop=True 时） |
| **Bob**（Architect） | `Architect` | RoleZero → Role | 系统架构设计、技术选型 | WritePRD | react（继承 RoleZero） |
| **Eve**（ProjectManager） | `ProjectManager` | RoleZero → Role | 任务拆解、依赖分析 | WriteDesign | react（继承 RoleZero） |
| **Alex**（Engineer） | `Engineer` | Role（直接继承） | 代码编写、审查、总结 | WriteTasks, SummarizeCode, WriteCode, WriteCodeReview, FixBug, WriteCodePlanAndChange | 自定义 _think/_act |
| **Edward**（QaEngineer） | `QaEngineer` | Role（直接继承） | 测试用例、测试执行、Bug 调试 | SummarizeCode, WriteTest, RunCode, DebugError | 自定义 _think/_act |

> **源码验证发现：** Engineer 和 QaEngineer 直接继承 Role（非 RoleZero），并完全覆盖 _think() 和 _act() 方法，不使用标准的 react 循环。ProductManager 只有在 use_fixed_sop=True 时才设 BY_ORDER，否则继承 RoleZero 的 react 模式。Architect 和 ProjectManager 继承 RoleZero 但未显式设置 react_mode，默认为 react。

### 角色层级关系

```
用户需求
↓
TeamLeader (Mike)
↓ 协调分发
[ProductManager] [Architect] [ProjectManager]
↓ 任务执行
[Engineer] [QaEngineer]
```

---

## 6. 三种反应模式（源码验证）

### 模式概览

**ReAct 模式：**
- 思考-行动交替循环，LLM 动态选择下一步动作
- `_think → _act → _think → _act → ...`（共用 _react() 循环骨架）
- 使用者：RoleZero、TeamLeader、SWEAgent

**BY_ORDER 模式：**
- 按注册顺序依次执行，state += 1 机械递增
- `Action0 → Action1 → Action2 → ...`（共用 _react() 循环骨架）
- 使用者：ProductManager（固定 SOP）、Researcher、TutorialAssistant

**PLAN_AND_ACT 模式：**
- 先用 LLM 生成 Plan，再按 Plan 逐步执行
- `planner.update_plan(goal) → while planner.current_task: _act_on_task(task)`（独立的 _plan_and_act() 循环）
- 使用者：DataInterpreter

### 核心流程：react() 入口路由

```python
# role.py — react() 是入口，根据模式分流
async def react(self) -> Message:
    if self.rc.react_mode == RoleReactMode.REACT \
       or self.rc.react_mode == RoleReactMode.BY_ORDER:
        rsp = await self._react()         # REACT 和 BY_ORDER 共用
    elif self.rc.react_mode == RoleReactMode.PLAN_AND_ACT:
        rsp = await self._plan_and_act()  # PLAN_AND_ACT 完全独立
    self._set_state(state=-1)
    ...
```

### _react() — REACT 和 BY_ORDER 共用的循环

```python
async def _react(self) -> Message:
    actions_taken = 0
    while actions_taken < self.rc.max_react_loop:
        has_todo = await self._think()   # ← 在此分叉
        if not has_todo:
            break
        rsp = await self._act()          # ← 所有模式共用
        actions_taken += 1
    return rsp
```

### _think() — 选择下一个 Action

**BY_ORDER — 机械递增：**
```python
if self.rc.react_mode == BY_ORDER:
    if self.rc.max_react_loop != len(self.actions):
        self.rc.max_react_loop = len(self.actions)
    self._set_state(self.rc.state + 1)
    return self.rc.state >= 0 \
       and self.rc.state < len(self.actions)
```
**本质就是一个 for 循环**，自动同步 max_react_loop = len(actions)。

**REACT — LLM 自主决策：**
```python
prompt += STATE_TEMPLATE.format(
    history=self.rc.history,
    states="0. WritePRD\n1. WriteDesign",
    previous_state=self.rc.state,
)
next_state = await self.llm.aask(prompt)
# LLM 可选任意顺序，可返回 -1 终止
```
**唯一真正的 ReAct 模式**，LLM 自由决策。

### _plan_and_act() — PLAN_AND_ACT 独立循环

```python
async def _plan_and_act(self) -> Message:
    if not self.planner.plan.goal:
        goal = self.rc.memory.get()[-1].content
        await self.planner.update_plan(goal=goal)  # 用 LLM 生成计划

    while self.planner.current_task:               # 按任务列表遍历
        task = self.planner.current_task
        task_result = await self._act_on_task(task)  # 抽象方法，子类实现
        await self.planner.process_task_result(task_result)

    rsp = self.planner.get_useful_memories()[0]
```

> **源码验证发现：** PLAN_AND_ACT 调用的是 _act_on_task()（抽象方法，返回 TaskResult），不是 _act()（返回 Message）。_think() 中没有 PLAN_AND_ACT 分支——它在 react() 入口就分流了，完全绕过 _react() 循环。

### 三种模式本质区别

| 维度 | BY_ORDER | REACT | PLAN_AND_ACT |
|------|----------|-------|--------------|
| **_think 选 action** | state += 1 机械递增 | LLM 看历史回答数字 | LLM 先生成 Plan，按 Plan 执行 |
| **执行顺序** | 固定 0→1→2 | LLM 自由选择 | 按 Plan 的拓扑序 |
| **终止条件** | 遍历完自动终止 | LLM 返回 -1 或 max_loop | Plan 完成后终止 |
| **循环骨架** | 共用 _react() | 共用 _react() | 独立 _plan_and_act() |
| **执行方法** | 共用 _act() → action.run() | 共用 _act() → action.run() | _act_on_task()（抽象方法） |
| **是否用 LLM 决策** | 否（硬编码） | 是（每轮调 LLM） | 是（规划时调一次） |
| **本质** | for 循环的伪装 | 真正的 ReAct | Plan-then-Execute |

---

## 7. 消息处理机制（经典 SOP vs MGX）

### 经典 SOP 模式：广播 + 事件驱动

> **核心特征：** 没有 TeamLeader。消息默认广播给所有人，靠 cause_by in watch 自动触发下一个角色。整个流程是事件驱动的链式触发。

```python
# base_env.py — Environment.publish_message()
def publish_message(self, message):
    for role, addrs in self.member_addrs.items():
        if is_send_to(message, addrs):     # send_to={"<all>"} → 所有人匹配
            role.put_message(message)
    self.history.add(message)
```

### MGX 复杂模式：TeamLeader 中心化路由

> **核心特征：** 有 TeamLeader 作为消息中枢。子 Agent 的消息默认经过 TeamLeader，由 TL 的 LLM 动态决定下一步发给谁。

**MGXEnv 的四条路由路径（源码验证）：**

```python
# mgx_env.py — MGXEnv.publish_message() 的四条路径
def publish_message(self, message, user_defined_recipient="", publicer=""):
    tl = self.get_role(TEAMLEADER_NAME)

    if user_defined_recipient:
        # 路径1：用户直接 @某角色 → 绕过 TL
        self._publish_message(message)

    elif message.sent_from in self.direct_chat_roles:
        # 路径2：直聊回复 → 非公开时完全不发布
        self.direct_chat_roles.remove(message.sent_from)
        if self.is_public_chat:
            self._publish_message(message)

    elif publicer == tl.profile:
        # 路径3：TL 自己发的消息 → 直接发布
        self._publish_message(message)

    else:
        # 路径4（默认）：子 Agent 消息 → 自动加 TL 到 send_to
        message.send_to.add(tl.name)       # ← 关键
        self._publish_message(message)
```

**消息内容改写：**
```python
# mgx_env.py — move_message_info_to_content()
# 在发布前改写 content，让 TL 的 LLM 能看到路由信息
converted_msg.content = f"[Message] from {sent_from} to {send_to}: {content}"
# 例: "[Message] from Bob to Mike: Designing is complete..."
```

### 两种模式核心区别

| 维度 | 经典 SOP 模式 | MGX 复杂模式 |
|------|--------------|--------------|
| **消息路由** | 广播 + cause_by in watch 事件过滤 | TL 中心化路由 + send_to 精确指定 |
| **子 Agent 结果去哪** | 广播给所有人，下一个角色 watch 自动匹配 | 自动回到 TeamLeader（send_to.add(tl.name)） |
| **谁决定下一个执行者** | watch 声明（静态，编译时确定） | TL 的 LLM（动态，运行时决策） |
| **是否需要 TeamLeader** | 不需要 | 必须，所有消息经过 TL |
| **消息内容是否改写** | 不改写 | 改写为 [Message] from X to Y: ... 格式 |
| **新增角色代价** | 只需声明 watch | 需注册到 TL 团队信息 |
| **本质** | 事件驱动 Workflow（静态链式触发） | 中心化调度（LLM 动态路由） |

> **MGX 模式的混合特性：** TeamLeader → 子 Agent 是 LLM 动态路由（不走 watch），但子 Agent 内部的多步执行（如 Engineer 的 WriteCode → SummarizeCode）仍然走 BY_ORDER 的固定 SOP。两种机制共存：宏观上是 TL 动态调度，微观上是子 Agent 内部的固定 Workflow。

---

## 8. 记忆机制全景（源码验证）

MetaGPT 有三套并行的记忆实现，不同场景不同方案——从简单列表到 RAG 向量检索。

### 继承关系

```
Memory  # memory.py — 基类，纯内存消息列表
│   storage: list[Message]
│   index: DefaultDict[str, list[Message]]  # 按 cause_by 倒排索引
│
├── LongTermMemory  # longterm_memory.py — 第一代，FAISS ⚠️ 已废弃
│       memory_storage: MemoryStorage (FAISS)
│       ⚠️ __init__.py 中已注释掉，不参与主流程
│
└── RoleZeroLongTermMemory  # role_zero_memory.py — 第二代，ChromaDB
        persist_path: ".role_memory_data"
        memory_k: 200  # 短期容量上限
        similarity_top_k: 5  # 检索返回数
        _rag_engine: SimpleEngine (ChromaDB)

BrainMemory  # brain_memory.py — 第三代，独立体系
│   history: List[Message]
│   knowledge: List[Message]
│   historical_summary: str  # LLM 压缩后的摘要
│   不继承 Memory，直接继承 BaseModel
```

### 三套记忆系统对比

**Memory（基础）：**
- **存储：** Python list，按时间追加；DefaultDict 按 cause_by 建倒排索引
- **检索：** get(k) 最近 k 条、get_by_actions 按 Action 类型、try_remember 子串匹配
- **淘汰：** 无淘汰，storage 无限增长
- **持久化：** 无，进程结束即丢失
- **用途：** 所有角色的基础记忆，短期对话上下文

**RoleZeroLongTermMemory（RAG）：**
- **存储：** 继承 Memory 的 list + ChromaDB 向量数据库存溢出的旧消息
- **写入条件：** 消息数超过 memory_k=200 → 第 201 条旧消息转入 ChromaDB
- **检索条件：** 三条件同时满足才 RAG 检索 top-5：① k != 0 ② 最后消息来自用户/TeamLeader ③ 消息总数 > 200
- **淘汰：** 滑动窗口转移：旧消息复制到 ChromaDB，但不从 storage 删除
- **用途：** MGX 模式下 RoleZero 角色的长期记忆

**BrainMemory（压缩）：**
- **存储：** history（对话历史）+ knowledge（知识库）+ historical_summary（LLM 摘要）
- **压缩：** 调用 LLM 将 history 压缩成摘要 → 存入 historical_summary → 清空 history
- **持久化：** Redis 缓存，TTL 30 分钟，key = {prefix}:{user_id}:{chat_id}
- **淘汰：** LLM 摘要压缩 + Redis TTL 过期
- **用途：** AgentStore 在线服务的单用户对话

### 记忆如何喂给 LLM

**经典 SOP 模式：**
```
1. Role._act() 被调用
2. self.rc.todo.run(self.rc.history)
3. Action._run_action_node() 构建 context:
   context = "## History Messages\n" + "\n".join(reversed(history))
4. LLM 收到完整 history 作为上下文
```
> **问题：** history 无限增长，最终会超出 context window。没有任何截断或压缩策略。

**MGX 模式 (RoleZero)：**
```
1. RoleZero._think() 被调用
2. memory.get(200) — 取最近 200 条
3. 如果满足三条件 → RAG 检索 ChromaDB → top-5 相关历史
4. final = related_memories + memories（长期在前 + 短期在后）
5. LLM 收到 最近200条 + top-5 相关历史
```
> **改进：** memory_k=200 截断 + RAG 语义检索。但存储的仍是原始消息，无抽象。

### 记忆生命周期

**写入时机：**
- `memory.add_batch(self.rc.news)` — Role._observe() — 过滤后的环境消息
- `memory.add(msg)` — Role._act() — Action 执行结果
- `memory.add(AIMessage(content=command_rsp))` — RoleZero._act() — LLM 命令响应

**读取时机：**
- `self.rc.history` — Role._think() / _act() — 决定和执行 Action
- `memory.get(memory_k)` — RoleZero._think() — 构建 LLM prompt
- `rag_engine.retrieve(query)` — RoleZeroLongTermMemory.get() — RAG 检索

**淘汰策略：**
- Memory: 无淘汰，storage 无限增长
- RoleZeroLongTermMemory: 超 200 条时复制到 ChromaDB，但 storage 不删除
- BrainMemory: LLM 摘要压缩 + Redis TTL 30分钟（唯一有真正清理的）

### MetaGPT vs Claude 记忆机制

| MetaGPT Memory | Claude Memory |
|----------------|---------------|
| 存储**原始 Message 对话原文** | 存储**从对话中提炼的结构化知识** |
| 每条消息都存，量大无筛选 | 只存有价值的，精简筛选 |
| 向量相似度匹配原文内容 | 按主题索引，人工判断相关性 |
| 无抽象、无总结、无提炼 | LLM 总结后写入结构化文档 |
| 本质：**聊天记录的 Ctrl+F** | 本质：**助理帮你做的笔记** |
| 用途：给 LLM 提供"我做到哪了"的上下文 | 用途：让 Claude 记住"用户是谁" |

### 关键结论

1. **Memory 基类是"对话上下文"，不是"记忆"。** 只是一个 list，把所有 Message 存起来拼成 LLM 的 prompt。没有遗忘、没有抽象、没有检索。

2. **RoleZeroLongTermMemory 是"聊天记录的语义搜索"。** 用 ChromaDB 做向量检索，但存的仍是原始消息。检索到的内容很长、有噪音，直接塞进 prompt。

3. **BrainMemory 是唯一有"压缩"的设计。** 用 LLM 把对话摘要后存 Redis，但只用于 AgentStore 在线服务，团队协作模式不使用。

4. **三套系统是并行的，不是叠加的。** 不同场景用不同实现，没有统一的记忆层。

5. **与 Claude 记忆的核心差距：没有"从对话中提炼知识"的机制。** MetaGPT 存原文取原文，Claude 存总结取总结。

---

## 9. TeamLeader 调度机制（源码验证）

> **TeamLeader 定位：** 继承链 TeamLeader → RoleZero → Role。name="Mike"，profile="Team Leader"，max_react_loop=3。使用 @register_tool 装饰器注册工具，通过 tool_execution_map 实现命令式调度。

### 核心能力

**需求接收：**
- 接收用户原始需求
- 解析需求意图
- 判断任务类型（快速问答/复杂任务）

**任务规划：**
- 使用 Planner 制定执行计划
- 任务拆解和排序
- 依赖关系分析

**消息分发：**
- publish_team_message 分发任务
- 指定接收者和任务内容
- 创建 UserMessage 让目标角色当用户请求处理

**进度跟踪：**
- 监控任务完成状态
- 处理异常和错误
- 子 Agent 结果自动回流到 TL

### 调度流程

```python
# TeamLeader._think() — 注入团队信息后调用父类
async def _think(self) -> bool:
    self.instruction = TL_INSTRUCTION.format(team_info=self._get_team_info())
    return await super()._think()  # RoleZero._think() 做 LLM 调用

# TeamLeader.publish_team_message() — 分发任务
def publish_team_message(self, content: str, send_to: str):
    self._set_state(-1)  # 暂停 TL，等待子 Agent 响应
    self.publish_message(
        UserMessage(content=content, sent_from=self.name,
                    send_to=send_to, cause_by=RunCommand),
        send_to=send_to
    )

# TeamLeader.publish_message() — 传递 publicer 标记
def publish_message(self, msg, send_to="no one"):
    msg.send_to = send_to
    self.rc.env.publish_message(msg, publicer=self.profile)  # → 路径3
```

### 并行调度

```python
# base_env.py — Environment.run() 并行执行所有非 idle Role
async def run(self, k=1):
    for _ in range(k):
        futures = []
        for role in self.roles.values():
            if role.is_idle:
                continue
            futures.append(role.run())
        if futures:
            await asyncio.gather(*futures)  # 并行执行
```

### 上下文传递机制

1. **结构化内容传递** — 通过 instruct_content 传递结构化数据（PRD、设计文档、任务列表）
2. **文件引用** — 使用文件路径而非文件内容，减少消息体积
3. **记忆继承** — 每个 Agent 维护独立 Memory，通过消息订阅获取相关上下文
4. **共享工作空间** — 通过 ProjectRepo 和 Git 管理共享的代码和文档

---

## 10. 与其他框架的对比

| 框架 | 特点 |
|------|------|
| **MetaGPT** | 固定角色定义（PM、Architect、Engineer）、标准化 SOP 流程、发布-订阅消息系统、TeamLeader 中心化协调、支持代码生成全流程、内置代码审查和测试 |
| **AutoGen** | 灵活的对话式协作、动态角色创建、人类参与循环、无固定 SOP、需手动定义流程、支持多种 LLM |
| **CrewAI** | 基于角色的协作、任务委派机制、工具集成、无代码生成特化、简单易用、灵活的任务定义 |
| **LangGraph** | 图状态机架构、精确流程控制、可视化工作流、学习曲线陡峭、高度可定制、支持复杂逻辑 |

### MetaGPT 的独特优势

**领域特化：** 专为软件开发场景设计，内置完整的开发流程（需求→设计→编码→测试），开箱即用。

**标准化 SOP：** 定义了清晰的角色职责和工作流程，减少了随机性，提高了输出质量的稳定性。

**结构化通信：** 通过 instruct_content 传递结构化数据，确保信息在角色间准确传递，减少信息损失。

---

> 基于 MetaGPT 源码验证 · 调研时间：2026年5月 · 合并自 agent-orchestration-analysis / class-tree / memory-mechanism
