"""验证 B1: 创建团队按钮 disabled 问题"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_b1():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # 进入角色管理
        page.get_by_role("button", name="角色管理").click()
        page.wait_for_timeout(2000)

        # 打开创建团队对话框
        page.get_by_text("+ 新建").click()
        page.wait_for_timeout(1000)

        # 填写团队名称
        page.locator('input[placeholder="输入团队名称"]').fill("B1验证团队")
        page.wait_for_timeout(500)

        # 方法1: 直接点击 label（应该触发 checkbox）
        print("\n--- 方法1: 点击 label ---")
        label = page.locator('label:has(input[type="checkbox"])').first
        label.click()
        page.wait_for_timeout(500)

        # 检查 checkbox 状态
        checkbox = page.locator('input[type="checkbox"]').first
        is_checked = checkbox.is_checked()
        print(f"[INFO] checkbox checked: {is_checked}")

        # 检查按钮状态
        submit_btn = page.get_by_role("button", name="创建")
        is_disabled = submit_btn.get_attribute("disabled")
        print(f"[INFO] button disabled attr: {is_disabled}")
        screenshot(page, "b1_01_after_click_label")

        # 方法2: 用 JS 直接触发
        print("\n--- 方法2: JS 直接触发 ---")
        page.evaluate("""() => {
            const checkbox = document.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                checkbox.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }""")
        page.wait_for_timeout(500)

        is_checked2 = checkbox.is_checked()
        print(f"[INFO] checkbox checked after JS: {is_checked2}")

        is_disabled2 = submit_btn.get_attribute("disabled")
        print(f"[INFO] button disabled attr after JS: {is_disabled2}")
        screenshot(page, "b1_02_after_js_trigger")

        # 方法3: 用 force click 直接点击 checkbox
        print("\n--- 方法3: force click checkbox ---")
        checkbox.click(force=True)
        page.wait_for_timeout(500)

        is_checked3 = checkbox.is_checked()
        print(f"[INFO] checkbox checked after force click: {is_checked3}")

        is_disabled3 = submit_btn.get_attribute("disabled")
        print(f"[INFO] button disabled attr after force click: {is_disabled3}")
        screenshot(page, "b1_03_after_force_click")

        browser.close()
        print("\n[OK] B1 验证完成")


if __name__ == "__main__":
    test_b1()
