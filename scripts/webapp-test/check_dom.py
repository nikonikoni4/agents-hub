from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto('http://localhost:5173')
        page.wait_for_load_state('networkidle')

        # 等待5秒让用户切换到"网页"tab
        print("请在浏览器中切换到'网页'tab，5秒后将截图...")
        time.sleep(5)

        # 截图
        page.screenshot(path='screenshot.png', full_page=True)
        print("截图已保存到 screenshot.png")

        # 查找emptyText元素
        empty_elements = page.locator('.emptyText').all()
        print(f"\n找到 {len(empty_elements)} 个 .emptyText 元素")

        # 检查网页预览面板
        web_panel = page.locator('[class*="webPreviewPanel"]').first
        if web_panel.count() > 0:
            print("\n网页预览面板HTML:")
            print(web_panel.inner_html())

        input("按回车关闭浏览器...")
        browser.close()
    except Exception as e:
        print(f"错误: {e}")
        if 'browser' in locals():
            browser.close()
