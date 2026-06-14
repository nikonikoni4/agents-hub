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

    # 导航到技能广场
    print("导航到技能广场页面...")
    skill_square = page.locator('text=技能广场').first
    if skill_square.is_visible():
        skill_square.click()
        time.sleep(3)  # 等待页面完全加载
        page.wait_for_load_state('networkidle')
    else:
        print("未找到技能广场入口")
        browser.close()
        exit()

    # 截取完整页面截图
    print("截取技能广场完整页面...")
    page.screenshot(path='screenshots/skill_square_full.png', full_page=True)

    # 截取视口截图
    print("截取技能广场视口截图...")
    page.screenshot(path='screenshots/skill_square_viewport.png')

    # 截取搜索/筛选区域
    print("截取搜索和筛选区域...")
    search_area = page.locator('[class*="search"], [class*="Search"], input[placeholder*="搜索"]').first
    if search_area.is_visible():
        # 获取搜索区域的边界框
        box = search_area.bounding_box()
        if box:
            # 扩大截图范围，包含筛选标签
            page.screenshot(path='screenshots/skill_search_filter.png', clip={
                'x': max(0, box['x'] - 50),
                'y': max(0, box['y'] - 50),
                'width': min(1920, box['width'] + 100),
                'height': min(300, box['height'] + 150)
            })
            print("搜索/筛选区域截图完成")
    else:
        print("未找到明确的搜索区域")

    # 截取单个技能卡片详细内容
    print("截取技能卡片详细内容...")
    skill_cards = page.locator('[class*="skill"], [class*="Skill"], [class*="card"], [class*="Card"]').all()
    if skill_cards:
        # 截取第一个技能卡片
        first_card = skill_cards[0]
        if first_card.is_visible():
            first_card.screenshot(path='screenshots/skill_card_detail.png')
            print(f"技能卡片截图完成，共找到 {len(skill_cards)} 个卡片")

        # 截取包含多个卡片的区域
        if len(skill_cards) >= 4:
            # 获取前4个卡片的位置，截取一个网格区域
            boxes = []
            for card in skill_cards[:4]:
                box = card.bounding_box()
                if box:
                    boxes.append(box)

            if boxes:
                min_x = min(b['x'] for b in boxes) - 20
                min_y = min(b['y'] for b in boxes) - 20
                max_x = max(b['x'] + b['width'] for b in boxes) + 20
                max_y = max(b['y'] + b['height'] for b in boxes) + 20

                page.screenshot(path='screenshots/skill_cards_grid.png', clip={
                    'x': max(0, min_x),
                    'y': max(0, min_y),
                    'width': min(1920, max_x - min_x),
                    'height': min(1080, max_y - min_y)
                })
                print("技能卡片网格截图完成")

    # 尝试将鼠标悬停在技能卡片上，查看tooltip
    print("尝试查看技能卡片tooltip...")
    if skill_cards and skill_cards[0].is_visible():
        skill_cards[0].hover()
        time.sleep(1)
        page.screenshot(path='screenshots/skill_card_tooltip.png')
        print("技能卡片悬停状态截图完成")

    print("\n所有技能广场截图完成！")

    browser.close()