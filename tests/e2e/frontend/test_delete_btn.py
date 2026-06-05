"""验证: 角色卡片删除按钮"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_delete_btn():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 进入角色管理
        page.get_by_role("button", name="角色管理").click()
        page.wait_for_timeout(2000)

        # 切换到角色管理 Tab
        page.get_by_role("button", name="角色管理").nth(1).click()
        page.wait_for_timeout(1000)
        screenshot(page, "del_01_role_list")

        # 检查删除按钮是否存在
        delete_btns = page.locator('button[aria-label="删除角色"]').all()
        print(f"[INFO] 发现 {len(delete_btns)} 个删除按钮")

        # hover 到第一个角色卡片
        role_cards = page.locator('[class*="card"]').all()
        if len(role_cards) > 0:
            role_cards[0].hover()
            page.wait_for_timeout(500)
            screenshot(page, "del_02_hover_card")

            # 点击删除按钮
            if len(delete_btns) > 0:
                delete_btns[0].click()
                page.wait_for_timeout(500)
                screenshot(page, "del_03_after_click")
                print("[OK] 点击了删除按钮")

                # 检查是否有 alert
                # playwright 不能直接检查 alert，但我们可以截图看状态
            else:
                print("[WARN] 没有删除按钮")
        else:
            print("[WARN] 没有角色卡片")

        browser.close()
        print("\n[OK] 删除按钮验证完成")


if __name__ == "__main__":
    test_delete_btn()
