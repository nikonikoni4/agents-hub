"""截图"新建对话"弹窗界面。

分别截取群聊（默认）和单聊两种模式的对话框内容。

用法（前端服务已运行时）:
    python scripts/screenshot_create_dialog.py

用法（自动启动前端服务）:
    python skills/webapp-testing/scripts/with_server.py \
        --server "cd frontend && npm run dev" --port 5173 \
        -- python scripts/screenshot_create_dialog.py

截图保存到 screenshots/ 目录下。
"""

from playwright.sync_api import sync_playwright
from pathlib import Path

SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "screenshots"
URL = "http://localhost:5173"


def main():
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 1. 打开主界面
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(2000)
        print("已打开主界面")

        # 2. 点击"新建对话"按钮
        create_btn = page.locator('button[aria-label="新建对话"]')
        if create_btn.count() == 0:
            print("错误: 未找到'新建对话'按钮")
            browser.close()
            return

        create_btn.first.click()
        page.wait_for_timeout(1500)
        print("已点击'新建对话'按钮")

        # 3. 定位弹窗容器 - 使用 class* 匹配 CSS 模块类名
        dialog = page.locator('div[class*="_dialog_"]')
        print(f"找到 {dialog.count()} 个弹窗容器")

        # 4. 截取群聊模式对话框（默认模式）
        if dialog.count() > 0:
            dialog.first.screenshot(path=str(SCREENSHOT_DIR / "create_dialog_group.png"))
            print("已截取群聊模式: screenshots/create_dialog_group.png")
        else:
            page.screenshot(path=str(SCREENSHOT_DIR / "create_dialog_group.png"))
            print("警告: 未能精确定位弹窗，已截取全页面")

        # 5. 切换到单聊模式
        # 在弹窗容器内查找"单聊"按钮
        if dialog.count() > 0:
            single_btn = dialog.first.locator('button:has-text("单聊")')
            print(f"弹窗内找到 {single_btn.count()} 个'单聊'按钮")

            if single_btn.count() > 0:
                single_btn.first.click()
                page.wait_for_timeout(1000)
                print("已点击弹窗内的'单聊'按钮")
            else:
                print("未在弹窗内找到'单聊'按钮，尝试其他选择器...")
                # 备选：查找包含 UserIcon 的按钮（单聊按钮有 UserIcon）
                mode_btns = dialog.first.locator('button[class*="modeBtn"]')
                if mode_btns.count() >= 2:
                    mode_btns.first.click()  # 第一个模式按钮是"单聊"
                    page.wait_for_timeout(1000)
                    print("已点击第一个模式按钮")

        # 6. 重新定位弹窗并截取单聊模式
        dialog = page.locator('div[class*="_dialog_"]')
        if dialog.count() > 0:
            dialog.first.screenshot(path=str(SCREENSHOT_DIR / "create_dialog_single.png"))
            print("已截取单聊模式: screenshots/create_dialog_single.png")
        else:
            page.screenshot(path=str(SCREENSHOT_DIR / "create_dialog_single.png"))
            print("警告: 未能精确定位弹窗，已截取全页面")

        browser.close()
        print("截图完成！")


if __name__ == "__main__":
    main()
