# Claude Code 和 Codex CLI 输出格式研究报告

## 概述

本报告分析了 Claude Code 和 Codex CLI 的流式与非流式输出格式，说明各种输出的特点和包含的字段信息。

---

## 一、Claude Code 输出格式

### 1.1 非流式输出 (`-p`)

**特点：**
- 纯文本格式
- 只包含最终回答内容
- 不显示思考过程、工具调用、元数据
- 适合快速查询和脚本集成

**包含字段：**
- 最终回答文本（纯文本）

**示例：**
```
在 Claude Code CLI 中，我的 `<thinking>` 思考过程**默认不会显示**给用户。

具体行为：
- **流式输出**：你看到的是我的最终回答文本和工具调用结果，思考过程在后台进行
- **非流式输出**：同样只显示最终输出，不包含 `<thinking>` 标签内的内容
```

---

### 1.2 流式输出 (`-p --verbose --output-format=stream-json --include-partial-messages`)

**特点：**
- JSON Lines 格式（每行一个 JSON 对象）
- 包含完整的事件流
- 实时推送内容增量
- 包含丰富的元数据

**示例：**

```json
{"type":"system","subtype":"hook_started","hook_id":"...","hook_name":"SessionStart:startup","hook_event":"SessionStart","uuid":"6044579f-54ac-4faf-bb53-ea9d926a6ae1","session_id":"..."}
{"type":"system","subtype":"hook_response","hook_id":"...","hook_name":"SessionStart:startup","hook_event":"SessionStart","output":"...","stdout":"...","stderr":"","exit_code":0,"outcome":"success","uuid":"7ee9abbe-c682-4dc8-8ce8-4ea64f3f8920","session_id":"..."}
{"type":"system","subtype":"init","cwd":"D:\\desktop\\软件开发\\agents-hub","session_id":"...","tools":["Task","AskUserQuestion","Bash",...],"mcp_servers":[{"name":"MiniMax","status":"connected"}],"model":"claude-opus-4-7[1m]","permissionMode":"auto","slash_commands":["ai-news-push",...],"memory_paths":{"auto":"C:\\Users\\15535\\.claude\\projects\\..."},"fast_mode_state":"off"}
{"type":"system","subtype":"status","status":"requesting","uuid":"...","session_id":"..."}
{"type":"stream_event","event":{"type":"message_start","message":{"id":"msg_20260523032028","content":[],"model":"claude-opus-4-7","usage":{"input_tokens":1,"output_tokens":1,"cache_creation_input_tokens":47863,"cache_read_input_tokens":0},"stop_reason":null,"type":"message","role":"assistant"}},"session_id":"...","parent_tool_use_id":null,"uuid":"...","ttft_ms":2816}
{"type":"stream_event","event":{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"index":0,"delta":{"type":"text_delta","text":"不"},"type":"content_block_delta"},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"会"}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"显"}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"text":"示。\n\n我","type":"text_delta"}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
```
```json
) PS D:\desktop\软件开发\agents-hub\.claude\worktrees\task-15-memory-assistant> claude -p --verbose --output-format stream-json --include-partial-messages " 你好，我现在在测试流式输出，收到后你先回复：收到任务，我将查看这个文档，然后你在回复我正在阅读这个文档，然后你在查看test.md文档，然后你在回复我这个文档的内容”
{"type":"system","subtype":"init","cwd":"D:\\desktop\\软件开发\\agents-hub\\.claude\\worktrees\\task-15-memory-assistant","session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","tools":["Task","AskUserQuestion","Bash","CronCreate","CronDelete","CronList","Edit","EnterPlanMode","EnterWorktree","ExitPlanMode","ExitWorktree","Glob","Grep","ListMcpResourcesTool","NotebookEdit","Read","ReadMcpResourceTool","ScheduleWakeup","Skill","TaskOutput","TaskStop","TodoWrite","WebFetch","WebSearch","Write","mcp__agents-hub__archive_task_list","mcp__agents-hub__assign_tasks_to_team","mcp__agents-hub__call_agent","mcp__agents-hub__check_agent_call","mcp__agents-hub__create_agent","mcp__agents-hub__create_group_chat","mcp__agents-hub__create_loop","mcp__agents-hub__delete_loop","mcp__agents-hub__get_loop_status","mcp__agents-hub__health_check","mcp__agents-hub__list_loop_executions","mcp__agents-hub__list_loops","mcp__agents-hub__start_loop","mcp__agents-hub__stop_loop","mcp__iqs-mcp-server-search__common_search","mcp__mimo-image__understand_image"],"mcp_servers":[{"name":"iqs-mcp-server-search","status":"connected"},{"name":"mimo-image","status":"connected"},{"name":"agents-hub","status":"connected"}],"model":"mimo-v2.5-pro[1m]","permissionMode":"bypassPermissions","slash_commands":["agent-knowledge-base","ai-decision-making","ai-mistake-recorder","algorithmic-art","brainstorming","ci-check","ci-check-fix","code-review","deep-answer","find-skills","frontend-design","grill-with-docs","hand-off","hand-on","huashu-design","knowledge-crystallizer","knowledge-learning","knowledge-research","local-code-review","parallel-worktree","progress-tracker","setup-matt-pocock-skills","skill-creator","subagent-driven-development","systematic-debugging","task-checklist","task-echo","taste-skill","tdd","test-driven-development","to-issues","to-prd","triage","user-workflow","utils-test-write","web-artifacts-builder","webapp-testing","write-decisions","write-project-rules","writing-plans","review","code-review:code-review","update-config","debug","simplify","batch","fewer-permission-prompts","loop","claude-api","clear","compact","context","heapdump","init","security-review","usage","insights","goal","team-onboarding"],"apiKeySource":"none","claude_code_version":"2.1.140","output_style":"default","agents":["Explore","general-purpose","Plan","statusline-setup"],"skills":["agent-knowledge-base","ai-decision-making","ai-mistake-recorder","algorithmic-art","brainstorming","ci-check","ci-check-fix","code-review","deep-answer","find-skills","frontend-design","grill-with-docs","hand-off","hand-on","huashu-design","knowledge-crystallizer","knowledge-learning","knowledge-research","local-code-review","parallel-worktree","progress-tracker","setup-matt-pocock-skills","skill-creator","subagent-driven-development","systematic-debugging","task-checklist","task-echo","taste-skill","tdd","test-driven-development","to-issues","to-prd","triage","user-workflow","utils-test-write","web-artifacts-builder","webapp-testing","write-decisions","write-project-rules","writing-plans","update-config","debug","simplify","batch","fewer-permission-prompts","loop","claude-api"],"plugins":[{"name":"code-review","path":"C:\\Users\\15535\\.claude\\plugins\\marketplaces\\claude-plugins-official\\plugins\\code-review","source":"code-review@claude-plugins-official"}],"analytics_disabled":false,"uuid":"e6ff4c80-badd-47dd-9ee5-7ae63e7b9f80","memory_paths":{"auto":"C:\\Users\\15535\\.claude\\projects\\D--desktop------agents-hub\\memory\\"},"fast_mode_state":"off"}
{"type":"system","subtype":"status","status":"requesting","uuid":"1aeafc0b-f86d-4620-a623-0768910ed5d1","session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9"}
{"type":"stream_event","event":{"type":"message_start","message":{"id":"msg_9adf39add37349c6a66d1c54","type":"message","role":"assistant","model":"mimo-v2.5-pro","content":[],"usage":{"input_tokens":0,"output_tokens":0}}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"dacbc14f-4f28-4de5-9bae-b0d495fc14fa","ttft_ms":2186}
{"type":"stream_event","event":{"type":"content_block_start","index":0,"content_block":{"type":"thinking","thinking":"","signature":""}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"07b8c327-10b8-4c52-aa56-a4dac5d69a17"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":"The"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"8114ca60-98da-4233-85b1-9ff7edf33760"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" user wants to"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"89e519e5-d7d8-48c2-9fbc-62fb408c5161"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" test streaming"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"d5c4c08d-d014-4878-8ead-895c38e99db7"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" output and"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"0e2bcc04-739d-4566-94e1-b9bb805eef1b"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" wants"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"de8f0825-17a0-4f7f-9b1a-509cd71515ba"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" me to follow a"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"9c2c33c7-36a6-452a-af71-e448813afe86"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" specific sequence of responses"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"fe81fd37-8c12-40d1-8865-e3d253c660ed"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":". Let me follow"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"9e1eba36-7b50-4ced-8382-7b09ff6b896e"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" their"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"d1abe3ed-5fc1-486a-b83b-b424cf466b16"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" instructions."},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"8cad9248-3c36-4495-8e64-3aecc1295162"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"signature_delta","signature":""},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"0c8f49a0-57f2-4d75-95d9-aaf2d738051e"}
{"type":"assistant","message":{"id":"msg_9adf39add37349c6a66d1c54","type":"message","role":"assistant","model":"mimo-v2.5-pro","content":[{"type":"thinking","thinking":"The user wants to test streaming output and wants me to follow a specific sequence of responses. Let me follow their instructions.","signature":""}],"usage":{"input_tokens":0,"output_tokens":0},"context_management":null},"parent_tool_use_id":null,"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","uuid":"0eec12ee-51e1-4a75-84c5-f12d476bb797"}
{"type":"stream_event","event":{"type":"content_block_stop","index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"2b5b4a95-05a5-4125-9899-7a4f357a109b"}
{"type":"stream_event","event":{"type":"content_block_start","index":1,"content_block":{"type":"text","text":""}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"37c7f69c-2e30-4a96-831e-e747877d4a5b"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"收到任务"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"bc78f322-06eb-4cbd-b19e-463b1c344d58"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"，我将查看"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"bc3f525d-e230-42a6-9266-3cdab54257fa"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"这个文档。"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"a8568a03-1008-477f-be83-bc67564a8e68"}
{"type":"assistant","message":{"id":"msg_9adf39add37349c6a66d1c54","type":"message","role":"assistant","model":"mimo-v2.5-pro","content":[{"type":"text","text":" 收到任务，我将查看这个文档。"}],"usage":{"input_tokens":0,"output_tokens":0},"context_management":null},"parent_tool_use_id":null,"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","uuid":"abb52462-eca5-4bd1-9c7d-11e255c9ab62"}
{"type":"stream_event","event":{"type":"content_block_stop","index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"354bc17e-1a11-4de5-b2ab-224664500167"}
{"type":"stream_event","event":{"type":"content_block_start","index":2,"content_block":{"type":"tool_use","id":"call_e0065f470ede45cabb2798a5","name":"Read","input":{}}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"501091fa-8dc3-4a05-9aa6-2191e4d94d56"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"input_json_delta","partial_json":"{\"file_path\": \"D:\\\\desktop\\\\软件开发\\\\agents-hub\\\\.claude\\\\worktrees\\\\task-15-memory-assistant\\\\test.md\"}"},"index":2},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"567b49f1-f280-4fd0-87ea-45e500715ee4"}
{"type":"assistant","message":{"id":"msg_9adf39add37349c6a66d1c54","type":"message","role":"assistant","model":"mimo-v2.5-pro","content":[{"type":"tool_use","id":"call_e0065f470ede45cabb2798a5","name":"Read","input":{"file_path":"D:\\desktop\\软件开发\\agents-hub\\.claude\\worktrees\\task-15-memory-assistant\\test.md"}}],"usage":{"input_tokens":0,"output_tokens":0},"context_management":null},"parent_tool_use_id":null,"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","uuid":"93764f4b-120f-4d48-b1ab-38098ec61c8a"}
{"type":"stream_event","event":{"type":"content_block_stop","index":2},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"f2fb6587-4e6b-43a2-8a58-190b5b417b53"}
{"type":"stream_event","event":{"type":"message_delta","delta":{"stop_reason":"tool_use"},"usage":{"input_tokens":35143,"output_tokens":81}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"2227f8c0-55c4-4d5b-a32c-81a6177556ba"}
{"type":"stream_event","event":{"type":"message_stop"},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"9c42e942-84a5-4a8f-85c3-68bb94b7fbba"}
{"type":"user","message":{"role":"user","content":[{"tool_use_id":"call_e0065f470ede45cabb2798a5","type":"tool_result","content":"1\t# Test File\n2\t\n3\tThis is a test file created by Manager.\n4\t"}]},"parent_tool_use_id":null,"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","uuid":"ee3720cc-fc85-4bd2-bd2e-55d8ef42b6b5","timestamp":"2026-06-24T12:19:11.537Z","tool_use_result":{"type":"text","file":{"filePath":"D:\\desktop\\软件开发\\agents-hub\\.claude\\worktrees\\task-15-memory-assistant\\test.md","content":"# Test File\n\nThis is a test file created by Manager.\n","numLines":4,"startLine":1,"totalLines":4}}}
{"type":"system","subtype":"status","status":"requesting","uuid":"feb7f43e-d894-4325-956e-38d7078a45d2","session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9"}
{"type":"stream_event","event":{"type":"message_start","message":{"id":"msg_0eaea44a372f4e9dab322eac","type":"message","role":"assistant","model":"mimo-v2.5-pro","content":[],"usage":{"input_tokens":0,"output_tokens":0}}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"bdb4ab1d-82dd-4c54-bc17-c7200428ecdc","ttft_ms":1114}
{"type":"stream_event","event":{"type":"content_block_start","index":0,"content_block":{"type":"thinking","thinking":"","signature":""}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"30ed8c94-f140-4792-b67d-b9aaf8db73ed"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":"I"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"f5e160da-e531-45ba-aadd-3f5cf29abcf9"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" read"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"4e41443d-7572-4509-a13f-75305dc46c10"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" the test.md file"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"0a3fb3cf-f6eb-4fee-a9ae-85cd843732f1"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":". Now"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"ae25a3d5-7526-483c-8253-e3101c600a64"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" let"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"deb96fd9-ce87-4af2-8699-2dea50fb493e"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" me respond"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"6b7ea2ce-8c2e-44dc-b7fb-dac16b7d8788"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" with"},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"66f5c72f-0824-459b-a753-4d3a6049b3f4"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"thinking_delta","thinking":" the content."},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"6afbc54e-a969-4e00-a649-36f16b1b3592"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"signature_delta","signature":""},"index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"a3623201-8540-4952-ae9d-e610f2ea71fa"}
{"type":"assistant","message":{"id":"msg_0eaea44a372f4e9dab322eac","type":"message","role":"assistant","model":"mimo-v2.5-pro","content":[{"type":"thinking","thinking":"I read the test.md file. Now let me respond with the content.","signature":""}],"usage":{"input_tokens":0,"output_tokens":0},"context_management":null},"parent_tool_use_id":null,"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","uuid":"5ec893f3-4551-44c5-b29a-0cb8209faf7d"}
{"type":"stream_event","event":{"type":"content_block_stop","index":0},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"c2644c61-0843-43db-beb2-b9b5e7c4077d"}
{"type":"stream_event","event":{"type":"content_block_start","index":1,"content_block":{"type":"text","text":""}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"39cf3135-d485-4446-9314-66da1b1c0815"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"我正在阅读这个"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"2fae37f8-5a0d-443f-99bb-c42be0009753"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"文档。\n\n文档"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"e9360b28-38bf-406f-a425-5ed56a3d5f9f"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"内容如下：\n\n这是一个"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"c7303e98-9076-4a00-ab17-6faaa1619535"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"测试文件，由"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"7401aac7-0c87-4b3f-ad55-f816f96a0aa1"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":" Manager 创建。"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"7d8c45c9-5836-4ea8-8b32-d80817a8ad91"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"文件内容很简单"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"fd204f21-ec7b-4b19-815d-dcb11f888a78"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"，只有一行"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"98ae183e-9bd4-4503-871d-65d6645b9288"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"文字"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"ad51909a-8b7f-42bf-a639-cd615a740c7f"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"说明：\"This is"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"e95afe2c-6174-4335-ba7f-add6d8952c42"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":" a test file created"},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"9aedb27a-56be-4413-8959-985cab9ab19a"}
{"type":"stream_event","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":" by Manager.\""},"index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"0511889f-1a6f-45fd-9dbd-9e59f7779ce2"}
{"type":"assistant","message":{"id":"msg_0eaea44a372f4e9dab322eac","type":"message","role":"assistant","model":"mimo-v2.5-pro","content":[{"type":"text","text":" 我正在阅读这个文档。\n\n文档内容如下：\n\n这是一个测试文件，由 Manager 创建。文件内容很简单，只有一行文字说明：\"This is a test file created by Manager.\""}],"usage":{"input_tokens":0,"output_tokens":0},"context_management":null},"parent_tool_use_id":null,"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","uuid":"dc74856e-03e2-4ef4-a194-dd71d77c7e62"}
{"type":"stream_event","event":{"type":"content_block_stop","index":1},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"d8355e7a-e0ff-4abb-9636-753b1736f204"}
{"type":"stream_event","event":{"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"input_tokens":119,"output_tokens":55,"cache_read_input_tokens":35136}},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"d97de2f2-bc14-4646-b081-404b6a7f6d9c"}
{"type":"stream_event","event":{"type":"message_stop"},"session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","parent_tool_use_id":null,"uuid":"152afa72-2fbb-44d2-9fbc-0f1de9a0dabe"}
{"type":"result","subtype":"success","is_error":false,"api_error_status":null,"duration_ms":6583,"duration_api_ms":6137,"num_turns":2,"result":"我正在阅读这个文档。\n\n文档内容如下：\n\n这是一个测试文件，由 Manager 创建。文件内容很简单，只有一行文字说明：\"This is a test file created by Manager.\"","stop_reason":"end_turn","session_id":"13ca6990-470c-4653-a3e1-abd5b59b86e9","total_cost_usd":0.197278,"usage":{"input_tokens":35262,"cache_creation_input_tokens":0,"cache_read_input_tokens":35136,"output_tokens":136,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":0},"inference_geo":"","iterations":[],"speed":"standard"},"modelUsage":{"mimo-v2.5-pro[1m]":{"inputTokens":35262,"outputTokens":136,"cacheReadInputTokens":35136,"cacheCreationInputTokens":0,"webSearchRequests":0,"costUSD":0.197278,"contextWindow":1000000,"maxOutputTokens":32000}},"permission_denials":[],"terminal_reason":"completed","fast_mode_state":"off","uuid":"284b4f4b-466c-4f8b-b339-6e8bcc17ab15"}
```


