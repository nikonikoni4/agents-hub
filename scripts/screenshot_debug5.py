"""
调试截图5：展开群聊列表
"""

from playwright.sync_api import sync_playwright

OUTPUT_DIR = "screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})

    # 导航到应用
    page.goto("http://localhost:5173")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # 查找 project-header 并点击展开
    print("=== 查找 project-header ===")
    project_header = page.locator(".project-header")
    if project_header.count() > 0:
        print(f"找到 {project_header.count()} 个 project-header")
        project_header.first.click()
        page.wait_for_timeout(1000)

        # 截图查看展开后的状态
        page.screenshot(path=f"{OUTPUT_DIR}/debug_after_expand.png", full_page=True)
        print("已截图展开后的状态")

        # 查找群聊列表项
        session_items = page.locator("[class*='session-item'], [class*='chat-item'], [class*='group-item']").all()
        print(f"找到 {len(session_items)} 个群聊列表项")

        # 查找所有可点击的元素
        clickable = page.locator("div[class*='session'], div[class*='chat'], div[class*='group']").all()
        print(f"找到 {len(clickable)} 个 session/chat/group 元素")

        # 尝试点击第一个群聊列表项
        if len(session_items) > 0:
            print("\n尝试点击第一个群聊列表项...")
            session_items[0].click()
            page.wait_for_timeout(2000)

            # 检查是否出现输入框
            textarea = page.locator('textarea')
            print(f"点击后找到 {textarea.count()} 个 textarea")

            # 截图
            page.screenshot(path=f"{OUTPUT_DIR}/debug_after_click_session.png", full_page=True)

    browser.close()
