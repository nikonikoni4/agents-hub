"""微信 Channel 独立启动脚本（第一阶段：自动回复）"""

import asyncio
import logging
import signal

from agents_hub.channels.wechat import WechatChannel, WechatConfig
from agents_hub.config.config import config


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    wechat_config = WechatConfig(allow_from=["*"])
    channel = WechatChannel(wechat_config, data_path=config.data_path)

    async def run():
        await channel.start()
        if not channel._running:
            print("微信 channel 启动失败")
            return

        print("微信 channel 已启动，等待消息...")
        print("按 Ctrl+C 退出")

        stop_event = asyncio.Event()

        def _signal_handler():
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                pass

        await stop_event.wait()
        await channel.stop()

    asyncio.run(run())


if __name__ == "__main__":
    main()
