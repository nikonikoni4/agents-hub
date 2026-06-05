# MiMo 端到端测试流程

## 前置说明

**重要**：你不能直接看图片（你不是多模态模型），你只能使用当前的 `mimo-image` MCP 工具查看图片。

---

## 流程概览

创建todolist来完成：
```
1. 调研阶段 → 2. 测试执行 → 3. 问题记录 → 4. 结果呈现 → 5. 问题修复 → 6. 规则收敛 → 7. 交接文档
```

---

## Step 1：调研阶段

### 1.1 检查测试进度

首先查看 `tests/e2e/frontend/test_process.md` 是否存在：
- **存在**：读取文件，了解当前测试进度，从上次中断的地方继续
- **不存在**：进入调研流程，创建测试计划

### 1.2 派出 Subagent 调研

如果需要调研，派出 Explore 类型的 Subagent 进行以下调研：

1. **前端 UX 调研**：
   - 前端项目的结构和主要模块
   - 已实现的所有 UI/UX 功能
   - 页面路由和视图切换逻辑
   - 表单元素和交互组件

2. **API 端点调研**：
   - 后端 API 路由和端点
   - 请求/响应格式（OpenAPI schema）
   - 错误处理机制

3. **项目文档调研**：
   - `CONTEXT.md` - 仓库术语表
   - `docs/ARCHITECTURE.md` - 架构地图
   - `docs/PRD.md` - 产品需求
   - `docs/specs/` - 产品规格
   - `docs/coding-rules/` - 编码规则

### 1.3 创建测试计划

基于调研结果，创建 `tests/e2e/frontend/test_process.md`，内容包括：

```markdown
# E2E 测试计划

## 测试内容（按依赖关系排序）

### Phase 1：基础功能
1. [ ] 页面加载和布局验证
2. [ ] 主题切换（亮/暗模式）

### Phase 2：角色管理
3. [ ] 查看角色列表
4. [ ] 创建角色
5. [ ] 编辑角色
6. [ ] 删除角色

### Phase 3：团队管理
7. [ ] 查看团队列表
8. [ ] 创建团队（如 UI 支持）
9. [ ] 添加团队成员

### Phase 4：会话管理
10. [ ] 创建单聊会话
11. [ ] 创建群聊会话
12. [ ] 切换会话
13. [ ] 删除会话

### Phase 5：聊天功能
14. [ ] 发送消息
15. [ ] 接收消息
16. [ ] 消息历史查看

### Phase 6：技能浏览
17. [ ] 查看技能列表
18. [ ] 查看技能详情

## 测试环境
- 前端端口：5173
- 后端端口：8099
- Mock 模式：关闭（VITE_USE_MOCK=false）

## 测试数据准备
- [ ] 创建 manager 角色（系统默认）
- [ ] 创建 Leader 角色
- [ ] 创建 Worker 角色
- [ ] 创建测试团队
```

### 1.4 用户审查

将测试计划呈现给用户，确认：
- 测试内容是否完整
- 测试优先级是否正确
- 是否有遗漏的功能

---

## Step 2：测试执行

### 2.1 环境准备

1. 确保后端服务运行：
   ```bash
   nohup uvicorn agents_hub.api.app:app --port 8099 > /tmp/backend.log 2>&1 &
   ```

2. 确认环境变量配置：
   ```
   # frontend/.env.development
   VITE_USE_MOCK=false
   VITE_API_BASE_URL=/api/v1
   VITE_WS_BASE_URL=ws://localhost:8099/api/v1
   ```

3. 确认 Vite proxy 配置：
   ```typescript
   // vite.config.ts
   proxy: {
     '/api': {
       target: 'http://localhost:8099',
       changeOrigin: true,
     },
   }
   ```

### 2.2 编写测试脚本

为每个测试项编写 Playwright 测试脚本，存放在 `tests/e2e/frontend/` 目录：

```python
"""E2E 测试：[测试名称]"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_xxx():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 监听网络请求
        def handle_response(response):
            url = response.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                print(f"[API] {response.status} {url}")

        page.on("response", handle_response)

        # 测试步骤...

        browser.close()
```

### 2.3 运行测试

使用 `with_server.py` 运行测试：

```bash
python "C:\Users\15535\.claude\skills\webapp-testing\scripts\with_server.py" \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python tests/e2e/frontend/test_xxx.py
```

### 2.4 查看截图

使用 `mimo-image` MCP 工具查看截图：

```python
mcp__mimo-image__understand_image(
    image_path="tests/e2e/frontend/screenshots/xxx.png",
    prompt="描述这个页面的状态，包括：1. 显示了什么内容 2. 是否有错误信息 3. 按钮状态"
)
```

---

## Step 3：问题记录

### 3.1 问题分类

测试过程中遇到的问题分为两类：

#### 阻塞性问题（Blocker）
- 无法继续进行后续测试
- 需要修复后才能继续
- 例如：后端 API 返回 500 错误、关键 UI 元素缺失

#### 非阻塞性问题（Non-blocker）
- 可以跳过继续测试
- 记录后后续处理
- 例如：样式问题、非关键功能缺失

### 3.2 处理策略

#### 阻塞性问题处理
1. **立即停止测试**
2. 记录问题详情到 `tests/e2e/frontend/test_issues.md`
3. 尝试解决：
   - 如果是配置问题：修改配置文件
   - 如果是代码问题：修复代码
   - 如果是数据问题：准备测试数据