**事件类型：**

| 事件类型 | subtype / delta.type | 说明 |
|---------|----------------------|------|
| `system` | `hook_started` | Hook 开始执行 |
| `system` | `hook_response` | Hook 执行完成，包含输出 |
| `system` | `init` | 会话初始化信息 |
| `system` | `status` | 状态变更（requesting 等） |
| `stream_event` | `message_start` | 消息开始，包含 token 使用统计 |
| `stream_event` | `content_block_start` | 内容块开始（`content_block.type` 可为 `text`、`thinking`、`tool_use`） |
| `stream_event` | `content_block_delta` / `text_delta` | 文本内容增量（逐字输出） |
| `stream_event` | `content_block_delta` / `thinking_delta` | 思考过程增量（逐字输出，`--include-partial-messages` 时可见） |
| `stream_event` | `content_block_delta` / `input_json_delta` | 工具调用输入增量（JSON 片段） |
| `stream_event` | `content_block_delta` / `signature_delta` | 签名增量（thinking 块结束时的签名数据） |
| `stream_event` | `content_block_stop` | 内容块结束 |
| `stream_event` | `message_delta` | 消息元数据更新 |
| `stream_event` | `message_stop` | 消息结束 |
| `assistant` | — | 非流式完整消息，每个 `message_stop` 后输出一次，包含完整的 content 块 |

