"""
调试截图4：点击具体群聊选项
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

    # 查找群聊列表项
    print("=== 查找群聊列表项 ===")

    # 查找包含时间信息的元素（可能是群聊列表项）
    time_elements = page.locator("text=/分钟前|昨天|今天/").all()
    print(f"找到 {len(time_elements)} 个时间元素")

    # 查找群聊名称
    chat_names = page.locator("[class*='chat-name'], [class*='session-name'], [class*='group-name']").all()
    print(f"找到 {len(chat_names)} 个聊天名称元素")

    # 尝试点击第一个时间元素（可能是群聊列表项）
    if len(time_elements) > 0:
        print("\n尝试点击第一个时间元素...")
        # 获取父元素
        parent = time_elements[0].locator("..")
        parent_class = parent.get_attribute("class") or "无class"
        print(f"父元素 class: {parent_class}")

        # 点击父元素
        parent.click()
        page.wait_for_timeout(2000)

        # 检查是否出现输入框
        textarea = page.locator('textarea')
        print(f"点击后找到 {textarea.count()} 个 textarea")

        # 截图
        page.screenshot(path=f"{OUTPUT_DIR}/debug_after_click_chat_item.png", full_page=True)

        # 查找所有按钮
        buttons = page.locator("button").all()
        print(f"\n找到 {len(buttons)} 个按钮:")
        for i, btn in enumerate(buttons):
            aria_label = btn.get_attribute("aria-label") or "无aria-label"
            if "输入" in aria_label or "消息" in aria_label or "附件" in aria_label or "确认" in aria_label or "发送" in aria_label:
                print(f"  {i+1}. aria-label='{aria_label}' (聊天相关)")

    browser.close()
