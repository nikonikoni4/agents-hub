---
labels: [ready-for-agent]
---

# Issue 7：端到端集成测试

## Parent

无

## What to build

进行完整的端到端集成测试，验证飞书 Channel 集成的正确性。

**测试内容**：
1. 完整流程测试：飞书发消息 → Agent 处理 → 回复到飞书
2. 命令系统测试：/help, /agents, /groups, /bind
3. 增量同步测试：重启后不重复发送历史消息
4. 断线重连测试：WebSocket 断开 → 自动重连

**测试场景**：

### 场景 1：完整流程
1. 飞书用户发送消息到飞书群
2. 飞书 Channel 接收消息
3. 转发到 agents-hub 群聊
4. Agent 处理消息
5. Agent 回复推送到飞书群

### 场景 2：命令系统
1. 飞书用户发送 `/help`
2. 飞书 Channel 返回帮助信息
3. 飞书用户发送 `/agents`
4. 飞书 Channel 返回 agent 列表
5. 飞书用户发送 `/bind my-team`
6. 飞书 Channel 绑定群聊

### 场景 3：增量同步
1. 飞书用户发送消息 A
2. Agent 回复消息 B
3. 重启飞书 Channel
4. 验证不会重复发送消息 A 和 B

### 场景 4：断线重连
1. 飞书 Channel 正常运行
2. 模拟网络断开
3. 验证自动重连
4. 验证消息正常接收

## Acceptance criteria

- [ ] 完整流程测试通过
- [ ] 命令系统测试通过
- [ ] 增量同步测试通过
- [ ] 断线重连测试通过
- [ ] 所有测试用例通过
- [ ] 测试覆盖率满足要求

## Blocked by

- Issue 1：广播机制扩展
- Issue 2：飞书 Channel 基础框架
- Issue 3：飞书消息接收与解析
- Issue 4：飞书消息发送与广播监听
- Issue 5：Session 映射与同步状态管理
- Issue 6：命令系统集成

## 相关文件

- `tests/integration/test_feishu_channel.py`

## 参考文档

- [架构约束文件](../architecture.md)
- [Checklist](../checklist.md)
- `tests/integration/test_wechat_channel.py` - 微信 Channel 测试参考
