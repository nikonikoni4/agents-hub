#!/usr/bin/env python3
"""
Loop 组件截图脚本

使用 Playwright 截图 LoopStatusPanel 和 LoopDetailModal 组件。
使用 mock 模式启动前端，不需要真实后端数据。

使用方法：
    python frontend/tests/e2e/loop_screenshot.py

输出位置：
    frontend/tests/e2e/screenshots/
"""

import subprocess
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """主函数：启动前端并截图 Loop 组件"""

    # 截图输出目录
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Loop 组件截图脚本")
    print("=" * 60)

    # 启动前端服务（mock 模式）
    print("\n1. 启动前端服务（mock 模式）...")

    # 设置环境变量
    env = os.environ.copy()
    env["VITE_USE_MOCK"] = "true"

    # 启动前端开发服务器
    frontend_dir = project_root / "frontend"
    server_process = subprocess.Popen(
        ["pnpm", "dev"],
        cwd=frontend_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )

    # 等待服务器启动
    print("等待前端服务启动...")
    import time
    import socket

    def is_server_ready(port, timeout=30):
        """检查服务器是否就绪"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection(("localhost", port), timeout=1):
                    return True
            except (socket.error, ConnectionRefusedError):
                time.sleep(0.5)
        return False

    if not is_server_ready(5173, timeout=30):
        print("错误：前端服务启动超时")
        server_process.terminate()
        sys.exit(1)

    print("前端服务已启动")

    # 运行 Playwright 截图
    print("\n2. 运行 Playwright 截图...")

    try:
        # 导入 Playwright
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})

            # 导航到首页
            print("导航到首页...")
            page.goto("http://localhost:5173")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)  # 等待数据加载

            # 选择一个群聊（点击第一个群聊）
            print("选择一个群聊...")
            # 查找session-groups中的第一个可点击元素
            session_groups = page.locator('.session-groups').first
            if session_groups.is_visible():
                # 点击第一个群聊项
                first_chat = session_groups.locator('div').first
                if first_chat.is_visible():
                    first_chat.click()
                    page.wait_for_timeout(3000)  # 等待群聊加载
                    print("已选择群聊")

                    # 检查是否成功选择了群聊
                    chat_area = page.locator('[class*="chatArea"]').first
                    if chat_area.is_visible():
                        chat_text = chat_area.text_content()
                        if "选择一个群聊开始对话" in chat_text:
                            print("警告：未成功选择群聊，尝试点击其他元素...")
                            # 尝试点击其他可能的群聊元素
                            session_items = page.locator('[class*="session-item"]').all()
                            if session_items:
                                session_items[0].click()
                                page.wait_for_timeout(2000)
                                print("已点击第一个session-item")
                        else:
                            print("已成功选择群聊")
                    else:
                        print("警告：未找到聊天区域")
                else:
                    print("警告：未找到群聊项")
            else:
                print("警告：未找到群聊列表")

            # 截图 1: LoopStatusPanel 缩略图
            print("\n截图 1: LoopStatusPanel 缩略图")

            # 查找 LoopStatusPanel
            loop_panel = page.locator('[class*="loopPanel"]').first
            if loop_panel.is_visible():
                # 截图整个 LoopStatusPanel
                loop_panel.screenshot(
                    path=str(screenshot_dir / "loop_status_panel.png")
                )
                print(f"  已保存: {screenshot_dir / 'loop_status_panel.png'}")
            else:
                print("  警告：未找到 LoopStatusPanel，尝试全页面截图...")
                page.screenshot(
                    path=str(screenshot_dir / "loop_status_panel_full.png"),
                    full_page=True
                )
                print(f"  已保存: {screenshot_dir / 'loop_status_panel_full.png'}")

            # 截图 2: LoopDetailModal 扩展图
            print("\n截图 2: LoopDetailModal 扩展图")

            # 点击 LoopStatusPanel 打开详情模态框
            loop_node_list = page.locator('[class*="loopNodeList"]').first
            if loop_node_list.is_visible():
                loop_node_list.click()
                page.wait_for_timeout(500)  # 等待模态框动画

                # 截图模态框
                modal = page.locator('[class*="modal"]').first
                if modal.is_visible():
                    modal.screenshot(
                        path=str(screenshot_dir / "loop_detail_modal.png")
                    )
                    print(f"  已保存: {screenshot_dir / 'loop_detail_modal.png'}")
                else:
                    print("  警告：未找到模态框，尝试全页面截图...")
                    page.screenshot(
                        path=str(screenshot_dir / "loop_detail_modal_full.png"),
                        full_page=True
                    )
                    print(f"  已保存: {screenshot_dir / 'loop_detail_modal_full.png'}")
            else:
                print("  警告：未找到节点列表，跳过模态框截图")

            # 关闭浏览器
            browser.close()

    except ImportError:
        print("错误：未安装 Playwright")
        print("请运行: pip install playwright && playwright install chromium")
        sys.exit(1)
    except Exception as e:
        print(f"错误：截图失败 - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 停止前端服务
        print("\n3. 停止前端服务...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("前端服务已停止")

    print("\n" + "=" * 60)
    print("截图完成！")
    print("=" * 60)
    print(f"\n截图文件位置: {screenshot_dir}")
    print("\n文件列表:")
    for file in screenshot_dir.glob("*.png"):
        print(f"  - {file.name}")


if __name__ == "__main__":
    main()