4. 解决后重新运行失败的测试
5. 如果无法解决：标记为"待解决"，继续其他测试阶段

#### 非阻塞性问题处理
1. 记录问题到 `tests/e2e/frontend/test_issues.md`
2. 在测试脚本中添加跳过逻辑
3. 继续执行后续测试

### 3.3 更新测试进度

每完成一个测试项，更新 `tests/e2e/frontend/test_process.md`：

```markdown
### Phase 2：角色管理
3. [x] 查看角色列表 ✓ 2026-06-05
4. [x] 创建角色 ✓ 2026-06-05
5. [ ] 编辑角色 - 跳过（缺少编辑 UI）
6. [ ] 删除角色 - 跳过（缺少删除 API）
```

---

## Step 4：结果呈现

### 4.1 汇总测试结果

向用户呈现测试结果，包括：

1. **测试统计**：
   - 总测试数：X
   - 通过：X
   - 失败：X
   - 跳过：X

2. **关键发现**：
   - 成功的功能列表
   - 失败的功能列表及原因

3. **问题清单**：
   - 阻塞性问题：X 个
   - 非阻塞性问题：X 个

### 4.2 商讨问题

与用户讨论：
- 哪些问题是优先需要解决的
- 缺少哪些功能需要开发
- 是否需要调整测试计划

---

## Step 5：问题修复

### 5.1 修复阻塞性问题

按照优先级修复问题：

1. **环境配置问题**：
   - 修改 `.env.development`
   - 修改 `vite.config.ts`
   - 重启服务

2. **后端 API 问题**：
   - 检查后端日志
   - 修复 API 代码
   - 添加缺失的初始化逻辑

3. **前端 UI 问题**：
   - 添加缺失的 UI 组件
   - 修复交互逻辑

### 5.2 补充缺失功能

根据测试结果，补充缺失的功能：

1. **系统默认角色**：
   - 在程序初始化时创建 `manager` 角色
   - 先判断是否存在，不存在则创建

2. **团队管理 UI**：
   - 添加创建团队按钮
   - 添加删除团队功能

### 5.3 重新运行测试

修复后重新运行失败的测试，验证问题是否解决。

---

## Step 6：规则收敛

### 6.1 派出 Subagent 收敛规则

派遣 Subagent 调用 `/write-project-rules` skill：

```
任务：基于 E2E 测试发现的问题，收敛编码规则
输入：
  - tests/e2e/frontend/test_issues.md
  - 测试过程中发现的代码问题
输出：
  - 更新 docs/coding-rules/ 相关规则
  - 更新 frontend/CLAUDE.md（如有需要）
```

### 6.2 规则内容

收敛的规则应包括：

1. **环境配置规则**：
   - Mock 模式切换规范
   - API 代理配置规范

2. **测试数据准备规则**：
   - 系统默认角色必须存在
   - 测试团队必须预先创建

3. **错误处理规则**：
   - 异常必须包含 `from e`
   - 错误信息必须详细

---

## Step 7：交接文档

### 7.1 编写交接文档

在 `docs/temp/hand-off/` 目录创建交接文档：

```markdown
# E2E 测试交接文档

## 测试时间
2026-06-05

## 测试范围
- 前端 UI 功能测试
- 后端 API 集成测试

## 测试结果
- 通过：X 项
- 失败：X 项
- 跳过：X 项

## 发现的问题
详见 tests/e2e/frontend/test_issues.md

## 已解决的问题
1. xxx
2. xxx

## 待解决的问题
1. xxx
2. xxx

## 下一步计划
1. xxx
2. xxx

## 相关文件
- tests/e2e/frontend/test_process.md
- tests/e2e/frontend/test_issues.md
- tests/e2e/frontend/screenshots/
```

---

## 附录：测试脚本模板

### 基础测试模板

```python
"""E2E 测试：[测试名称]"""
from pathlib import Path
from playwright.sync_api import sync_playwright

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


def screenshot(page, name: str):
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"[screenshot] {path}")
    return path


def test_xxx():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        # 监听网络请求
        def handle_response(response):
            url = response.url
            if "/api/v1/" in url and not url.endswith(".ts"):
                print(f"[API] {response.status} {url}")

        page.on("response", handle_response)

        # 1. 打开页面
        page.goto("http://localhost:5173")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)
        screenshot(page, "01_initial")

        # 2. 执行操作
        # ...

        # 3. 验证结果
        # ...

        browser.close()
        print("\n[OK] Test completed.")


if __name__ == "__main__":
    test_xxx()
```

### 隐藏元素点击模板

```python
# 方式 1：点击 label
page.locator('label:has-text("选项文本")').click()

# 方式 2：使用 JavaScript
page.evaluate("""() => {
    const radio = document.querySelector('input[type="radio"][name="leader"]');
    if (radio) {
        radio.click();
        radio.dispatchEvent(new Event('change', { bubbles: true }));
    }
}""")
```

### 选择器精确度模板

```python
# 匹配多个元素时使用 nth()
page.get_by_role("button", name="角色管理").nth(1).click()

# 或使用更精确的选择器
page.locator('button.tab:has-text("角色管理")').click()
```
