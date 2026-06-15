"""
聊天输入框区域截图脚本
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

    # 等待页面完全加载
    page.wait_for_timeout(2000)

    # 截图1: 整个聊天输入框区域
    chat_input_container = page.locator('[class*="chatInputContainer"]')
    if chat_input_container.count() > 0:
        chat_input_container.first.screenshot(path=f"{OUTPUT_DIR}/01_chat_input_area.png")
        print("截图1完成: 整个聊天输入框区域")
    else:
        print("未找到聊天输入框容器，尝试备选选择器...")
        # 备选：尝试通过 textarea 定位
        textarea = page.locator('textarea[aria-label="输入消息"]')
        if textarea.count() > 0:
            # 获取父容器
            parent = textarea.locator("..")
            parent.screenshot(path=f"{OUTPUT_DIR}/01_chat_input_area.png")
            print("截图1完成: 整个聊天输入框区域（通过备选选择器）")

    # 截图2: 加号按钮（添加附件）特写
    plus_btn = page.locator('button[aria-label="添加附件"]')
    if plus_btn.count() > 0:
        plus_btn.first.screenshot(path=f"{OUTPUT_DIR}/02_plus_button.png")
        print("截图2完成: 加号按钮特写")
    else:
        print("未找到加号按钮")

    # 截图3: 确认按钮（时钟图标）特写
    confirm_btn = page.locator('button[aria-label="确认"]')
    if confirm_btn.count() > 0:
        confirm_btn.first.screenshot(path=f"{OUTPUT_DIR}/03_confirm_button.png")
        print("截图3完成: 确认按钮特写")
    else:
        print("未找到确认按钮")

    # 额外截图: 整体输入区域概览
    input_wrapper = page.locator('[class*="chatInputWrapper"]')
    if input_wrapper.count() > 0:
        input_wrapper.first.screenshot(path=f"{OUTPUT_DIR}/04_input_wrapper.png")
        print("截图4完成: 输入区域包装器")

    browser.close()
    print("\n所有截图已完成，保存在 screenshots/ 目录")
