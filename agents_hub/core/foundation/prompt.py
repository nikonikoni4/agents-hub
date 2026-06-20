"""系统级 prompt 模板"""

COMPACT_CONTEXT_PROMPT = """\
<compact_request>
请总结你当前的工作上下文：
1. 已经完成的工作内容
2. 当前正在做的事情
3. 接下来需要完成的任务
4. 关键决策
5. 重要约束和提示词
请简洁明了，控制在 1000字以内。
</compact_request>
"""
