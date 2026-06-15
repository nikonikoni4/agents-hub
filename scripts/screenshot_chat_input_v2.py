"""
聊天输入框区域截图脚本 v2
先选择群聊，再截图输入框区域
"""

from playwright.sync_api import sync_playwright

OUTPUT_DIR = "screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})

    # 导航到应用
    page.goto("http://localhost:5173")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    # 点击第一个群聊（task-33-front-im...）
    session_tab = page.locator('.session-tab').first
    if session_tab.count() > 0:
        session_tab.click()
        page.wait_for_timeout(1000)
        print("已点击第一个群聊")
    else:
        print("未找到群聊选项")

    # 等待页面加载
    page.wait_for_timeout(2000)

    # 截图整个页面查看状态
    page.screenshot(path=f"{OUTPUT_DIR}/debug_after_select.png", full_page=True)
    print("调试截图完成: debug_after_select.png")

    # 查找聊天输入框
    chat_input_container = page.locator('[class*="chatInputContainer"]')
    if chat_input_container.count() > 0:
        print(f"找到聊天输入框容器: {chat_input_container.count()} 个")
        chat_input_container.first.screenshot(path=f"{OUTPUT_DIR}/01_chat_input_area.png")
        print("截图1完成: 整个聊天输入框区域")
    else:
        print("未找到聊天输入框容器")

    # 查找加号按钮
    plus_btn = page.locator('button[aria-label="添加附件"]')
    if plus_btn.count() > 0:
        print(f"找到加号按钮: {plus_btn.count()} 个")
        plus_btn.first.screenshot(path=f"{OUTPUT_DIR}/02_plus_button.png")
        print("截图2完成: 加号按钮特写")
    else:
        print("未找到加号按钮")

    # 查找确认按钮
    confirm_btn = page.locator('button[aria-label="确认"]')
    if confirm_btn.count() > 0:
        print(f"找到确认按钮: {confirm_btn.count()} 个")
        confirm_btn.first.screenshot(path=f"{OUTPUT_DIR}/03_confirm_button.png")
        print("截图3完成: 确认按钮特写")
    else:
        print("未找到确认按钮")

    # 查找所有按钮
    buttons = page.locator("button").all()
    print(f"\n找到 {len(buttons)} 个按钮:")
    for i, btn in enumerate(buttons):
        aria_label = btn.get_attribute("aria-label") or "无aria-label"
        if "输入" in aria_label or "消息" in aria_label or "附件" in aria_label or "确认" in aria_label or "发送" in aria_label:
            print(f"  {i+1}. aria-label='{aria_label}' (聊天相关)")

    browser.close()
    print("\n截图完成")
