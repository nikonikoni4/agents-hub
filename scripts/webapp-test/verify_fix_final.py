from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    # 点击"网页"tab
    web_tab = page.locator('text=网页').first
    web_tab.click()
    page.wait_for_timeout(1000)

    # 截图
    page.screenshot(path='fixed_web_tab.png', full_page=True)
    print("修复后截图已保存到 fixed_web_tab.png")

    # 检查SVG尺寸
    web_panel = page.locator('[class*="webPreviewPanel"]').first
    svgs = web_panel.locator('svg').all()
    print(f"\n找到 {len(svgs)} 个SVG元素")

    for i, svg in enumerate(svgs):
        box = svg.bounding_box()
        if box:
            print(f"SVG {i}: width={box['width']:.1f}, height={box['height']:.1f}")

    browser.close()
