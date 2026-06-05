"""E2E 测试：创建角色流程"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_create_role():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 监听所有网络请求和响应
        def handle_request(request):
            url = request.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                print(f"[REQ] {request.method} {url}")

        def handle_response(response):
            url = response.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                try:
                    body = response.text()
                    print(f"[RES] {response.status} {url} -> {body[:200]}")
                except:
                    print(f"[RES] {response.status} {url} -> (could not read body)")

        def handle_requestfailed(request):
            print(f"[FAIL] {request.url} - {request.failure}")

        page.on("request", handle_request)
        page.on("response", handle_response)
        page.on("requestfailed", handle_requestfailed)

        # 1. 打开前端页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)

        screenshot(page, "role_01_initial")

        # 2. 点击左侧边栏的"角色管理"Tab
        page.get_by_role("button", name="角色管理").click()
        page.wait_for_timeout(3000)

        screenshot(page, "role_02_role_management")

        # 3. 检查团队列表
        team_buttons = page.locator('button:has-text("成员")').all()
        print(f"Found {len(team_buttons)} team buttons")

        if len(team_buttons) == 0:
            print("No teams found. Test cannot continue.")
            screenshot(page, "role_03_no_teams")
            browser.close()
            return

        # 4. 选择第一个团队
        team_buttons[0].click()
        page.wait_for_timeout(1000)
        screenshot(page, "role_04_team_selected")

        # 5. 切换到"角色管理"Tab
        page.get_by_role("button", name="角色管理").nth(1).click()
        page.wait_for_timeout(1000)
        screenshot(page, "role_05_role_tab")

        # 6. 点击"+ 添加角色"按钮
        add_role_btn = page.get_by_text("+ 添加角色")
        add_role_btn.wait_for(state="visible", timeout=5000)
        add_role_btn.click()

        # 7. 等待对话框出现
        page.get_by_text("创建角色").wait_for(state="visible", timeout=5000)
        screenshot(page, "role_06_dialog_opened")

        # 8. 填写角色名称
        page.locator("#role-name").fill("E2E测试角色")

        # 9. 选择平台
        page.locator("#role-platform").select_option("claude")

        # 10. 填写描述（可选）
        page.locator("#role-description").fill("这是一个E2E测试创建的角色")
        screenshot(page, "role_07_filled_form")

        # 11. 点击创建按钮
        page.get_by_role("button", name="创建").click()

        # 12. 等待响应
        page.wait_for_timeout(3000)
        screenshot(page, "role_08_after_create")

        # 13. 检查角色是否创建成功
        dialog_visible = page.get_by_text("创建角色").is_visible()
        print(f"Dialog still visible: {dialog_visible}")

        page.wait_for_timeout(1000)
        screenshot(page, "role_09_final_state")

        browser.close()
        print("\n[OK] Create role E2E test completed.")


if __name__ == "__main__":
    test_create_role()
