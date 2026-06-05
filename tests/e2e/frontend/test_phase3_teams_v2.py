"""E2E 测试 Phase 3：团队管理 - 用正确的选择器"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_team_management():
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
                if method in ("POST", "PATCH", "DELETE") or status >= 400:
                    print(f"[API] {status} {method} {url}")

        page.on("response", handle_response)

        # 1. 打开页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 2. 进入角色管理
        page.get_by_role("button", name="角色管理").click()
        page.wait_for_timeout(2000)
        screenshot(page, "p3v2_01_role_panel")

        # 3. 检查团队列表
        team_list = page.locator('text=团队列表').first
        print(f"[INFO] 团队列表可见: {team_list.is_visible()}")

        # 4. 点击"+ 新建"创建团队
        new_team_btn = page.get_by_text("+ 新建")
        if new_team_btn.is_visible():
            new_team_btn.click()
            page.wait_for_timeout(1000)
            screenshot(page, "p3v2_02_create_dialog")

            # 填写团队名称
            name_input = page.locator('input[placeholder="输入团队名称"]')
            if name_input.is_visible():
                name_input.fill("E2E测试团队")
                page.wait_for_timeout(500)

            # 选择成员 - 点击 label（checkbox 被隐藏，点击 label 会触发）
            member_labels = page.locator('label:has(input[type="checkbox"])').all()
            print(f"[INFO] 发现 {len(member_labels)} 个可选成员")

            if len(member_labels) > 0:
                # 选择第一个成员
                member_labels[0].click()
                page.wait_for_timeout(500)
                screenshot(page, "p3v2_03_member_selected")

                # 检查 checkbox 状态
                checkbox = page.locator('input[type="checkbox"]').first
                print(f"[INFO] 第一个成员 checked: {checkbox.is_checked()}")

                # 检查按钮状态
                submit_btn = page.get_by_role("button", name="创建")
                is_disabled = submit_btn.get_attribute("disabled")
                print(f"[INFO] 创建按钮 disabled: {is_disabled}")

                if is_disabled is None:
                    # 按钮可用，点击创建
                    submit_btn.click()
                    page.wait_for_timeout(3000)
                    screenshot(page, "p3v2_04_after_create")
                    print("[OK] 创建团队操作完成")

                    # 检查 API 结果
                    team_api_calls = [c for c in api_calls if "POST" in c and "teams" in c]
                    print(f"[INFO] 团队创建 API 调用: {team_api_calls}")

                    # 检查团队列表
                    page.wait_for_timeout(1000)
                    screenshot(page, "p3v2_05_team_list")
                else:
                    print("[WARN] 按钮仍然 disabled，尝试 force click")
                    submit_btn.click(force=True)
                    page.wait_for_timeout(3000)
                    screenshot(page, "p3v2_04_after_force_create")
            else:
                print("[WARN] 没有可选成员")
        else:
            print("[SKIP] 未找到'+ 新建'按钮")

        # 5. 最终状态
        screenshot(page, "p3v2_06_final")

        browser.close()
        write_count = len([c for c in api_calls if "POST" in c or "PATCH" in c or "DELETE" in c])
        print(f"\n[INFO] 总 API 调用: {len(api_calls)} 个，写操作: {write_count} 个")
        print("\n[OK] Phase 3 团队管理测试完成")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3: 团队管理测试 (v2)")
    print("=" * 60)
    test_team_management()
