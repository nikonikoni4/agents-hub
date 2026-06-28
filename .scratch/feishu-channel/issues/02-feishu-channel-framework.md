---
labels: [ready-for-agent]
---

# Issue 2：飞书 Channel 基础框架

## Parent

无

## What to build

创建飞书 Channel 模块的基础结构，包括配置模型、异常定义和 lark-oapi SDK 封装。这是飞书 Channel 的骨架，后续所有功能都基于此框架。

**创建内容**：
1. `agents_hub/channels/feishu/__init__.py` - 模块导出
2. `agents_hub/channels/feishu/config.py` - FeishuConfig 配置模型
3. `agents_hub/channels/feishu/exceptions.py` - 异常定义
4. `agents_hub/channels/feishu/client.py` - lark-oapi SDK 封装

**配置模型**：
```python
@dataclass
class FeishuConfig:
    app_id: str                  # 飞书开放平台应用 ID
    app_secret: str              # 飞书开放平台应用 Secret
    encrypt_key: str = ""        # 事件加密密钥（可选）
    verification_token: str = "" # 验证 token（可选）
    group_policy: str = "mention"  # "open" / "mention"
    domain: str = "feishu"       # "feishu" / "lark"
```

## Acceptance criteria

- [ ] 目录结构创建完成
- [ ] `FeishuConfig` 配置模型定义
- [ ] 异常类定义（继承 `AgentsHubError`）
- [ ] `FeishuClient` 基础封装（连接、断开、发送消息）
- [ ] lark-oapi SDK 线程安全处理（使用 `asyncio.run_coroutine_threadsafe()` 桥接）
- [ ] 单元测试通过

## Blocked by

None - 可以立即开始

## 相关文件

- `agents_hub/channels/wechat/` - 微信 Channel 参考实现

## 参考文档

- [架构约束文件](../architecture.md)
- [Checklist](../checklist.md)
- nanobot 飞书实现：`D:\desktop\软件开发\nanobot\nanobot\channels\feishu.py`