**关键字段：**

**system.init 事件包含：**
- `cwd` - 工作目录
- `session_id` - 会话 ID
- `tools` - 可用工具列表
- `mcp_servers` - MCP 服务器列表（name, status）
- `model` - 模型名称
- `permissionMode` - 权限模式
- `slash_commands` - 可用的 slash 命令
- `memory_paths` - 内存路径
- `claude_code_version` - CLI 版本
- `agents` - 可用的 agent 列表
- `skills` - 可用的 skill 列表
- `plugins` - 已加载的插件列表

**stream_event.message_start 包含：**
- `message.id` - 消息 ID
- `message.model` - 模型名称
- `message.usage` - Token 使用统计
  - `input_tokens` - 输入 token 数
  - `output_tokens` - 输出 token 数
  - `cache_creation_input_tokens` - 缓存创建 token 数
  - `cache_read_input_tokens` - 缓存读取 token 数
- `ttft_ms` - Time to first token（首字延迟）

**stream_event.content_block_delta 包含：**
- `index` - 内容块索引
- `delta.type` - 增量类型（`text_delta` / `thinking_delta` / `input_json_delta` / `signature_delta`）
- `delta.text` - 增量文本内容（仅 `text_delta`）
- `delta.thinking` - 思考增量内容（仅 `thinking_delta`）
- `delta.partial_json` - 工具输入 JSON 片段（仅 `input_json_delta`）
- `delta.signature` - 签名数据（仅 `signature_delta`）
- `session_id` - 会话 ID
- `parent_tool_use_id` - 父工具调用 ID（如果有）
- `uuid` - 事件唯一标识

