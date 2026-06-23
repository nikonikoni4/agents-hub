#!/usr/bin/env python3
"""
页面结构探查脚本

使用 Playwright 查看页面 DOM 结构，帮助定位元素选择器。

使用方法：
    python frontend/tests/e2e/inspect_page.py
"""

import subprocess
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """主函数：探查页面结构"""

    print("=" * 60)
    print("页面结构探查脚本")
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

    # 运行 Playwright 探查
    print("\n2. 运行 Playwright 探查...")

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
            page.wait_for_timeout(2000)  # 等待数据加载

            # 探查页面结构
            print("\n=== 页面标题 ===")
            print(page.title())

            print("\n=== 按钮列表 ===")
            buttons = page.locator('button').all()
            for i, btn in enumerate(buttons[:10]):  # 只显示前10个
                text = btn.text_content()
                print(f"  [{i}] {text}")

            print("\n=== 链接列表 ===")
            links = page.locator('a').all()
            for i, link in enumerate(links[:10]):  # 只显示前10个
                text = link.text_content()
                href = link.get_attribute('href')
                print(f"  [{i}] {text} -> {href}")

            print("\n=== 输入框列表 ===")
            inputs = page.locator('input').all()
            for i, inp in enumerate(inputs[:10]):  # 只显示前10个
                placeholder = inp.get_attribute('placeholder')
                input_type = inp.get_attribute('type')
                print(f"  [{i}] type={input_type}, placeholder={placeholder}")

            print("\n=== 包含 'session' 或 'chat' 的元素 ===")
            session_elements = page.locator('[class*="session"], [class*="chat"]').all()
            for i, elem in enumerate(session_elements[:10]):  # 只显示前10个
                class_name = elem.get_attribute('class')
                text = elem.text_content()[:50] if elem.text_content() else ""
                print(f"  [{i}] class={class_name}, text={text}")

            print("\n=== 包含 'loop' 的元素 ===")
            loop_elements = page.locator('[class*="loop"]').all()
            for i, elem in enumerate(loop_elements[:10]):  # 只显示前10个
                class_name = elem.get_attribute('class')
                text = elem.text_content()[:50] if elem.text_content() else ""
                print(f"  [{i}] class={class_name}, text={text}")

            # 截图当前页面
            print("\n截图当前页面...")
            page.screenshot(
                path=str(Path(__file__).parent / "screenshots" / "page_structure.png"),
                full_page=True
            )
            print(f"已保存: {Path(__file__).parent / 'screenshots' / 'page_structure.png'}")

            # 关闭浏览器
            browser.close()

    except ImportError:
        print("错误：未安装 Playwright")
        print("请运行: pip install playwright && playwright install chromium")
        sys.exit(1)
    except Exception as e:
        print(f"错误：探查失败 - {e}")
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
    print("探查完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
