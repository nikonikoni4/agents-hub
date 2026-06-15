"""
调试截图：查看页面当前状态
"""

from playwright.sync_api import sync_playwright

OUTPUT_DIR = "screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})

    # 导航到应用
    page.goto("http://localhost:5173")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # 截图整个页面
    page.screenshot(path=f"{OUTPUT_DIR}/debug_full_page.png", full_page=True)
    print("调试截图完成: debug_full_page.png")

    # 输出页面 HTML 结构
    html = page.content()
    with open(f"{OUTPUT_DIR}/page_structure.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("页面 HTML 已保存到 page_structure.html")

    # 查找所有按钮
    buttons = page.locator("button").all()
    print(f"\n找到 {len(buttons)} 个按钮:")
    for i, btn in enumerate(buttons):
        aria_label = btn.get_attribute("aria-label") or "无aria-label"
        class_name = btn.get_attribute("class") or "无class"
        print(f"  {i+1}. aria-label='{aria_label}', class='{class_name}'")

    browser.close()
