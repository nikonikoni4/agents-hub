from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    # 点击"网页" tab
    web_tab = page.locator('button:has-text("网页")')
    if web_tab.count() > 0:
        web_tab.first.click()
        page.wait_for_timeout(500)
        print("Clicked '网页' tab")

    # 截图右侧边栏区域
    sidebar = page.locator('[class*="rightSidebar"]')
    if sidebar.count() > 0:
        sidebar.first.screenshot(path='/tmp/web_tab_only.png')
        print("Screenshot of right sidebar saved to /tmp/web_tab_only.png")

    # 检查 webPreviewEmpty 的内容
    empty_panel = page.locator('[class*="webPreviewEmpty"]')
    if empty_panel.count() > 0:
        print(f"\nFound {empty_panel.count()} webPreviewEmpty elements")
        for i in range(empty_panel.count()):
            el = empty_panel.nth(i)
            # 检查是否有 SVG 或其他图标元素
            svgs = el.locator('svg')
            print(f"  Element {i}: {svgs.count()} SVG elements found")
            # 检查所有子元素
            children = el.locator('*')
            print(f"  Element {i}: {children.count()} total child elements")
            for j in range(min(children.count(), 10)):  # 只显示前10个
                child = children.nth(j)
                tag = child.evaluate('el => el.tagName')
                class_name = child.get_attribute('class')
                print(f"    Child {j}: <{tag}> class={class_name}")

    # 检查是否有任何大的 SVG 图标
    all_svgs = page.locator('svg')
    print(f"\nTotal SVG elements on page: {all_svgs.count()}")
    for i in range(min(all_svgs.count(), 20)):  # 只显示前20个
        svg = all_svgs.nth(i)
        bbox = svg.bounding_box()
        if bbox and bbox['width'] > 50:  # 只显示大的 SVG
            print(f"  Large SVG {i}: {bbox['width']}x{bbox['height']} at ({bbox['x']}, {bbox['y']})")
            parent = svg.locator('..')
            parent_class = parent.get_attribute('class')
            print(f"    Parent class: {parent_class}")

    browser.close()
