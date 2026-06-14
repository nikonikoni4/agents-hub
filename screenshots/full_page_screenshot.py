from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    # 访问前端页面
    print("正在访问前端页面...")
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    time.sleep(2)  # 等待页面完全渲染

    # 截取完整页面截图
    print("截取完整页面截图...")
    page.screenshot(path='screenshots/full_page.png', full_page=True)

    # 截取视口截图
    print("截取视口截图...")
    page.screenshot(path='screenshots/viewport.png')

    # 查看页面标题和URL
    print(f"页面标题: {page.title()}")
    print(f"当前URL: {page.url}")

    # 获取页面内容，用于分析结构
    content = page.content()
    with open('screenshots/page_structure.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print("截图完成！")
    print("- full_page.png: 完整页面截图")
    print("- viewport.png: 视口截图")
    print("- page_structure.html: 页面结构")

    browser.close()