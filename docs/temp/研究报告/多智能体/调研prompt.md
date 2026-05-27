1. 记忆调研：memory机制的详情，包括写入和读取两方面，a.agent什么时候写入，他写入依据的内容是什么（对话历史？修改内容？还是什么），他写入的重点是什么？，这部分需要看他写入的prompt b. 读取的时机是什么？是上下文加载的时候主动读取还是工具调用读取，若都有他们之间的读取区别是什么？ 
2. 工具调用，主要说明a. function call的tool schemas他是怎么写的 b. 工具的错误处理机制是什么等内容 
3. agent之间通信：main agent/leader/manager发送给worker/subagent的信息格式是什么，包含消息的数据结构（如果有），具体的prompt（主要查看具体的prompt的结构，是否有一定的范式）。subagent的llm调用之前的context组成。两个内容需要各举一个例子，比如：
a. main agent -> subagent: main agent 在判断需要发送给subagent工作时应该有一个prompt指导main agent如何编写内容
```
# task
你的任务是..
# 注意事项
xxx

```
b. subagent的context组成:subagent为了更好的执行任务，他的context包含了哪些内容？
```
# main agent message
# memory
...
```
4. 消息机制：1. 外部用户指令发送到内部消息的架构 2. 获取外部指令之后agent team内部的消息机制（比如发布-订阅，或者简单的工具调用）