**content_block_start 的 content_block.type 可能值：**
- `text` - 文本块
- `thinking` - 思考块（包含 `thinking` 和 `signature` 字段）
- `tool_use` - 工具调用块（包含 `id`、`name`、`input` 字段）

**assistant 事件包含：**
- `message.id` - 消息 ID
- `message.content` - 完整内容块数组，每个元素包含 `type`（`text` / `thinking` / `tool_use`）及对应字段
- `message.usage` - Token 使用统计
- `parent_tool_use_id` - 父工具调用 ID
- `session_id` - 会话 ID

**单轮回复的典型事件流（含思考）：**

```
stream_event  content_block_start   index=0, type=thinking     ← 思考块开始
stream_event  content_block_delta   delta.type=thinking_delta  ← 思考内容（多条）
stream_event  content_block_delta   delta.type=signature_delta ← 思考签名
stream_event  content_block_start   index=1, type=text         ← 文本块开始
stream_event  content_block_delta   delta.type=text_delta      ← 文本内容（多条）
stream_event  content_block_stop    index=1                    ← 文本块结束
stream_event  message_delta                                    ← 消息元数据
stream_event  message_stop                                     ← 消息结束
assistant     (完整消息，包含 thinking + text 内容块)           ← 非流式汇总
```

若包含工具调用，文本块之后会追加 `tool_use` 类型的 content_block。

