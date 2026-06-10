from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')

    # 截图
    page.screenshot(path='page_inspect.png', full_page=True)

    # 获取页面HTML
    content = page.content()
    with open('page_content.html', 'w', encoding='utf-8') as f:
        f.write(content)

    # 查找可能的地球图标元素
    print("=== SVG elements ===")
    svgs = page.locator('svg').all()
    print(f"Found {len(svgs)} SVG elements")

    print("\n=== Elements with 'globe' in class or id ===")
    globe_elements = page.locator('[class*="globe"], [id*="globe"]').all()
    print(f"Found {len(globe_elements)} elements")

    print("\n=== Large elements (might be the globe) ===")
    large_elements = page.locator('svg[width], svg[height]').all()
    for i, elem in enumerate(large_elements[:5]):
        print(f"Element {i}: {elem.get_attribute('class')}, width={elem.get_attribute('width')}, height={elem.get_attribute('height')}")

    browser.close()
