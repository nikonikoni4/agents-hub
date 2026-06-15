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

    # 1. 截取侧边栏/导航区域
    print("截取侧边栏/导航区域...")
    sidebar = page.locator('[class*="sidebar"], [class*="Sidebar"], nav, [role="navigation"]').first
    if sidebar.is_visible():
        sidebar.screenshot(path='screenshots/sidebar.png')
        print("侧边栏截图完成")
    else:
        print("未找到明确的侧边栏元素，截取左侧区域")
        page.screenshot(path='screenshots/sidebar.png', clip={'x': 0, 'y': 0, 'width': 300, 'height': 1080})

    # 2. 导航到角色管理页面
    print("导航到角色管理页面...")
    role_management = page.locator('text=角色管理').first
    if role_management.is_visible():
        role_management.click()
        time.sleep(2)
        page.screenshot(path='screenshots/role_management.png', full_page=True)
        print("角色管理页面截图完成")
    else:
        print("未找到角色管理入口")

    # 3. 导航到技能广场页面
    print("导航到技能广场页面...")
    skill_square = page.locator('text=技能广场').first
    if skill_square.is_visible():
        skill_square.click()
        time.sleep(2)
        page.screenshot(path='screenshots/skill_square.png', full_page=True)
        print("技能广场页面截图完成")
    else:
        print("未找到技能广场入口")

    # 4. 导航到群聊页面
    print("导航到群聊页面...")
    group_chat = page.locator('text=群聊').first
    if group_chat.is_visible():
        group_chat.click()
        time.sleep(2)
        page.screenshot(path='screenshots/group_chat.png', full_page=True)
        print("群聊页面截图完成")
    else:
        print("未找到群聊入口")

    # 5. 截取主内容区域
    print("截取主内容区域...")
    main_content = page.locator('main, [class*="content"], [class*="Content"]').first
    if main_content.is_visible():
        main_content.screenshot(path='screenshots/main_content.png')
        print("主内容区域截图完成")
    else:
        print("未找到明确的主内容区域，截取右侧区域")
        page.screenshot(path='screenshots/main_content.png', clip={'x': 300, 'y': 0, 'width': 1620, 'height': 1080})

    # 6. 截取技能卡片区域（如果在技能广场页面）
    print("尝试截取技能卡片区域...")
    skill_cards = page.locator('[class*="skill"], [class*="Skill"], [class*="card"], [class*="Card"]').all()
    if skill_cards:
        print(f"找到 {len(skill_cards)} 个技能卡片元素")
        for i, card in enumerate(skill_cards[:5]):  # 只截取前5个
            if card.is_visible():
                card.screenshot(path=f'screenshots/skill_card_{i}.png')
        print("技能卡片截图完成")
    else:
        print("未找到技能卡片元素")

    print("\n所有截图完成！")
    print("生成的截图文件:")
    print("- sidebar.png: 侧边栏/导航区域")
    print("- role_management.png: 角色管理页面")
    print("- skill_square.png: 技能广场页面")
    print("- group_chat.png: 群聊页面")
    print("- main_content.png: 主内容区域")
    print("- skill_card_*.png: 技能卡片区域")

    browser.close()