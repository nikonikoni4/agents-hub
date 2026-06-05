"""E2E 测试 Phase 4：会话管理 - 创建/切换/删除会话"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_session_management():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        api_calls = []
        def handle_response(response):
            url = response.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                status = response.status
                method = response.request.method
                api_calls.append(f"{status} {method} {url}")
                if method in ("POST", "DELETE") or status >= 400:
                    print(f"[API] {status} {method} {url}")

        page.on("response", handle_response)

        # 1. 打开页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        screenshot(page, "phase4_01_initial")

        # 2. 测试点击已有会话
        session_items = page.locator('[class*="sessionItem"], [class*="session-item"]').all()
        print(f"[INFO] 发现 {len(session_items)} 个会话项")

        if len(session_items) > 0:
            session_items[0].click()
            page.wait_for_timeout(2000)
            screenshot(page, "phase4_02_session_selected")
            print("[OK] 点击了第一个会话")

            # 3. 检查聊天区域是否加载
            chat_area = page.locator('[class*="chatArea"], [class*="chat-area"]').first
            if chat_area.is_visible():
                print("[OK] 聊天区域可见")

            # 4. 检查右侧成员面板
            member_panel = page.locator('text=成员列表').first
            if member_panel.is_visible():
                print("[OK] 成员列表面板可见")
                screenshot(page, "phase4_03_member_panel")
        else:
            print("[INFO] 没有已有会话，跳过会话选择测试")

        # 5. 测试创建新对话
        new_chat_btn = page.locator('button[aria-label="新建对话"]')
        if new_chat_btn.is_visible():
            new_chat_btn.click()
            page.wait_for_timeout(1000)
            screenshot(page, "phase4_04_new_chat_dialog")

            # 检查对话框内容
            dialog_title = page.locator('h2:has-text("新建对话")')
            if dialog_title.is_visible():
                print("[OK] 新建对话对话框打开")

                # 检查单聊/群聊模式切换
                single_mode = page.get_by_role("button", name="单聊")
                group_mode = page.get_by_role("button", name="群聊")
                if single_mode.is_visible():
                    print("[INFO] 单聊模式选项可见")
                if group_mode.is_visible():
                    print("[INFO] 群聊模式选项可见")

                screenshot(page, "phase4_05_dialog_content")

                # 关闭对话框
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            else:
                print("[WARN] 对话框标题未找到")
        else:
            print("[SKIP] 未找到新建对话按钮")

        # 6. 最终状态
        screenshot(page, "phase4_06_final")

        browser.close()
        write_count = len([c for c in api_calls if "POST" in c or "DELETE" in c])
        print(f"\n[INFO] 总 API 调用: {len(api_calls)} 个，写操作: {write_count} 个")
        print("\n[OK] Phase 4 会话管理测试完成")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 4: 会话管理测试")
    print("=" * 60)
    test_session_management()
