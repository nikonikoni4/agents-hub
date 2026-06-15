"""
聊天输入框区域截图脚本 - 最终版本
截图内容：
1. 整个聊天输入框区域
2. 加号按钮（添加附件）特写
3. 确认按钮（时钟图标）特写
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

    # 展开群聊列表
    project_header = page.locator(".project-header")
    if project_header.count() > 0:
        project_header.first.click()
        page.wait_for_timeout(1000)

    # 点击第一个群聊列表项
    session_items = page.locator("[class*='session-item'], [class*='chat-item'], [class*='group-item']").all()
    if len(session_items) > 0:
        session_items[0].click()
        page.wait_for_timeout(2000)
        print("已选择群聊")
    else:
        print("未找到群聊列表项")
        browser.close()
        exit(1)

    # 截图1: 整个聊天输入框区域
    chat_input_container = page.locator('[class*="chatInputContainer"]')
    if chat_input_container.count() > 0:
        chat_input_container.first.screenshot(path=f"{OUTPUT_DIR}/01_chat_input_area.png")
        print("截图1完成: 整个聊天输入框区域")
    else:
        print("未找到聊天输入框容器，尝试备选选择器...")
        # 备选：通过 textarea 定位
        textarea = page.locator('textarea[aria-label="输入消息"]')
        if textarea.count() > 0:
            # 向上查找父容器
            parent = textarea.locator("../..")
            parent.screenshot(path=f"{OUTPUT_DIR}/01_chat_input_area.png")
            print("截图1完成: 整个聊天输入框区域（通过备选选择器）")

    # 截图2: 加号按钮（添加附件）特写
    plus_btn = page.locator('button[aria-label="添加附件"]')
    if plus_btn.count() > 0:
        plus_btn.first.screenshot(path=f"{OUTPUT_DIR}/02_plus_button.png")
        print("截图2完成: 加号按钮特写")
    else:
        print("未找到加号按钮，尝试查找其他选择器...")
        # 尝试查找包含 + 图标的按钮
        plus_icon = page.locator('svg line[x1="12"][y1="5"][x2="12"][y2="19"]').locator("..")
        if plus_icon.count() > 0:
            plus_icon.first.screenshot(path=f"{OUTPUT_DIR}/02_plus_button.png")
            print("截图2完成: 加号按钮特写（通过图标选择器）")

    # 截图3: 确认按钮（时钟图标）特写
    confirm_btn = page.locator('button[aria-label="确认"]')
    if confirm_btn.count() > 0:
        confirm_btn.first.screenshot(path=f"{OUTPUT_DIR}/03_confirm_button.png")
        print("截图3完成: 确认按钮特写")
    else:
        print("未找到确认按钮，尝试查找其他选择器...")
        # 尝试查找包含圆形+勾号的按钮
        check_circle = page.locator('svg circle[cx="12"][cy="12"][r="10"]').locator("..")
        if check_circle.count() > 0:
            check_circle.first.screenshot(path=f"{OUTPUT_DIR}/03_confirm_button.png")
            print("截图3完成: 确认按钮特写（通过图标选择器）")

    # 截图4: 发送按钮特写
    send_btn = page.locator('button[aria-label="发送消息"]')
    if send_btn.count() > 0:
        send_btn.first.screenshot(path=f"{OUTPUT_DIR}/04_send_button.png")
        print("截图4完成: 发送按钮特写")

    # 截图5: 整体输入区域概览（包含所有按钮）
    input_wrapper = page.locator('[class*="chatInputWrapper"]')
    if input_wrapper.count() > 0:
        input_wrapper.first.screenshot(path=f"{OUTPUT_DIR}/05_input_wrapper.png")
        print("截图5完成: 输入区域包装器")

    # 输出所有按钮信息
    print("\n=== 聊天输入框相关按钮 ===")
    buttons = page.locator("button").all()
    for i, btn in enumerate(buttons):
        aria_label = btn.get_attribute("aria-label") or "无aria-label"
        if "输入" in aria_label or "消息" in aria_label or "附件" in aria_label or "确认" in aria_label or "发送" in aria_label:
            print(f"  {i+1}. aria-label='{aria_label}'")

    browser.close()
    print("\n所有截图已完成，保存在 screenshots/ 目录")
