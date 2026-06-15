"""
调试截图2：查看页面元素结构
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

    # 查找所有可点击的元素
    print("=== 查找群聊相关元素 ===")

    # 查找包含 task-33 的元素
    task_elements = page.locator("text=task-33").all()
    print(f"找到 {len(task_elements)} 个包含 'task-33' 的元素:")
    for i, elem in enumerate(task_elements):
        tag = elem.evaluate("el => el.tagName")
        class_name = elem.get_attribute("class") or "无class"
        print(f"  {i+1}. tag={tag}, class={class_name}")

    # 查找 session-tab 元素
    session_tabs = page.locator(".session-tab").all()
    print(f"\n找到 {len(session_tabs)} 个 session-tab 元素:")
    for i, tab in enumerate(session_tabs):
        text = tab.inner_text()
        class_name = tab.get_attribute("class") or "无class"
        print(f"  {i+1}. text='{text}', class={class_name}")

    # 尝试点击 session-tab
    if len(session_tabs) > 0:
        print("\n尝试点击第一个 session-tab...")
        session_tabs[0].click()
        page.wait_for_timeout(2000)

        # 检查是否出现输入框
        textarea = page.locator('textarea')
        print(f"点击后找到 {textarea.count()} 个 textarea")

        # 截图
        page.screenshot(path=f"{OUTPUT_DIR}/debug_after_click_session_tab.png", full_page=True)

    browser.close()
