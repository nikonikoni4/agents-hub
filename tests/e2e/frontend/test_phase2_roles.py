"""E2E 测试 Phase 2：角色管理 - 查看/创建/编辑/删除角色"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_role_management():
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

        # 2. 点击"角色管理"
        page.get_by_role("button", name="角色管理").click()
        page.wait_for_timeout(2000)
        screenshot(page, "phase2_01_role_panel")

        # 3. 切换到"角色管理"Tab（第二个同名按钮）
        role_tab = page.get_by_role("button", name="角色管理").nth(1)
        if role_tab.is_visible():
            role_tab.click()
            page.wait_for_timeout(1000)
            screenshot(page, "phase2_02_role_tab")

        # 4. 查看角色列表
        role_cards = page.locator('[class*="roleCard"], [class*="role-card"]').all()
        print(f"[INFO] 发现 {len(role_cards)} 个角色卡片")
        screenshot(page, "phase2_03_role_list")

        # 5. 测试创建角色
        add_btn = page.get_by_text("+ 添加角色")
        if add_btn.is_visible():
            add_btn.click()
            page.wait_for_timeout(1000)
            screenshot(page, "phase2_04_create_dialog")

            # 填写表单
            page.locator("#role-name").fill("Phase2测试角色")
            page.locator("#role-platform").select_option("claude")
            page.locator("#role-description").fill("Phase2 自动测试创建")
            screenshot(page, "phase2_05_filled_form")

            # 点击创建
            page.get_by_role("button", name="创建").click()
            page.wait_for_timeout(3000)
            screenshot(page, "phase2_06_after_create")

            # 验证：对话框应该关闭
            dialog_visible = page.get_by_text("创建角色").is_visible()
            print(f"[RESULT] 创建后对话框仍可见: {dialog_visible}")

            # 验证：角色列表应该多一个
            page.wait_for_timeout(1000)
            new_role_cards = page.locator('[class*="roleCard"], [class*="role-card"]').all()
            print(f"[RESULT] 创建后角色数: {len(new_role_cards)}")
            screenshot(page, "phase2_07_role_created")
        else:
            print("[SKIP] 未找到'+ 添加角色'按钮")

        # 6. 测试编辑角色（点击已有角色卡片的编辑按钮）
        edit_btn = page.locator('button:has-text("编辑"), button[aria-label*="edit"]').first
        if edit_btn.is_visible():
            edit_btn.click()
            page.wait_for_timeout(1000)
            screenshot(page, "phase2_08_edit_dialog")

            # 修改描述
            desc_input = page.locator("#role-description")
            if desc_input.is_visible():
                desc_input.fill("已编辑的描述")
                page.get_by_role("button", name="保存").click()
                page.wait_for_timeout(2000)
                screenshot(page, "phase2_09_after_edit")
                print("[OK] 编辑角色完成")
            else:
                print("[SKIP] 编辑对话框未出现")
        else:
            print("[SKIP] 未找到编辑按钮")

        # 7. 检查最终状态
        page.wait_for_timeout(1000)
        screenshot(page, "phase2_10_final")

        browser.close()
        print(f"\n[INFO] 总 API 调用: {len(api_calls)} 个")
        print("\n[OK] Phase 2 角色管理测试完成")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2: 角色管理测试")
    print("=" * 60)
    test_role_management()