---

## 二、Codex CLI 输出格式

### 2.1 非流式输出 (`codex exec`)

**特点：**
- 格式化的文本输出
- 包含完整的工作日志
- 显示会话元数据、工具调用、Agent 思考过程
- 适合调试和审计

**输出结构：**

```
┌─────────────────────────────────────┐
│ 1. 会话元数据区                      │
│    - CLI 版本、模型、配置信息         │
├─────────────────────────────────────┤
│ 2. 对话交互区                        │
│    - user: 用户输入                  │
│    - codex: Agent 工作说明           │
├─────────────────────────────────────┤
│ 3. 工具执行区                        │
│    - exec: 命令                      │
│    - succeeded/failed: 结果          │
│    - 完整的 stdout 输出              │
├─────────────────────────────────────┤
│ 4. Agent 回复区                      │
│    - codex: 最终回答                 │
│    - tokens used: Token 统计         │
└─────────────────────────────────────┘
```

**包含字段：**

**1. 会话元数据区：**
- `version` - CLI 版本（如 "OpenAI Codex v0.133.0"）
- `workdir` - 工作目录
- `model` - 使用的模型
- `provider` - 提供商
- `approval` - 审批模式
- `sandbox` - 沙箱权限
- `reasoning effort` - 推理强度
- `reasoning summaries` - 推理摘要设置
- `session id` - 会话 ID

