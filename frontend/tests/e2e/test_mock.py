#!/usr/bin/env python3
"""
Mock 数据测试脚本

测试前端是否正确使用 mock 数据。

使用方法：
    python frontend/tests/e2e/test_mock.py
"""

import subprocess
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """主函数：测试 mock 数据"""

    print("=" * 60)
    print("Mock 数据测试脚本")
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

    # 运行 Playwright 测试
    print("\n2. 运行 Playwright 测试...")

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

            # 检查页面标题
            print(f"\n页面标题: {page.title()}")

            # 检查是否显示 "暂无Loop定义"
            loop_empty = page.locator('text=暂无Loop定义').first
            if loop_empty.is_visible():
                print("✓ 显示 '暂无Loop定义'（mock 数据未加载）")
            else:
                print("✗ 未显示 '暂无Loop定义'（mock 数据可能已加载）")

            # 检查 Loop 组件
            loop_panel = page.locator('[class*="loopPanel"]').first
            if loop_panel.is_visible():
                print("✓ Loop 组件可见")

                # 获取 Loop 组件的文本内容
                loop_text = loop_panel.text_content()
                print(f"Loop 组件内容: {loop_text[:100]}...")
            else:
                print("✗ Loop 组件不可见")

            # 检查是否有节点列表
            node_list = page.locator('[class*="loopNodeList"]').first
            if node_list.is_visible():
                print("✓ 节点列表可见")
            else:
                print("✗ 节点列表不可见")

            # 截图当前页面
            print("\n截图当前页面...")
            page.screenshot(
                path=str(Path(__file__).parent / "screenshots" / "mock_test.png"),
                full_page=True
            )
            print(f"已保存: {Path(__file__).parent / 'screenshots' / 'mock_test.png'}")

            # 关闭浏览器
            browser.close()

    except ImportError:
        print("错误：未安装 Playwright")
        print("请运行: pip install playwright && playwright install chromium")
        sys.exit(1)
    except Exception as e:
        print(f"错误：测试失败 - {e}")
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
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
