"""测试 Claude CLI 错误处理

测试目标：验证 Claude CLI 的错误是否会被静默处理，即 try/except 无法捕获 CLI 内部错误

测试场景：
1. 权限错误：让 Claude 执行一个被 deny 列表阻止的命令（git log）
2. API 错误：使用错误的 API key

===============================================================================
测试结论（2026-05-30）：
===============================================================================

1. try/except 无法捕获 CLI 错误
   - asyncio.create_subprocess_exec 只在进程启动失败时抛出 FileNotFoundError
   - 进程正常启动后，无论内部发生什么错误，都不会抛出异常
   - 即使返回码非零，也不会触发 except 块

2. 错误捕获方式对比：

   | 错误类型   | try/except | 返回码 | JSON 输出字段                    |
   |-----------|------------|--------|----------------------------------|
   | 权限错误   | ❌ 无法捕获 | 0      | permission_denials 不为空         |
   | API 错误   | ❌ 无法捕获 | 1      | is_error=true, api_error_status  |

3. 正确的错误检测方式：

   ```python
   # ❌ 错误：try/except 无法捕获
   try:
       process = await asyncio.create_subprocess_exec(...)
   except Exception:
       # 这里不会被执行
       pass

   # ✅ 正确：解析 JSON 输出
   async for line in process.stdout:
       data = json.loads(line)

       # 检查权限错误
       if data.get("permission_denials"):
           raise PermissionError(f"CLI 权限拒绝: {data['permission_denials']}")

       # 检查 API 错误
       if data.get("type") == "result" and data.get("is_error"):
           raise RuntimeError(f"CLI 错误: {data.get('result')}")

       # 检查 API 重试
       if data.get("type") == "system" and data.get("subtype") == "api_retry":
           raise RuntimeError(f"API 认证失败: {data.get('error')}")

   # 检查返回码
   if process.returncode != 0:
       raise RuntimeError(f"CLI 进程异常退出: {process.returncode}")
   ```

4. 为什么 try/except 无法捕获？

   原因：Claude CLI 的错误是"业务逻辑错误"，不是"系统异常"

   - asyncio.create_subprocess_exec 只关心：进程能否启动？stdout/stderr 能否读取？
   - CLI 内部的错误（权限拒绝、API 认证失败）通过 JSON 输出传递，不是通过异常
   - 这是设计选择：CLI 用 JSON 流式输出报告状态，而不是抛异常

   类比：
   - 你调用 curl 请求一个 API，返回 401 错误
   - curl 进程正常退出（返回码可能是 0 或 1）
   - 但 curl 不会抛 Python 异常，你需要检查响应内容

5. 需要解析的 JSON 字段：

   权限错误检测：
   - data["permission_denials"] - 非空数组表示有权限拒绝
   - 每个元素包含: tool_name, tool_use_id, tool_input

   API 错误检测：
   - data["type"] == "result" && data["is_error"] == true
   - data["api_error_status"] - HTTP 状态码（如 401）
   - data["result"] - 错误消息文本
   - data["type"] == "system" && data["subtype"] == "api_retry" - 重试事件

===============================================================================
测试 1 真实返回值（权限错误）：
===============================================================================

进程返回码: 0

关键 JSON 输出（permission_denials 不为空）：
{
    "type": "result",
    "subtype": "success",
    "is_error": false,
    "api_error_status": null,
    "duration_ms": 21125,
    "num_turns": 2,
    "result": "我只有 PowerShell 工具可以执行终端命令，没有独立的 Bash 工具...",
    "permission_denials": [
        {
            "tool_name": "PowerShell",
            "tool_use_id": "call_d530fa0417154ee79ede21f4",
            "tool_input": {
                "command": "git log --oneline -10",
                "description": "查看最近10条提交记录"
            }
        }
    ],
    "terminal_reason": "completed"
}

try/except 捕获结果: ❌ 未触发任何异常
返回码捕获结果: ❌ 返回码为 0（成功）
JSON 解析结果: ✅ permission_denials 不为空，包含被拒绝的工具调用

===============================================================================
测试 2 真实返回值（API 错误）：
===============================================================================

进程返回码: 1

重试事件（共 10 次）：
{
    "type": "system",
    "subtype": "api_retry",
    "attempt": 1,
    "max_retries": 10,
    "retry_delay_ms": 524.72,
    "error_status": 401,
    "error": "authentication_failed",
    "session_id": "37d175b6-..."
}
... (重复 10 次)

最终错误消息：
{
    "type": "assistant",
    "message": {
        "content": [
            {
                "type": "text",
                "text": "Failed to authenticate. API Error: 401 Invalid API Key"
            }
        ]
    },
    "error": "authentication_failed"
}

结果消息：
{
    "type": "result",
    "subtype": "success",
    "is_error": true,
    "api_error_status": 401,
    "duration_ms": 182304,
    "num_turns": 1,
    "result": "Failed to authenticate. API Error: 401 Invalid API Key",
    "permission_denials": [],
    "terminal_reason": "completed"
}

try/except 捕获结果: ❌ 未触发任何异常
返回码捕获结果: ✅ 返回码为 1（非零，可检测）
JSON 解析结果: ✅ is_error=true, api_error_status=401

===============================================================================
"""

