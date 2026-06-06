"""截图前端主界面。

用法（前端服务已运行时）:
    python scripts/screenshot_main.py

用法（自动启动前端服务）:
    python skills/webapp-testing/scripts/with_server.py \
        --server "cd frontend && npm run dev" --port 5173 \
        -- python scripts/screenshot_main.py

截图保存到 screenshots/ 目录下。
"""

from playwright.sync_api import sync_playwright
from pathlib import Path

SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "screenshots"
URL = "http://localhost:5173"


def screenshot(page, name):
    page.wait_for_timeout(1000)
    path = SCREENSHOT_DIR / name
    page.screenshot(path=str(path), full_page=True)
    print(f"截图已保存: {path}")


def main():
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 1. 主界面（会话页）- 点击"测试"会话加载消息
        page.goto(URL, wait_until="networkidle")
        page.locator('.session-item').first.click()
        page.wait_for_load_state('networkidle')
        screenshot(page, "main.png")

        # # 2. 技能广场
        page.locator('button[aria-label="技能广场"]').click()
        screenshot(page, "skill_square.png")

        # # 3. 角色管理 - 团队管理（默认 tab）
        page.locator('button[aria-label="角色管理"]').click()
        screenshot(page, "role_management_teams.png")

        # # 4. 角色管理 - 角色面板
        page.locator('text=角色管理').last.click()
        screenshot(page, "role_management_roles.png")

        browser.close()


if __name__ == "__main__":
    main()
