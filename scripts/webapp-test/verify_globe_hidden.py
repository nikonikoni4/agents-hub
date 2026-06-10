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
        sidebar.first.screenshot(path='/tmp/after_hide_globe.png')
        print("Screenshot saved to /tmp/after_hide_globe.png")

    # 检查 webPreviewHeader 中是否有 SVG 元素
    header = page.locator('[class*="webPreviewHeader"]')
    if header.count() > 0:
        svgs = header.first.locator('svg')
        print(f"\nwebPreviewHeader has {svgs.count()} SVG elements")
        if svgs.count() == 0:
            print("SUCCESS: GlobeIcon is hidden!")
        else:
            print("FAIL: GlobeIcon is still visible")

    # 检查 webPreviewEmpty 的内容
    empty_panel = page.locator('[class*="webPreviewEmpty"]')
    if empty_panel.count() > 0:
        print(f"\nwebPreviewEmpty has {empty_panel.count()} elements")
        children = empty_panel.first.locator('*')
        print(f"  Children: {children.count()}")
        for i in range(children.count()):
            child = children.nth(i)
            tag = child.evaluate('el => el.tagName')
            text = child.text_content()
            print(f"    Child {i}: <{tag}> text='{text}'")

    browser.close()
