## CI 检查 001
 - updated_at : 2026-06-06
 - path: generated/001/
 - 触发规则：ci-check 技能首次测试运行
 - 内容摘要：代码审查 + 文档一致性检查（ARCHITECTURE.md / specs / CONTEXT.md），含 `--tools` 格式问题导致 code-review 缺少 Bash 工具

## CI 检查 002
 - updated_at : 2026-06-06
 - path: generated/002/
 - 触发规则：Specs 联合调整修复验证
 - 内容摘要：验证 Phase 1-4 修复效果，包括 3 个 spec 修复确认、5 个新建 spec 代码对齐验证、ARCHITECTURE.md 瘦身验证（723→285 行）、索引完整性检查

## 单聊通道代码审查 003
 - updated_at : 2026-06-08
 - path: generated/003/
 - 触发规则：code-review 技能审查 task-12-single-chat 分支
 - 内容摘要：审查 `377110d..d7cb214`（9 commits），发现 3 个高置信度问题：`_resolve_session_path` 硬编码路径忽略 RoleConfig.work_root、`except Exception` 违反 backend-style.md、`parse_codex_session` 未校验 role 类型；7 个中置信度问题（未使用异常、私有属性访问、SSE 格式化位置等）

## CI 检查 004
 - updated_at : 2026-06-10
 - path: generated/004/
 - 触发规则：ci-check 技能触发的提交前检查
 - 内容摘要：代码审查 + 文档一致性检查（ARCHITECTURE.md / specs / CONTEXT.md）

## 严重的AI自主设计错误
 - updated_at : 2026-06-10
 - path: generated/004/
 - 触发规则：手动审查
 - 内容摘要：在file upload的过程中，首先给出了完整的spec，但是ai后续给出的plan只plan了一半。多次发现spec和plan无法对齐。中间缺少审查

## CI 检查 010
 - updated_at : 2026-06-10
 - path: generated/010/
 - 触发规则：ci-check 技能触发的提交前检查
 - 内容摘要：代码审查 + 文档一致性检查（ARCHITECTURE.md / specs / CONTEXT.md）

## CI 检查 006
 - updated_at : 2026-06-10
 - path: generated/006/
 - 触发规则：ci-check 技能触发的提交前检查
 - 内容摘要：代码审查 + 文档一致性检查（ARCHITECTURE.md / specs / CONTEXT.md）

## 核心模块架构审查 007
 - updated_at : 2026-06-14
 - path: generated/007/
 - 触发规则：GroupChatContext → GroupChatRuntime 重构期间的架构审查
 - 内容摘要：6 份审查报告 — Agent 状态生命周期、Agent 生命周期、GroupChat 生命周期、AgentCall 生命周期、并发安全性、GroupChatContext/Runtime 架构评估

## Parser 隔离修复代码审查 008
 - updated_at : 2026-06-16
 - path: generated/008/
 - 触发规则：bridge.py parser 单例改为每次创建的代码审查
 - 内容摘要：8 维度并行审查（安全/性能/架构/质量/最佳实践/测试/文档/注释），无高置信度问题（>=80），2 个低置信度发现（缺少 unsupported platform 边界测试 75 分、冗余注释 50 分）

## Loop 重构文件清单审查 021
 - updated_at : 2026-06-21
 - path: generated/021/
 - 触发规则：local-code-review 审查 docs/temp/loop-refactor-file-list.md
 - 内容摘要：文档准确性+完整性+结构质量审查，发现 3 个高置信度问题（>=80）：Phase 5 测试 checklist 严重过时（100）、废弃工具未记录（85）、group_chat.py 文档字符串遗留旧字段名 node_prompt（80）

## Loop 懒加载机制代码审查 020
 - updated_at : 2026-06-21
 - path: generated/020/
 - 触发规则：LoopManager 懒加载、单 Loop 保持、list_loops 重构的代码审查
 - 内容摘要：8 维度并行审查，发现 8 个高置信度问题（>=80）：GroupChat 直接访问 _loops 私有属性（95）、JSONL 读取逻辑重复 3 次（95）、Spec/Flow 文档未同步（95）、内存命中路径未测试（90）、MCP 模块 docstring 过时（90）、墓碑排除未测试（85）、类型注解不完整（85）、损坏行静默忽略缺少日志（85）

## 首响事件（FIRST_RESPONSE）代码审查 023
 - updated_at : 2026-06-24
 - path: generated/023/
 - 触发规则：local-code-review 审查 3a631cc - feat: 实现 execute_with_first_response() 方法支持群聊首响
 - 内容摘要：8 维度并行审查，发现 8 个高置信度问题（>=90）：execute_with_first_response() 违反"LLM 输出默认不进入群聊历史"原则（Architecture 90）、Claude/Codex parser 和 execute_with_first_response 缺少单元测试（Testing 90x3）、核心业务逻辑 add_message 无集成测试（Testing 90）、agent-bridge spec 事件类型表缺少 FIRST_RESPONSE（Documentation 90）、core-agent-orchestration spec key_function 和接口表缺少新方法（Documentation 90x2）

