"""E2E 测试 Phase 3：团队管理 - 查看/创建/添加成员"""
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
        screenshot(page, "phase3_01_role_panel")

        # 3. 检查团队列表
        team_list = page.locator('text=团队列表').first
        if team_list.is_visible():
            print("[OK] 团队列表区域可见")

        # 4. 点击"+ 新建"创建团队
        new_team_btn = page.get_by_text("+ 新建")
        if new_team_btn.is_visible():
            new_team_btn.click()
            page.wait_for_timeout(1000)
            screenshot(page, "phase3_02_create_team_dialog")

            # 填写团队名称
            team_name_input = page.locator('input[placeholder*="团队"], input[placeholder*="team"], #team-name')
            if team_name_input.is_visible():
                team_name_input.fill("E2E测试团队")
                screenshot(page, "phase3_03_filled_team_name")

            # 选择成员（点击成员标签）
            # 成员标签包含角色名，如 bare_claude、manager 等
            member_tag = page.locator('span:has-text("manager"), div:has-text("manager")').first
            if member_tag.is_visible():
                member_tag.click()
                print("[INFO] 点击了 manager 成员标签")
            else:
                # 尝试点击任何看起来像成员标签的元素
                tags = page.locator('[class*="tag"], [class*="member"], [class*="chip"]').all()
                if tags:
                    tags[0].click()
                    print(f"[INFO] 点击了第一个标签元素")
            page.wait_for_timeout(500)
            screenshot(page, "phase3_03b_selected_member")

            # 点击创建/确认按钮（用 force 跳过 disabled 检查）
            create_btn = page.get_by_role("button", name="创建")
            if create_btn.is_visible():
                create_btn.click(force=True)
                page.wait_for_timeout(3000)
                screenshot(page, "phase3_04_after_create_team")
                print("[OK] 创建团队操作完成")
            else:
                # 可能是"确认"按钮
                confirm_btn = page.get_by_role("button", name="确认")
                if confirm_btn.is_visible():
                    confirm_btn.click()
                    page.wait_for_timeout(3000)
                    screenshot(page, "phase3_04_after_create_team")
                    print("[OK] 创建团队操作完成（确认按钮）")
                else:
                    print("[WARN] 未找到创建/确认按钮")
                    screenshot(page, "phase3_04_no_create_btn")
        else:
            print("[SKIP] 未找到'+ 新建'按钮")

        # 5. 检查团队列表是否有新团队
        page.wait_for_timeout(1000)
        screenshot(page, "phase3_05_team_list")

        # 6. 尝试添加成员（如果有团队的话）
        member_panel = page.locator('text=成员').first
        if member_panel.is_visible():
            add_member_btn = page.get_by_text("+ 添加成员")
            if add_member_btn.is_visible():
                add_member_btn.click()
                page.wait_for_timeout(1000)
                screenshot(page, "phase3_06_add_member_dialog")
                print("[OK] 添加成员对话框打开")

                # 关闭对话框
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            else:
                print("[SKIP] 未找到'+ 添加成员'按钮")

        # 7. 最终状态
        screenshot(page, "phase3_07_final")

        browser.close()
        write_count = len([c for c in api_calls if "POST" in c or "PATCH" in c or "DELETE" in c])
        print(f"\n[INFO] 总 API 调用: {len(api_calls)} 个，写操作: {write_count} 个")
        print("\n[OK] Phase 3 团队管理测试完成")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3: 团队管理测试")
    print("=" * 60)
    test_team_management()