import asyncio
import os
import shutil
from pathlib import Path

# 测试配置目录
CLAUDE_HOME = Path(__file__).parent / "claude_home"


async def run_claude_cli(prompt: str, config_dir: Path, description: str) -> dict:
    """
    使用 asyncio.create_subprocess_exec 调用 Claude CLI

    Returns:
        dict: 包含 stdout, stderr, returncode, exception
    """
    cmd = [
        "claude",
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        prompt,
    ]

    # 构建环境变量 - CLAUDE_CONFIG_DIR 指向包含 settings.json 的目录
    env = os.environ.copy()
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)

    result = {
        "description": description,
        "stdout": [],
        "stderr": [],
        "returncode": None,
        "exception": None,
    }

    print(f"\n{'=' * 60}")
    print(f"测试: {description}")
    print(f"命令: {' '.join(cmd)}")
    print(f"配置目录: {config_dir}")
    print(f"{'=' * 60}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
        )

        # 读取 stdout
        async for line in process.stdout:
            decoded = line.decode("utf-8").strip()
            if decoded:
                result["stdout"].append(decoded)
                print(f"[stdout] {decoded}")

        # 等待进程结束
        await process.wait()
        result["returncode"] = process.returncode

        # 读取 stderr
        stderr_data = await process.stderr.read()
        stderr_text = stderr_data.decode("utf-8").strip()
        if stderr_text:
            result["stderr"].append(stderr_text)
            print(f"[stderr] {stderr_text}")

        print(f"\n[returncode] {process.returncode}")

    except FileNotFoundError as e:
        result["exception"] = f"FileNotFoundError: {e}"
        print(f"\n[exception] FileNotFoundError: {e}")
    except Exception as e:
        result["exception"] = f"{type(e).__name__}: {e}"
        print(f"\n[exception] {type(e).__name__}: {e}")

    return result


async def test_permission_error():
    """
    测试 1: Claude 内部权限错误

    使用正确的 API key，但让 Claude 执行一个被 deny 列表阻止的命令
    settings.json 中 deny 列表包含: Bash(git log)
    git log 是安全命令，模型会尝试执行，但会被 CLI 权限系统阻止

    注意：必须明确要求使用 Bash 工具，否则 Claude 可能选择 PowerShell
    """
    prompt = "请使用 Bash 工具执行 git log 命令查看最近的提交记录，不要使用 PowerShell"
    result = await run_claude_cli(
        prompt=prompt,
        config_dir=CLAUDE_HOME,  # 指向包含 settings.json 的目录
        description="权限错误测试 - 尝试执行被 deny 的 git log 命令",
    )
    return result