## 首响逻辑重构代码审查 024
 - updated_at : 2026-06-24
 - path: generated/024/
 - 触发规则：local-code-review 审查 7e05336 - refactor: 将首响检测逻辑从 agent 层移到 agent_bridge 层
 - 内容摘要：8 维度并行审查，发现 12 个高置信度问题（>=80）：2 个致命缺陷（AgentEventType.FIRST_RESPONSE 枚举未定义 100、Parser 不产出事件导致死代码 100）、架构违规（Agent 直接写群聊历史绕过 report_progress 90、AgentBridge 引入业务语义违反 spec 90）、测试缺失（新方法和数据类型零测试 90x3）、文档未同步（spec 事件表/接口表/key_function 缺失 90x3）、注释与代码不符（Docker 回退条件描述错误 85x2、回退逻辑注释不一致 85）、spec 描述过时（与 agent_bridge 协作章节 85）

## 首响功能完整实现代码审查 025（重新审查）
 - updated_at : 2026-06-24
 - path: generated/025/
 - 触发规则：local-code-review 重新审查 3a631cc + 7e05336 合并效果
 - 内容摘要：确认两个致命缺陷已修复（FIRST_RESPONSE 枚举已定义、Parser 已实现事件生成）。剩余 10 个高置信度问题（>=80）：架构违规（Agent 直接写群聊历史绕过 report_progress 90、AgentBridge 引入业务语义违反 spec 90）、测试缺失（新方法和数据类型零测试 90x2）、文档未同步（spec 事件表/接口表/key_function 缺失 90）、注释与代码不符（Docker 回退条件描述错误 85x2）、代码质量（DRY 违反 80、字符串拼接效率 80）

## 首响功能测试和文档补充代码审查 026（修复验证）
 - updated_at : 2026-06-24
 - path: generated/026/
 - 触发规则：local-code-review 审查 d9c86f3 - feat: 添加首响功能测试和文档，修复代码质量问题
 - 内容摘要：验证之前审查问题修复情况。已修复 6 个问题：文档同步（spec 事件表/接口表/key_function 已更新）、测试覆盖（新增 5 个测试场景）、代码质量（DRY 违反已修复、字符串拼接已优化）。剩余 3 个问题：2 个架构设计决策问题（Agent 直接写群聊历史绕过 report_progress 90、AgentBridge 引入业务语义违反 spec 90，需团队讨论）、1 个注释准确性问题（docstring 与代码不符 85）

## 私聊功能文档完整性审查 027
 - updated_at : 2026-06-25
 - path: generated/027/
 - 触发规则：local-code-review 审查 a1fdd19 - feat(private-chat): 新增私聊状态定义和 API 端点
 - 内容摘要：文档完整性专项审查，发现 3 个高置信度问题（>=85）：缺少正式 spec 文档（95）、API 文档未更新（90）、状态枚举文档未更新（85）。代码注释充分，符合规范。建议创建正式 spec 文档并更新相关文档

## 私聊功能代码质量审查 028
 - updated_at : 2026-06-25
 - path: generated/028/
 - 触发规则：local-code-review 审查 a1fdd19..HEAD（5 个提交，14 个文件，420 行新增）
 - 内容摘要：8 维度并行审查，发现 8 个高置信度问题（>=80）：组件直接调用 API 违反分层架构（95）、缺少测试覆盖（90）、直接操作 store state（85）、重复的状态检查代码（85）、缺少更新 Spec 文档（85）、嵌套三元表达式（80）、重复的状态映射逻辑（80）、注释与代码不符（80）

## 飞书重构代码审查 031
 - updated_at : 2026-06-27
 - path: generated/031/
 - 触发规则：local-code-review 审查 HEAD~1..HEAD（飞书重构提交，14 文件，+2125/-229）
 - 内容摘要：8 维度并行审查，发现 8 个高置信度问题（>=80）：prompt injection 可伪造 feishu_chat_id（90）、6 个 MCP 工具无鉴权绕过 ADR-0007（95）、list_group_chats N+1 查询（90）、bind_to_single_chat 缺少 exc_info（90）、缺少错误路径测试（90）、mock side_effect 逻辑缺陷（88）、spec 行号系统性偏移（95）、spec 异常类型不符（95）。核心风险：Issue 1+2 组合构成跨租户会话操控攻击面