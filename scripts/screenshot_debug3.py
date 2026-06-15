"""
调试截图3：查找群聊列表项
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

    # 查找左侧栏
    print("=== 查找左侧栏元素 ===")

    # 查找所有列表项
    list_items = page.locator("li").all()
    print(f"找到 {len(list_items)} 个 li 元素")

    # 查找包含数字的元素（可能是未读数）
    badge_elements = page.locator("[class*='badge'], [class*='count'], [class*='unread']").all()
    print(f"找到 {len(badge_elements)} 个 badge/count/unread 元素")

    # 查找项目名称
    project_names = page.locator(".project-name").all()
    print(f"找到 {len(project_names)} 个 project-name 元素:")
    for i, name in enumerate(project_names):
        text = name.inner_text()
        parent = name.locator("..")
        parent_class = parent.get_attribute("class") or "无class"
        print(f"  {i+1}. text='{text}', parent_class={parent_class}")

    # 尝试点击项目名称
    if len(project_names) > 0:
        print("\n尝试点击第一个项目名称...")
        project_names[0].click()
        page.wait_for_timeout(2000)

        # 检查是否出现输入框
        textarea = page.locator('textarea')
        print(f"点击后找到 {textarea.count()} 个 textarea")

        # 检查聊天区域
        chat_area = page.locator('[class*="chatArea"]')
        print(f"找到 {chat_area.count()} 个 chatArea 元素")

        # 截图
        page.screenshot(path=f"{OUTPUT_DIR}/debug_after_click_project.png", full_page=True)

        # 查找所有按钮
        buttons = page.locator("button").all()
        print(f"\n找到 {len(buttons)} 个按钮:")
        for i, btn in enumerate(buttons):
            aria_label = btn.get_attribute("aria-label") or "无aria-label"
            if "输入" in aria_label or "消息" in aria_label or "附件" in aria_label or "确认" in aria_label or "发送" in aria_label:
                print(f"  {i+1}. aria-label='{aria_label}' (聊天相关)")

    browser.close()
