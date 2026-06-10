from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    # 截图查看当前状态
    page.screenshot(path='current_state.png', full_page=True)
    print("截图已保存到 current_state.png")

    # 查找所有class包含empty的元素
    print("\n=== 所有包含'empty'的元素 ===")
    empties = page.locator('[class*="empty"]').all()
    print(f"找到 {len(empties)} 个元素")

    for i, elem in enumerate(empties[:5]):
        class_name = elem.get_attribute('class')
        text = elem.inner_text()[:100] if elem.inner_text() else ''
        print(f"{i}: class='{class_name}', text='{text}'")

    # 查找所有SVG元素
    print("\n=== SVG元素（前10个）===")
    svgs = page.locator('svg').all()
    print(f"总共找到 {len(svgs)} 个SVG")

    for i, svg in enumerate(svgs[:10]):
        parent_class = svg.locator('..').get_attribute('class') or ''
        viewbox = svg.get_attribute('viewBox') or ''
        print(f"{i}: 父元素class='{parent_class}', viewBox='{viewbox}'")

    browser.close()
