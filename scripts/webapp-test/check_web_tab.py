from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    # 点击"网页"tab
    print("查找并点击'网页'tab...")
    web_tab = page.locator('text=网页').first
    if web_tab.count() > 0:
        web_tab.click()
        page.wait_for_timeout(1000)
        print("已点击'网页'tab")

        # 截图
        page.screenshot(path='web_tab_state.png', full_page=True)
        print("截图已保存到 web_tab_state.png")

        # 查找网页预览面板
        print("\n=== 网页预览面板内容 ===")
        web_panel = page.locator('[class*="webPreviewPanel"]').first
        if web_panel.count() > 0:
            html = web_panel.inner_html()
            print(f"面板HTML:\n{html}\n")

            # 查找所有子元素
            children = web_panel.locator('> *').all()
            print(f"直接子元素数量: {len(children)}")
            for i, child in enumerate(children):
                class_name = child.get_attribute('class')
                tag = child.evaluate('el => el.tagName')
                text = child.inner_text()[:50] if child.inner_text() else ''
                print(f"  {i}: <{tag}> class='{class_name}', text='{text}'")

        else:
            print("未找到webPreviewPanel")
    else:
        print("未找到'网页'tab")

    browser.close()
