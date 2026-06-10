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

    # 查找网页预览面板中的所有SVG
    print("=== 网页预览面板中的所有SVG ===")
    web_panel = page.locator('[class*="webPreviewPanel"]').first
    svgs = web_panel.locator('svg').all()
    print(f"找到 {len(svgs)} 个SVG元素\n")

    for i, svg in enumerate(svgs):
        # 获取SVG的尺寸和位置
        box = svg.bounding_box()
        parent = svg.locator('..')
        parent_class = parent.get_attribute('class')
        viewbox = svg.get_attribute('viewBox')

        print(f"SVG {i}:")
        print(f"  父元素class: {parent_class}")
        print(f"  viewBox: {viewbox}")
        if box:
            print(f"  位置: x={box['x']:.1f}, y={box['y']:.1f}")
            print(f"  尺寸: width={box['width']:.1f}, height={box['height']:.1f}")
        print()

    browser.close()
