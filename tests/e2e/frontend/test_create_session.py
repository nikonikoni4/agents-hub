"""E2E 测试：创建会话流程"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_create_session():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 监听网络请求
        def handle_response(response):
            url = response.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                print(f"[API] {response.status} {url}")

        page.on("response", handle_response)

        # 1. 打开前端页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        screenshot(page, "session_01_initial")

        # 2. 点击"新对话"按钮
        new_chat_btn = page.locator('button[aria-label="新建对话"]')
        new_chat_btn.wait_for(state="visible", timeout=10000)
        new_chat_btn.click()

        # 3. 等待对话框出现
        dialog = page.locator('h2:has-text("新建对话")')
        dialog.wait_for(state="visible", timeout=5000)
        screenshot(page, "session_02_dialog_opened")

        # 4. 填写群组名称
        name_input = page.locator('input[placeholder="输入群组名称"]')
        name_input.wait_for(state="visible", timeout=5000)
        name_input.fill("E2E测试会话")
        page.wait_for_timeout(1000)

        # 5. 等待角色列表加载
        page.wait_for_timeout(2000)
        screenshot(page, "session_03_filled_name")

        # 6. 选择 Leader（使用 label 点击）
        # 找到包含 "E2E测试Leader" 的 label
        leader_label = page.locator('label:has-text("E2E测试Leader")')
        if leader_label.is_visible():
            leader_label.click()
            page.wait_for_timeout(500)
            screenshot(page, "session_04_selected_leader")
        else:
            print("Leader label not found")

        # 7. 选择 Worker（使用 label 点击）
        worker_label = page.locator('label:has-text("E2E测试角色")')
        if worker_label.is_visible():
            worker_label.click()
            page.wait_for_timeout(500)
            screenshot(page, "session_05_selected_worker")
        else:
            print("Worker label not found")

        # 8. 填写项目路径
        project_input = page.locator('input[placeholder="/home/user/projects/your-project"]')
        if project_input.is_visible():
            project_input.fill("/tmp/e2e-test-project")
            screenshot(page, "session_06_filled_project")

        # 9. 检查创建按钮状态
        create_btn = page.locator('button:has-text("创建")')
        is_enabled = create_btn.is_enabled()
        print(f"Create button enabled: {is_enabled}")

        # 10. 点击创建按钮
        if is_enabled:
            create_btn.click()

            # 等待 API 调用完成（可能需要较长时间）
            page.wait_for_timeout(10000)
            screenshot(page, "session_07_after_create")
        else:
            print("Create button is disabled, cannot click")
            screenshot(page, "session_07_button_disabled")

        # 11. 最终状态
        page.wait_for_timeout(2000)
        screenshot(page, "session_08_final_state")

        # 12. 检查对话框是否关闭
        dialog_visible = page.locator('h2:has-text("新建对话")').is_visible()
        print(f"Dialog still visible: {dialog_visible}")

        # 13. 检查会话列表
        session_items = page.locator('.session-item').all()
        print(f"Session items: {len(session_items)}")

        browser.close()
        print("\n[OK] Create session E2E test completed.")


if __name__ == "__main__":
    test_create_session()
