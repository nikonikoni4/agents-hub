from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    # 访问前端页面
    print("正在访问前端页面...")
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    time.sleep(2)

    # 选择一个群聊进入主界面
    print("选择群聊进入主界面...")
    group_chat = page.locator('text=前端优化团队2').first
    if group_chat.is_visible():
        group_chat.click()
        time.sleep(3)  # 等待对话页面加载
        page.wait_for_load_state('networkidle')
        print("已进入群聊页面")
    else:
        # 尝试其他群聊
        group_chat = page.locator('text=前端UI优化团队1').first
        if group_chat.is_visible():
            group_chat.click()
            time.sleep(3)
            page.wait_for_load_state('networkidle')
            print("已进入群聊页面")
        else:
            print("未找到群聊入口，尝试点击第一个群聊")
            first_chat = page.locator('[class*="chat"], [class*="Chat"], [class*="conversation"]').first
            if first_chat.is_visible():
                first_chat.click()
                time.sleep(3)
                page.wait_for_load_state('networkidle')

    # 截取完整主界面
    print("截取完整主界面...")
    page.screenshot(path='screenshots/main_interface_full.png', full_page=True)

    # 截取视口截图
    print("截取主界面视口截图...")
    page.screenshot(path='screenshots/main_interface_viewport.png')

    # 截取输入框区域（重点）
    print("截取输入框区域...")
    # 查找输入框元素
    input_area = page.locator('textarea, input[type="text"], [class*="input"], [class*="Input"], [class*="editor"], [class*="Editor"]').first
    if input_area.is_visible():
        box = input_area.bounding_box()
        if box:
            # 扩大截图范围，包含输入框周围的按钮
            page.screenshot(path='screenshots/input_area_detail.png', clip={
                'x': max(0, box['x'] - 100),
                'y': max(0, box['y'] - 100),
                'width': min(1920, box['width'] + 200),
                'height': min(400, box['height'] + 200)
            })
            print("输入框区域截图完成")
    else:
        print("未找到明确的输入框元素，截取底部区域")
        # 截取底部区域，通常输入框在底部
        page.screenshot(path='screenshots/input_area_detail.png', clip={
            'x': 0,
            'y': 700,
            'width': 1920,
            'height': 380
        })

    # 尝试聚焦输入框并截图
    print("尝试聚焦输入框...")
    try:
        page.click('textarea, input[type="text"], [class*="input"], [class*="Input"]', timeout=3000)
        time.sleep(1)
        page.screenshot(path='screenshots/input_area_focused.png')
        print("输入框聚焦状态截图完成")
    except:
        print("无法聚焦输入框")

    # 截取左侧栏
    print("截取左侧栏...")
    page.screenshot(path='screenshots/left_sidebar.png', clip={
        'x': 0,
        'y': 0,
        'width': 300,
        'height': 1080
    })

    # 截取消息区域
    print("截取消息区域...")
    message_area = page.locator('[class*="message"], [class*="Message"], [class*="chat-content"], [class*="ChatContent"]').first
    if message_area.is_visible():
        message_area.screenshot(path='screenshots/message_area.png')
        print("消息区域截图完成")
    else:
        print("未找到明确的消息区域，截取中间区域")
        page.screenshot(path='screenshots/message_area.png', clip={
            'x': 300,
            'y': 0,
            'width': 1200,
            'height': 800
        })

    # 截取右侧面板
    print("截取右侧面板...")
    page.screenshot(path='screenshots/right_panel.png', clip={
        'x': 1500,
        'y': 0,
        'width': 420,
        'height': 1080
    })

    print("\n所有主界面截图完成！")

    browser.close()