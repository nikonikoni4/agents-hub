"""测试飞书消息发送功能

使用方法：
    python scripts/test_feishu_send.py <chat_id> [message]

示例：
    python scripts/test_feishu_send.py oc_xxx "Hello from test"
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents_hub.channels.feishu.client import FeishuClient
from agents_hub.channels.feishu.config import FeishuConfig
from agents_hub.config.config import config


async def test_send(chat_id: str, message: str = "Hello from agents-hub test!"):
    """测试发送消息到飞书群"""
    print(f"=" * 50)
    print(f"飞书消息发送测试")
    print(f"=" * 50)

    # 1. 加载配置
    feishu_data = config.feishu_config
    app_id = feishu_data.get("app_id", "")
    app_secret = feishu_data.get("app_secret", "")

    print(f"\n[1] 配置信息:")
    print(f"    app_id: {app_id[:10]}..." if app_id else "    app_id: 未配置")
    print(f"    app_secret: {'***' if app_secret else '未配置'}")

    if not app_id or not app_secret:
        print("\n❌ 错误: 飞书配置不完整，请检查 config.yaml")
        return

    # 2. 创建客户端
    print(f"\n[2] 创建飞书客户端...")
    feishu_config = FeishuConfig.from_system_config(config.system)
    client = FeishuClient(feishu_config)

    # 3. 连接
    print(f"\n[3] 连接飞书 API...")
    try:
        await client.connect()
        print(f"    ✅ 连接成功")
    except Exception as e:
        print(f"    ❌ 连接失败: {e}")
        return

    # 4. 发送消息
    print(f"\n[4] 发送消息:")
    print(f"    目标 chat_id: {chat_id}")
    print(f"    消息内容: {message}")

    try:
        result = await client.send_message(chat_id, message)
        print(f"    ✅ 发送成功!")
        print(f"    message_id: {result.get('message_id', 'N/A')}")
    except Exception as e:
        print(f"    ❌ 发送失败: {e}")
        import traceback
        traceback.print_exc()

    # 5. 断开连接
    print(f"\n[5] 断开连接...")
    await client.disconnect()
    print(f"    ✅ 已断开")

    print(f"\n{'=' * 50}")
    print(f"测试完成")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/test_feishu_send.py <chat_id> [message]")
        print("示例: python scripts/test_feishu_send.py oc_xxx 'Hello'")
        sys.exit(1)

    chat_id = sys.argv[1]
    message = sys.argv[2] if len(sys.argv) > 2 else "Hello from agents-hub test!"

    asyncio.run(test_send(chat_id, message))
