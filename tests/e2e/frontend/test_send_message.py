"""验证: 发送消息功能（修改后）"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_send_message():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        api_results = []
        def handle_response(response):
            url = response.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                status = response.status
                method = response.request.method
                if method == "POST" and "messages" in url:
                    try:
                        body = response.text()
                    except:
                        body = "(could not read)"
                    api_results.append(f"{status} {method} {url} -> {body[:200]}")
                    print(f"[API] {status} {method} {url}")

        page.on("response", handle_response)

        # 1. 打开页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("load")
        page.wait_for_timeout(5000)

        # 2. 选择一个会话
        session_items = page.locator('[class*="sessionItem"], [class*="session-item"]').all()
        if len(session_items) > 0:
            session_items[0].click()
            page.wait_for_timeout(2000)
            print(f"[OK] 选择了会话")

        # 3. 发送消息（不带 @，应该发给 manager）
        msg_input = page.locator('textarea, input[placeholder*="消息"], input[placeholder*="输入"]').first
        if msg_input.is_visible():
            msg_input.fill("测试消息：你好 manager")
            send_btn = page.locator('button[aria-label*="发送"], button:has-text("发送")').first
            if send_btn.is_visible():
                send_btn.click()
                page.wait_for_timeout(5000)
                screenshot(page, "send_01_no_at")
                print("[OK] 发送了不带@的消息")

        # 4. 发送消息（带 @，应该发给指定成员）
        msg_input2 = page.locator('textarea, input[placeholder*="消息"], input[placeholder*="输入"]').first
        if msg_input2.is_visible():
            msg_input2.fill("@测试 请帮我写个测试")
            send_btn2 = page.locator('button[aria-label*="发送"], button:has-text("发送")').first
            if send_btn2.is_visible():
                send_btn2.click()
                page.wait_for_timeout(5000)
                screenshot(page, "send_02_with_at")
                print("[OK] 发送了带@的消息")

        # 5. 检查结果
        print(f"\n[INFO] POST messages 结果:")
        for r in api_results:
            print(f"  {r}")

        browser.close()
        print("\n[OK] 发送消息验证完成")


if __name__ == "__main__":
    test_send_message()
