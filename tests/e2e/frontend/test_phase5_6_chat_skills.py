"""E2E 测试 Phase 5-6：聊天功能 + 技能浏览"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_chat_and_skills():
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
                if method == "POST" or status >= 400:
                    print(f"[API] {status} {method} {url}")

        page.on("response", handle_response)

        # === Phase 5: 聊天功能 ===
        print("\n--- Phase 5: 聊天功能 ---")

        # 1. 打开页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 2. 选择一个会话
        session_items = page.locator('[class*="sessionItem"], [class*="session-item"]').all()
        if len(session_items) > 0:
            session_items[0].click()
            page.wait_for_timeout(2000)
            screenshot(page, "phase5_01_session_selected")
            print(f"[OK] 选择了会话，共 {len(session_items)} 个会话")

        # 3. 检查消息列表
        messages = page.locator('[class*="message"], [class*="bubble"]').all()
        print(f"[INFO] 发现 {len(messages)} 条消息")
        screenshot(page, "phase5_02_messages")

        # 4. 尝试发送消息
        message_input = page.locator('textarea, input[placeholder*="消息"], input[placeholder*="输入"]').first
        if message_input.is_visible():
            message_input.fill("E2E 测试消息")
            screenshot(page, "phase5_03_message_typed")

            # 发送
            send_btn = page.locator('button[aria-label*="发送"], button:has-text("发送")').first
            if send_btn.is_visible():
                send_btn.click()
                page.wait_for_timeout(3000)
                screenshot(page, "phase5_04_message_sent")
                print("[OK] 消息已发送")

                # 检查消息是否出现在列表中
                page.wait_for_timeout(2000)
                new_messages = page.locator('[class*="message"], [class*="bubble"]').all()
                print(f"[INFO] 发送后消息数: {len(new_messages)}")
                screenshot(page, "phase5_05_after_send")
            else:
                # 尝试 Enter 键发送
                message_input.press("Enter")
                page.wait_for_timeout(3000)
                screenshot(page, "phase5_04_message_sent_enter")
                print("[OK] 通过 Enter 发送消息")
        else:
            print("[SKIP] 未找到消息输入框")

        # 5. 检查右侧成员面板
        member_list = page.locator('[class*="member"], [class*="Member"]').all()
        print(f"[INFO] 右侧面板成员数: {len(member_list)}")

        # === Phase 6: 技能浏览 ===
        print("\n--- Phase 6: 技能浏览 ---")

        # 6. 切换到技能广场
        skill_btn = page.get_by_role("button", name="技能广场")
        if skill_btn.is_visible():
            skill_btn.click()
            page.wait_for_timeout(2000)
            screenshot(page, "phase6_01_skill_square")
            print("[OK] 技能广场打开")

            # 7. 检查技能列表
            skill_cards = page.locator('[class*="skillCard"], [class*="skill-card"]').all()
            print(f"[INFO] 发现 {len(skill_cards)} 个技能卡片")
            screenshot(page, "phase6_02_skill_list")

            # 8. 点击一个技能查看详情
            if len(skill_cards) > 0:
                skill_cards[0].click()
                page.wait_for_timeout(1000)
                screenshot(page, "phase6_03_skill_detail")
                print("[OK] 技能详情打开")

                # 关闭详情
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            else:
                print("[INFO] 没有技能卡片")
        else:
            print("[SKIP] 未找到技能广场按钮")

        # 9. 最终状态
        screenshot(page, "phase5_6_final")

        browser.close()
        post_count = len([c for c in api_calls if "POST" in c])
        print(f"\n[INFO] 总 API 调用: {len(api_calls)} 个，POST 操作: {post_count} 个")
        print("\n[OK] Phase 5-6 测试完成")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5-6: 聊天功能 + 技能浏览测试")
    print("=" * 60)
    test_chat_and_skills()
