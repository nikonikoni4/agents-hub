"""
Loop 4 主界面截图脚本
截图内容：
1. 整体主界面 - 完整的页面布局
2. 左侧边栏 - 会话列表区域
3. 聊天消息区域 - 消息展示区域
4. 右侧边栏 - Agent调用和任务面板（展示状态标签颜色规范化后的效果）
5. 聊天输入框 - 最新状态
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

    # 截图1: 整体主界面
    page.screenshot(path=f"{OUTPUT_DIR}/loop4_01_overview.png", full_page=True)
    print("截图1完成: 整体主界面")

    # 截图2: 左侧边栏
    left_sidebar = page.locator('[class*="leftSidebar"]')
    if left_sidebar.count() > 0:
        left_sidebar.first.screenshot(path=f"{OUTPUT_DIR}/loop4_02_left_sidebar.png")
        print("截图2完成: 左侧边栏")
    else:
        print("未找到左侧边栏")

    # 截图3: 聊天消息区域
    chat_messages = page.locator('[class*="chatMessages"]')
    if chat_messages.count() > 0:
        chat_messages.first.screenshot(path=f"{OUTPUT_DIR}/loop4_03_chat_messages.png")
        print("截图3完成: 聊天消息区域")

        # 截图3.1: Agent消息气泡特写（展示边框效果）
        agent_messages = page.locator('[class*="messageAgent"]')
        if agent_messages.count() > 0:
            agent_messages.first.screenshot(path=f"{OUTPUT_DIR}/loop4_03_1_agent_bubble.png")
            print("截图3.1完成: Agent消息气泡特写（边框效果）")
    else:
        print("未找到聊天消息区域")

    # 截图4: 右侧边栏（展示状态标签颜色规范化后的效果）
    right_sidebar = page.locator('[class*="rightSidebar"]')
    if right_sidebar.count() > 0:
        right_sidebar.first.screenshot(path=f"{OUTPUT_DIR}/loop4_04_right_sidebar.png")
        print("截图4完成: 右侧边栏")

        # 截图4.1: 成员列表特写（展示状态标签颜色）
        member_list = page.locator('[class*="memberList"]')
        if member_list.count() > 0:
            member_list.first.screenshot(path=f"{OUTPUT_DIR}/loop4_04_1_member_list.png")
            print("截图4.1完成: 成员列表特写（状态标签颜色）")

        # 截图4.2: 状态标签特写（空闲/忙碌）
        status_labels = page.locator('[class*="status"]')
        if status_labels.count() > 0:
            status_labels.first.screenshot(path=f"{OUTPUT_DIR}/loop4_04_2_status_label.png")
            print("截图4.2完成: 状态标签特写")
    else:
        print("未找到右侧边栏")

    # 截图5: 聊天输入框
    chat_input = page.locator('[class*="chatInputContainer"]')
    if chat_input.count() > 0:
        chat_input.first.screenshot(path=f"{OUTPUT_DIR}/loop4_05_chat_input.png")
        print("截图5完成: 聊天输入框")

        # 截图5.1: 输入框按钮特写
        input_wrapper = page.locator('[class*="chatInputWrapper"]')
        if input_wrapper.count() > 0:
            input_wrapper.first.screenshot(path=f"{OUTPUT_DIR}/loop4_05_1_input_buttons.png")
            print("截图5.1完成: 输入框按钮特写")
    else:
        print("未找到聊天输入框")

    # 输出页面结构信息
    print("\n=== 页面结构信息 ===")
    print(f"左侧边栏: {left_sidebar.count()} 个")
    print(f"聊天消息区域: {chat_messages.count()} 个")
    print(f"右侧边栏: {right_sidebar.count()} 个")
    print(f"聊天输入框: {chat_input.count()} 个")

    # 输出消息气泡信息
    agent_messages = page.locator('[class*="messageAgent"]')
    user_messages = page.locator('[class*="messageUser"]')
    print(f"Agent消息气泡: {agent_messages.count()} 个")
    print(f"用户消息气泡: {user_messages.count()} 个")

    # 输出状态标签信息
    status_labels = page.locator('[class*="status"]')
    print(f"状态标签: {status_labels.count()} 个")

    browser.close()
    print("\n所有截图已完成，保存在 screenshots/ 目录")
