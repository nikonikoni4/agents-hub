# 需要的架构
1. workflow : 按照设定顺序执行
2. orchestrate-subagent ： subagent之间不能直接对话，必须通过主agent协调
3. subagent之间的对话，比如A委派B执行一个任务，不经过主agents
4. boss直接与subagent对话：@subagents

# 设计1：用orchestrate-subagent 实现 workflow
1. workflow可以由orchestrate-subagent实现，只要主agent编排一个顺序流程即可，而且可以处理潜在的问题：因为claude code / codex本身就是已经完善的平台，但是他们可能不会在执行一个任务的时候直接完成任务，而是可能会询问一些问题（取决于仓库的规则），比如某些仓库可能要求需要澄清需求，这时候就会停下来，而无主agent的workflow会被中断并且没有完成任务。就算system prompt中设定了直接执行，但是不确定性很高

# 设计2：
subagent之间的对话有两种方式:
1. subagent A -> 发送信息给main agent -> subagent B
2. subagent A -> 直接发送信息给subagent B
同时subagent还需要再群聊内直接由boss@回复
## 1. 如果subagent之间的消息不经过main agent会怎么样
1. main agent可能会不知道进度，但是如果只是任务过程中的中间会话，那么main agent就不需要知道。这个取决于[main agent，需不需要知道中间传递的内容]
2. subagent之间的传递应该是有限制的，应该是一个不同的模式。
## 2. 如何判断agent的结果是否应该返回到群聊记录呢？
1. autogen是默认都返回结果到聊天记录（buffer）
## 3. 是否需要一个路由呢？
是否需要一个专门的路由（秘书），他判断subagent之间的内容以及结果是否需要发送给main agent和群聊，这个路由也是一个llm

# 多agent架构
从消息设计上来说目前倾向于发布-订阅，原因：
1. 为什么不选择deer flow 和 crewAI的使用工具调用作为派遣subagent的方法呢？
因为群聊有时候是需要subagent发话的，如果是工具调用，就算不是处于main agent的tool loop内（调用的时候只启动，返回可以找到这个启动进程的相关信息和session，而不是等待subagent执行完成之后才通过tool call result返回），[等会，这个方案似乎也可以]。main agent -> subagent tool call -> tool call 返回subagent启动信息，这里工具循环就结束了，可以设置定时和超时，没完成在一次触发信息[这里有一个问题是，在claude code中即使subagent在后台运行，但是这轮会话还是没有结束，这个是怎么做到的？]，等待subagent结束，返回信息，然后再判断返回信息是否需要发送到群聊。[结论：似乎如果是main agent调用subagent，无论是工具调用还是订阅发布都是可以的]
2. 如果要实现@subagent，然后subagent回话，其实orchestrate-subagent 经过main agent也可以，但是这里多一次调用，不合适
3. 如果是发布-订阅要怎么做？
主要参考metaGPT，但是不需要_observe和_watch机制，而是强制通过send_by指定
1. 模式1：orchestrate-subagent，main agent 发送消息给 subagent ,实现编排
        @subagent : 不经过main agent, subagent 直接与main agent对话

# 是否需要一个秘书？
1. 如何保证群聊的上下文？如果想autogen，我觉得上下文可能会被污染，因为说的内容可能和当前subagent的任务无关，比如前端设计再群里面，但是后端数据库在群聊中讨论，这个讨论内容与前端完全无关，根本就不需要他知道这些上下文。本质上[多agent架构设计是最优化不同agent之间的上下文]。这么看了好像是需要一个秘书的工作。main agent通常负责编排，他也不需要集体内容的讨论，所以他的上下文接受还是需要一个秘书来对接？