**2. 对话交互区：**
- 角色标识：`user` 或 `codex`（单独一行）
- 消息内容：角色标识后的所有行，直到下一个角色标识

**3. 工具执行区：**
- `exec` - 工具调用标识（单独一行）
- 命令行：完整的命令字符串（通常以引号开头）
- 执行结果：`succeeded in Xms:` 或 `failed in Xms:`
- 输出内容：`---` 分隔符后的所有内容，直到下一个 `codex` 标识

**4. Agent 回复区：**
- `codex` - 角色标识
- 回答内容：多行文本
- `tokens used` - Token 统计标识（单独一行）
- Token 数量：下一行的数字（可能包含逗号分隔符）

**可提取的信息：**
1. **对话内容** - 所有 user 和 codex 的消息
2. **Agent 思考过程** - 工具调用前的 codex 消息（工作说明）
3. **工具调用** - exec 块中的命令、执行时间、输出结果
4. **Token 使用** - tokens used 后的数字
5. **最终答案** - 最后一个 codex 消息

---

### 2.2 流式输出 (`codex exec --json`)

**特点：**
- JSON Lines 格式
- 事件驱动模型
- 实时推送工具执行和消息

**示例：**

```json
{"type":"thread.started","thread_id":"019e5122-2a0e-7c61-a26b-19c036bf9315"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"我会先按当前会话规则加载 `superpowers:using-superpowers`，确认这类问题不需要额外项目文件读取。"}}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"\"C:\\\\Program Files\\\\PowerShell\\\\7\\\\pwsh.exe\" -Command \"Get-Content -LiteralPath '...'\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"\"C:\\\\Program Files\\\\PowerShell\\\\7\\\\pwsh.exe\" -Command \"Get-Content -LiteralPath '...'\"","aggregated_output":"---\r\nname: using-superpowers\r\n...","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"不会。\n\n在这个 CLI/API 环境里，我的隐藏思考过程不会出现在流式或非流式输出中..."}}
{"type":"turn.completed","usage":{"input_tokens":24773,"cached_input_tokens":11264,"output_tokens":322,"reasoning_output_tokens":0}}
```

