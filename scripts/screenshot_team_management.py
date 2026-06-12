"""截图"团队管理"界面。

截取角色管理界面中的团队管理部分，包括：
1. 整体布局
2. 团队列表
3. 团队成员面板

用法（前端服务已运行时）:
    python scripts/screenshot_team_management.py

用法（自动启动前端服务）:
    python skills/webapp-testing/scripts/with_server.py \
        --server "cd frontend && npm run dev" --port 5173 \
        -- python scripts/screenshot_team_management.py

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

        # 2. 点击"角色管理"按钮
        role_btn = page.locator('button[aria-label="角色管理"]')
        if role_btn.count() == 0:
            print("错误: 未找到'角色管理'按钮")
            browser.close()
            return

        role_btn.first.click()
        page.wait_for_timeout(1500)
        print("已点击'角色管理'按钮")

        # 3. 确保在"团队管理" tab（默认应该是）
        teams_tab = page.locator('button:has-text("团队管理")')
        if teams_tab.count() > 0:
            teams_tab.first.click()
            page.wait_for_timeout(1000)
            print("已切换到'团队管理' tab")

        # 4. 截取团队管理整体布局
        # 使用 class* 匹配 CSS 模块类名
        teams_view = page.locator('div[class*="_teamsView_"]')
        print(f"找到 {teams_view.count()} 个团队视图容器")

        if teams_view.count() > 0:
            teams_view.first.screenshot(path=str(SCREENSHOT_DIR / "team_management_overview.png"))
            print("已截取团队管理整体布局: screenshots/team_management_overview.png")
        else:
            page.screenshot(path=str(SCREENSHOT_DIR / "team_management_overview.png"))
            print("警告: 未能精确定位团队视图，已截取全页面")

        # 5. 截取团队卡片
        team_cards = page.locator('div[class*="_card_"]')
        print(f"找到 {team_cards.count()} 个团队卡片")

        if team_cards.count() > 0:
            # 截取第一个团队卡片
            team_cards.first.screenshot(path=str(SCREENSHOT_DIR / "team_card.png"))
            print("已截取第一个团队卡片: screenshots/team_card.png")

            # 如果有多个团队，截取第二个
            if team_cards.count() > 1:
                team_cards.nth(1).screenshot(path=str(SCREENSHOT_DIR / "team_card_second.png"))
                print("已截取第二个团队卡片: screenshots/team_card_second.png")

        # 6. 截取团队成员面板（如果有的话）
        member_panels = page.locator('div[class*="_memberGrid_"]')
        print(f"找到 {member_panels.count()} 个成员面板")

        if member_panels.count() > 0:
            member_panels.first.screenshot(path=str(SCREENSHOT_DIR / "team_member_panel.png"))
            print("已截取第一个团队成员面板: screenshots/team_member_panel.png")

        browser.close()
        print("截图完成！")


if __name__ == "__main__":
    main()
