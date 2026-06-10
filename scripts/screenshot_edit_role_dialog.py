"""截图"编辑角色"弹窗界面。

用法（前端服务已运行时）:
    python scripts/screenshot_edit_role_dialog.py

用法（自动启动前端服务）:
    python skills/webapp-testing/scripts/with_server.py \
        --server "cd frontend && npm run dev" --port 5173 \
        -- python scripts/screenshot_edit_role_dialog.py

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

        # 2. 点击左侧边栏的"角色管理"按钮进入角色管理界面
        role_btn = page.locator('button[aria-label="角色管理"]')
        if role_btn.count() == 0:
            print("错误: 未找到'角色管理'按钮")
            browser.close()
            return

        role_btn.first.click()
        page.wait_for_timeout(1500)
        print("已点击'角色管理'按钮")

        # 3. 切换到"角色管理" tab（第二个"角色管理"按钮是 tab）
        role_tabs = page.locator('button').filter(has_text='角色管理')
        if role_tabs.count() >= 2:
            role_tabs.nth(1).click()
            page.wait_for_timeout(1000)
            print("已切换到'角色管理' tab")

        # 4. 点击第一个"编辑角色"按钮
        edit_btn = page.locator('button[aria-label="编辑角色"]')
        print(f"找到 {edit_btn.count()} 个'编辑角色'按钮")

        if edit_btn.count() == 0:
            print("错误: 未找到'编辑角色'按钮")
            browser.close()
            return

        edit_btn.first.click()
        page.wait_for_timeout(1500)
        print("已点击'编辑角色'按钮")

        # 5. 定位弹窗容器 - 使用 class* 匹配 CSS 模块类名
        dialog = page.locator('div[class*="_dialog_"]')
        print(f"找到 {dialog.count()} 个弹窗容器")

        # 6. 截取编辑角色弹窗
        if dialog.count() > 0:
            dialog.first.screenshot(path=str(SCREENSHOT_DIR / "edit_role_dialog.png"))
            print("已截取编辑角色弹窗: screenshots/edit_role_dialog.png")
        else:
            page.screenshot(path=str(SCREENSHOT_DIR / "edit_role_dialog.png"))
            print("警告: 未能精确定位弹窗，已截取全页面")

        browser.close()
        print("截图完成！")


if __name__ == "__main__":
    main()