async def test_api_error():
    """
    测试 2: API 错误

    使用错误的 API key（settings copy.json 中的截断 key）
    需要临时替换 settings.json 以使用错误的配置
    """
    settings_path = CLAUDE_HOME / "settings.json"
    settings_backup = CLAUDE_HOME / "settings_backup.json"
    settings_wrong = CLAUDE_HOME / "settings copy.json"

    # 备份原始 settings.json
    if settings_path.exists():
        shutil.copy2(settings_path, settings_backup)

    try:
        # 使用错误的 API key 配置
        shutil.copy2(settings_wrong, settings_path)

        prompt = "你好，请回复一句话"
        result = await run_claude_cli(
            prompt=prompt, config_dir=CLAUDE_HOME, description="API 错误测试 - 使用错误的 API key"
        )
    finally:
        # 恢复原始 settings.json
        if settings_backup.exists():
            shutil.copy2(settings_backup, settings_path)
            settings_backup.unlink()

    return result


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("Claude CLI 错误处理测试")
    print("=" * 60)

    # 测试 1: 权限错误
    print("\n" + "=" * 60)
    print("测试 1: 权限错误测试")
    print("=" * 60)
    permission_result = await test_permission_error()

    # 测试 2: API 错误
    print("\n" + "=" * 60)
    print("测试 2: API 错误测试")
    print("=" * 60)
    api_result = await test_api_error()

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for result in [permission_result, api_result]:
        print(f"\n测试: {result['description']}")
        print(f"  - 返回码: {result['returncode']}")
        print(f"  - stdout 行数: {len(result['stdout'])}")
        print(f"  - stderr 行数: {len(result['stderr'])}")
        print(f"  - 异常: {result['exception'] or '无'}")

        # 分析错误是否被静默
        import json

        # 检查 JSON 输出中的错误标志
        has_is_error = False
        has_api_error = False
        has_permission_denial = False
        error_details = []

        for line in result["stdout"]:
            try:
                data = json.loads(line)
                # 检查 result 类型的消息
                if data.get("type") == "result":
                    if data.get("is_error"):
                        has_is_error = True
                        error_details.append(f"is_error=true, result={data.get('result')}")
                    if data.get("api_error_status"):
                        has_api_error = True
                        error_details.append(f"api_error_status={data.get('api_error_status')}")
                # 检查 system 类型的 api_retry
                if data.get("type") == "system" and data.get("subtype") == "api_retry":
                    has_api_error = True
                    error_details.append(f"api_retry: {data.get('error')}")
                # 检查 permission_denials
                if data.get("type") == "result" and data.get("permission_denials"):
                    has_permission_denial = True
                    error_details.append(f"permission_denials={data.get('permission_denials')}")
            except json.JSONDecodeError:
                pass

        has_error_in_stderr = any(
            "error" in line.lower() or "permission" in line.lower() or "denied" in line.lower()
            for line in result["stderr"]
        )

        print(f"\n  [详细分析]")
        print(f"  - is_error 标志: {has_is_error}")
        print(f"  - API 错误: {has_api_error}")
        print(f"  - 权限拒绝: {has_permission_denial}")
        if error_details:
            print(f"  - 错误详情: {error_details}")

        if result["returncode"] != 0:
            print(f"\n  [结论] 进程返回非零码 ({result['returncode']}), 错误可通过返回码捕获")
        elif has_is_error or has_api_error or has_permission_denial:
            print(f"\n  [结论] 错误信息在 JSON 输出中, 可通过解析 stdout 捕获")
        elif has_error_in_stderr:
            print(f"\n  [结论] 错误信息在 stderr 中")
        elif result["exception"]:
            print(f"\n  [结论] 异常被捕获: {result['exception']}")
        else:
            print(f"\n  [结论] ⚠️ 错误可能被静默处理, stdout/stderr/returncode 均无明显错误标志")


if __name__ == "__main__":
    asyncio.run(main())
