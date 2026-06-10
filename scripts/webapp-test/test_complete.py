from playwright.sync_api import sync_playwright
import sys
import io

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    print("✓ 页面加载成功")

    # 点击"网页"tab
    web_tab = page.locator('text=网页').first
    web_tab.click()
    page.wait_for_timeout(500)
    print("✓ 已切换到网页tab")

    # 检查空状态
    empty_text = page.locator('text=点击消息中的预览卡片查看网页').first
    if empty_text.count() > 0:
        print("✓ 空状态显示正常")
    else:
        print("✗ 未找到空状态文本")

    # 检查标题栏
    header = page.locator('[class*="webPreviewHeader"]').first
    if header.count() > 0:
        print("✓ 标题栏显示正常")

        # 检查SVG图标大小
        svg = header.locator('svg').first
        if svg.count() > 0:
            box = svg.bounding_box()
            if box and box['width'] <= 20 and box['height'] <= 20:
                print(f"✓ 地球图标大小正常: {box['width']:.0f}x{box['height']:.0f}px")
            else:
                print(f"✗ 地球图标过大: {box['width']:.0f}x{box['height']:.0f}px" if box else "✗ 无法获取图标大小")
        else:
            print("✗ 未找到地球图标")
    else:
        print("✗ 未找到标题栏")

    print("\n所有检查完成！")
    browser.close()
