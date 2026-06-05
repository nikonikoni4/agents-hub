"""E2E 测试 Phase 1：基础功能 - 页面加载和主题切换"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_page_load_and_layout():
    """测试 1: 页面加载和布局验证"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        api_calls = []
        def handle_response(response):
            url = response.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                api_calls.append(f"{response.status} {url}")
                print(f"[API] {response.status} {url}")

        page.on("response", handle_response)

        # 1. 打开页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        screenshot(page, "01_initial_load")

        # 2. 验证布局元素存在
        # 左侧边栏
        sidebar = page.locator('[class*="leftSidebar"], [class*="sidebar"]').first
        assert sidebar.is_visible(), "左侧边栏应该可见"
        print("[OK] 左侧边栏可见")

        # 顶部栏
        topbar = page.locator('[class*="topBar"], [class*="topbar"]').first
        assert topbar.is_visible(), "顶部栏应该可见"
        print("[OK] 顶部栏可见")

        # 聊天区域（默认视图应该是 chat）
        chat_area = page.locator('[class*="chatArea"], [class*="chat"]').first
        assert chat_area.is_visible(), "聊天区域应该可见"
        print("[OK] 聊天区域可见")

        # 3. 验证 API 调用
        print(f"\n[INFO] 页面加载期间的 API 调用: {len(api_calls)} 个")
        for call in api_calls:
            print(f"  - {call}")

        browser.close()
        print("\n[OK] test_page_load_and_layout 完成")


def test_theme_switch():
    """测试 2: 主题切换（亮/暗模式）"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 1. 打开页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 2. 获取初始主题
        initial_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
        print(f"[INFO] 初始主题: {initial_theme}")
        screenshot(page, "02_theme_initial")

        # 3. 找到主题切换按钮并点击
        # 通常在左下角
        theme_btn = page.locator('button:has-text("🌙"), button:has-text("☀"), [class*="theme"]').first
        if theme_btn.is_visible():
            theme_btn.click()
            page.wait_for_timeout(500)
            new_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            print(f"[INFO] 切换后主题: {new_theme}")
            screenshot(page, "03_theme_switched")

            # 验证主题确实切换了
            assert initial_theme != new_theme, f"主题应该切换，但仍然是 {new_theme}"
            print("[OK] 主题切换成功")
        else:
            print("[SKIP] 未找到主题切换按钮，跳过测试")
            screenshot(page, "03_theme_btn_not_found")

        browser.close()
        print("\n[OK] test_theme_switch 完成")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1: 基础功能测试")
    print("=" * 60)

    print("\n--- 测试 1: 页面加载和布局验证 ---")
    test_page_load_and_layout()

    print("\n--- 测试 2: 主题切换 ---")
    test_theme_switch()

    print("\n" + "=" * 60)
    print("Phase 1 测试完成")
    print("=" * 60)
