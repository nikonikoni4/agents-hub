from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 900})
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')

    # 等待页面完全加载
    page.wait_for_timeout(2000)

    # 点击"网页" tab
    web_tab = page.locator('button:has-text("网页")')
    if web_tab.count() > 0:
        web_tab.first.click()
        page.wait_for_timeout(500)
        print("Clicked '网页' tab")
    else:
        print("'网页' tab not found")

    # 截图当前状态
    page.screenshot(path='/tmp/web_preview_state.png', full_page=True)
    print("Screenshot saved to /tmp/web_preview_state.png")

    # 查看右侧边栏的 HTML 结构
    sidebar = page.locator('[class*="rightSidebar"]')
    if sidebar.count() > 0:
        sidebar_html = sidebar.first.inner_html()
        print("\n=== Right Sidebar HTML (first 5000 chars) ===")
        print(sidebar_html[:5000])

    # 查看是否有 webPreviewPanel
    web_panel = page.locator('[class*="webPreview"]')
    if web_panel.count() > 0:
        print(f"\n=== Found {web_panel.count()} Web Preview elements ===")
        for i in range(web_panel.count()):
            el = web_panel.nth(i)
            class_name = el.get_attribute('class')
            print(f"\nElement {i}: class={class_name}")
            inner = el.inner_html()
            print(f"  innerHTML: {inner[:800]}")

    browser.close()
