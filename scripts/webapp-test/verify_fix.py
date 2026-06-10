from playwright.sync_api import sync_playwright
import sys

# 简单测试：检查 webPreviewEmpty 类是否存在
with sync_playwright() as p:
    try:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('http://localhost:5173')
        page.wait_for_load_state('networkidle')

        # 获取页面HTML
        html = page.content()

        # 检查是否包含新的类名
        if 'webPreviewEmpty' in html:
            print("✓ 新的 webPreviewEmpty 类已应用")
        else:
            print("✗ 未找到 webPreviewEmpty 类")

        # 检查网页预览面板
        web_panels = page.locator('[class*="webPreview"]').all()
        print(f"✓ 找到 {len(web_panels)} 个网页预览相关元素")

        browser.close()
        sys.exit(0)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