```json
(base) PS D:\desktop\软件开发\agents-hub\.claude\worktrees\task-15-memory-assistant> codex exec --json "你好，我现在在测试流式输出，收到后你先回复：收到任务，我将查看这个文档，然后你在回复我正在阅读这个文档，然后你在查看test.md文档，然后你在回复我这个文档的内容"
{"type":"thread.started","thread_id":"019ef990-f050-7500-b400-6c50f0ed9f76"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"收到任务，我将查看这个文档。"}}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"\"C:\\\\Program Files\\\\PowerShell\\\\7\\\\pwsh.exe\" -Command 'Get-Content -Path test.md'","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"\"C:\\\\Program Files\\\\PowerShell\\\\7\\\\pwsh.exe\" -Command 'Get-Content -Path test.md'","aggregated_output":"# Test File\r\n\r\nThis is a test file created by Manager.\r\n","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"正在阅读这个文档。\n\n这个文档的内容是：\n\n```markdown\n# Test File\n\nThis is a test file created by Manager.\n```"}}
{"type":"turn.completed","usage":{"input_tokens":26750,"cached_input_tokens":10496,"output_tokens":123,"reasoning_output_tokens":0}}
```
**事件类型：**

| 事件类型 | 说明 |
|---------|------|
| `thread.started` | 线程开始，包含 thread_id |
| `turn.started` | 回合开始 |
| `turn.completed` | 回合结束，包含 token 使用统计 |
| `item.started` | 项目开始（消息或工具调用） |
| `item.completed` | 项目完成 |

**Item 类型：**

| item.type | 说明 |
|-----------|------|
| `agent_message` | Agent 发送的消息 |
| `command_execution` | 命令执行（工具调用） |

**关键字段：**

**thread.started 包含：**
- `thread_id` - 线程 ID

**item.completed (agent_message) 包含：**
- `item.id` - 项目 ID
- `item.type` - 类型（"agent_message"）
- `item.text` - 消息内容

**item.started (command_execution) 包含：**
- `item.id` - 项目 ID
- `item.type` - 类型（"command_execution"）
- `item.command` - 执行的命令
- `item.aggregated_output` - 聚合输出（进行中为空）
- `item.exit_code` - 退出码（进行中为 null）
- `item.status` - 状态（"in_progress"）

**item.completed (command_execution) 包含：**
- `item.id` - 项目 ID
- `item.type` - 类型（"command_execution"）
- `item.command` - 执行的命令
- `item.aggregated_output` - 完整输出
- `item.exit_code` - 退出码
- `item.status` - 状态（"completed" 或 "failed"）

**turn.completed 包含：**
- `usage.input_tokens` - 输入 token 数
- `usage.cached_input_tokens` - 缓存输入 token 数
- `usage.output_tokens` - 输出 token 数
- `usage.reasoning_output_tokens` - 推理输出 token 数

### 2.3 Codex `turn.completed.usage` 的累计量陷阱

2026-06-20 对 `codex exec resume --json` 做多轮实测时发现：恢复已有 session 后，stdout 最后一条 `turn.completed.usage` 不是本轮 LLM 调用的 token 用量，而是当前 session 的累计用量。

实测命令形态：

```powershell
codex exec resume --json 019ee34b-deea-73b0-8bc0-9911a1283bd0 "<prompt>"
```

stdout 最后一条：

```json
{"type":"turn.completed","usage":{"input_tokens":657268,"cached_input_tokens":574464,"output_tokens":4864,"reasoning_output_tokens":410}}
```

同一个 session JSONL 的最后一条 `token_count`：

```json
{
  "payload": {
    "type": "token_count",
    "info": {
      "total_token_usage": {
        "input_tokens": 657268,
        "cached_input_tokens": 574464,
        "output_tokens": 4864,
        "reasoning_output_tokens": 410
      },
      "last_token_usage": {
        "input_tokens": 81627,
        "cached_input_tokens": 80256,
        "output_tokens": 1026,
        "reasoning_output_tokens": 104
      },
      "model_context_window": 258400
    }
  }
}
```

对应关系：

```text
turn.completed.usage.input_tokens == token_count.info.total_token_usage.input_tokens
turn.completed.usage.cached_input_tokens == token_count.info.total_token_usage.cached_input_tokens
```

因此，恢复会话时不能把 `turn.completed.usage.input_tokens` 当作当前上下文窗口占用。上例中错误值是 `657K`，真实的最后一次 LLM 调用输入是 `81K`，且 `81K < model_context_window 258400`。

正确方案：

1. 新会话没有历史累计时，可以直接使用 `turn.completed.usage`。
2. resume 已有会话时，在启动 CLI 前读取 session JSONL 最后一条 `token_count.info.total_token_usage` 作为 baseline。
3. 收到 stdout 的 `turn.completed.usage` 后，对 token 字段做差分：

```text
last_input_tokens = current_usage.input_tokens - baseline.input_tokens
last_cached_input_tokens = current_usage.cached_input_tokens - baseline.cached_input_tokens
last_output_tokens = current_usage.output_tokens - baseline.output_tokens
last_reasoning_output_tokens = current_usage.reasoning_output_tokens - baseline.reasoning_output_tokens
```

4. 对外输出的 `AgentResult.usage.input_tokens` 应使用差分后的 `last_input_tokens`，这样 `input_tokens` 才表示本轮 LLM 调用的上下文窗口输入占用。

---

## 三、输出对比总结

### 3.1 输出特点对比

| 特性 | Claude 非流式 | Claude 流式 | Codex 非流式 | Codex 流式 |
|-----|-------------|-----------|------------|----------|
| **格式** | 纯文本 | JSON Lines | 格式化文本 | JSON Lines |
| **元数据** | ❌ | ✅ 丰富 | ✅ 基础 | ✅ 基础 |
| **思考过程** | ❌ | ❌ | ✅ | ❌ |
| **工具调用** | ❌ | ✅ | ✅ 详细 | ✅ |
| **Token 统计** | ❌ | ✅ 详细 | ✅ 总计 | ✅ 详细 |
| **实时性** | ❌ | ✅ | ❌ | ✅ |
| **易解析性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

### 3.2 使用场景建议

**Claude Code 非流式：**
- ✅ 快速查询、脚本集成
- ✅ 只需要最终答案
- ❌ 需要调试信息

**Claude Code 流式：**
- ✅ 实时监控执行过程
- ✅ 需要详细的元数据
- ✅ 构建交互式应用

**Codex 非流式：**
- ✅ 调试和审计
- ✅ 需要完整的工作日志
- ✅ 理解 Agent 决策过程

**Codex 流式：**
- ✅ 实时监控
- ✅ 事件驱动应用
- ✅ 需要结构化数据

---

## 四、Codex 非流式解析要点

### 4.1 需要提取的信息

如果要解析 Codex 非流式输出，需要提取以下信息：

1. **对话内容**
   - 识别 `user` 和 `codex` 角色标识
   - 提取每个角色的消息内容

2. **Agent 思考过程**
   - 提取工具调用前的 codex 消息
   - 这些消息说明了 Agent 的工作计划

3. **工具调用**
   - 识别 `exec` 标识
   - 提取命令字符串
   - 提取执行结果（succeeded/failed）
   - 提取执行时间（Xms）
   - 提取工具输出内容（`---` 后的内容）
   - 格式化为：`{tool_call: "命令", tool_call_result: "输出"}`

4. **Token 使用**
   - 识别 `tokens used` 标识
   - 提取下一行的数字（去除逗号）

5. **最终答案**
   - 提取最后一个 codex 消息的内容

### 4.2 解析难点

1. **状态跟踪**
   - 需要跟踪当前处于哪个区域（元数据、对话、工具、回复）
   - 通过关键字切换状态

2. **角色识别**
   - 单独一行的 `user` 或 `codex` 表示角色切换
   - 后续行直到下一个角色标识都属于当前角色

3. **工具调用边界**
   - `exec` 开始，下一个 `codex` 结束
   - 中间包含命令、结果、输出

4. **内容去重**
   - Codex 可能输出重复内容
   - 需要检测并合并重复的消息

---

## 五、核心发现

1. **思考过程部分可见**：Claude CLI 在使用 `--include-partial-messages` 时会输出 `thinking_delta` 事件，包含模型的思考过程增量内容；每轮回复以 `content_block_start`（type=`thinking`）开始，经过多个 `thinking_delta`，以 `signature_delta` 结束思考块。非流式模式（`-p`）不输出思考过程
2. **格式差异明显**：Claude 简洁，Codex 详细
3. **流式输出统一**：都使用 JSON Lines 格式，易于解析
4. **非流式差异大**：Claude 纯文本，Codex 结构化文本

---

## 六、统一管理可行性

✅ **完全可行**

通过设计统一的数据结构，可以：
- 屏蔽不同 CLI 的格式差异
- 提供一致的 API 访问输出数据
- 支持灵活的数据提取和转换

**建议的统一数据结构应包含：**
- 元数据（CLI 类型、模式、会话 ID、模型等）
- 对话内容（角色、消息）
- 思考过程（可选，仅 Codex 非流式）
- 工具调用（命令、结果、状态、耗时）
- Token 使用统计
- 最终答案

---

**报告完成时间：** 2026-05-23  
**测试数据来源：** `tests/explore/claude_codex_cli_output/outputs/`  
**相关文件：** `test-cli-output.ps1`, `compare-outputs.ps1`
