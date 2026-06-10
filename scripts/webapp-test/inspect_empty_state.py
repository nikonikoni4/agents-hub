from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')

    # 等待页面加载
    page.wait_for_timeout(2000)

    # 查找网页预览相关的元素
    print("=== 查找网页预览面板 ===")
    panels = page.locator('[class*="webPreview"]').all()
    print(f"找到 {len(panels)} 个元素")

    for i, panel in enumerate(panels):
        class_name = panel.get_attribute('class')
        print(f"\n元素 {i}: class='{class_name}'")

        # 获取该元素的HTML内容（限制长度）
        html = panel.inner_html()
        if len(html) > 500:
            html = html[:500] + "..."
        print(f"HTML: {html}")

    # 查找空状态文本
    print("\n=== 查找空状态元素 ===")
    empty_texts = page.locator('text=点击消息中的预览卡片查看网页').all()
    print(f"找到 {len(empty_texts)} 个空状态文本")

    if empty_texts:
        parent = empty_texts[0].locator('..')
        parent_class = parent.get_attribute('class')
        print(f"父元素 class: {parent_class}")
        print(f"父元素 HTML: {parent.inner_html()}")

    browser.close()
