"""直接调用 Codex CLI 测试，不通过 AgentBridge"""

import subprocess
import json


def test_direct_codex_call():
    """直接调用 codex exec 命令"""

    prompt = """请总结以下对话内容，并以 JSON 格式输出。对话内容：[Leader]: 你好！我是你的AI助手，将协助你指挥小李、小赵和小王三位团队成员，高效完成你分配的各项任务。[小李]: 你好！我是这个多智能体团队中的一名AI助手，主要负责协助团队成员进行软件开发、代码维护和技术研究等工作。[小赵]: 我会先加载会话要求的基础技能说明，确认本轮应遵守的工作方式。我是 Codex，负责在当前 workspace 里协助团队完成代码、文档和工程验证工作，会遵守 Leader 的安排并和小李、小王协同推进任务。[小王]: 你好！我是AI编程助手，擅长代码编写、调试和架构设计，由Leader直接指导工作，随时准备为团队提供技术支持。[Leader]: 大家好！我们接到一个新项目：开发一个电商平台的用户管理系统。这个系统需要支持用户注册、登录、个人信息管理、订单历史查询等功能。预计开发周期是3周。[Leader]: 小李，你负责前端部分，需要设计用户友好的界面。小赵，你负责后端API和数据库设计。小王，你负责制定测试计划和执行测试。大家有什么问题吗？[小李]: 收到！我有几个问题：1. 这个系统需要支持移动端吗？2. UI设计风格有什么要求？3. 需要支持第三方登录（如微信、支付宝）吗？[小赵]: 我也有一些技术问题：1. 用户量预期是多少？这关系到数据库设计。2. 需要支持分布式部署吗？3. 对于用户密码，我们使用什么加密方式？参与者及其职责：Leader-团队领导负责任务分配进度跟踪和技术决策，小李-负责前端开发和UI设计擅长React和Vue框架，小赵-负责后端开发和数据库设计擅长Python和PostgreSQL，小王-负责测试和质量保证擅长自动化测试和性能优化。请输出 JSON 格式，包含 summary 字段（对整体对话的简短总结1到2句话）和 agent_specific 字段（为每个参与者提取与其职责最相关的信息2到3句话），只输出 JSON 不要有其他文字。"""

    print("=" * 70)
    print("测试1: 直接调用 codex exec（不设置 CODEX_HOME）")
    print("=" * 70)

    # 获取 codex 完整路径
    from pathlib import Path

    codex_path = Path.home() / "AppData/Roaming/npm/codex.cmd"

    # 直接调用，不设置 CODEX_HOME
    result = subprocess.run(
        [str(codex_path), "exec", "--json", prompt],
        capture_output=True,
        text=True,
        cwd="D:/desktop/软件开发/agents-hub",
        shell=True,
        encoding="utf-8",
        errors="ignore",
    )

    print(f"返回码: {result.returncode}")
    print(f"stdout 长度: {len(result.stdout)}")
    print(f"stderr: {result.stderr}")

    # 解析 JSONL 输出
    lines = result.stdout.strip().split("\n")
    for line in lines:
        if line.strip():
            try:
                event = json.loads(line)
                if (
                    event.get("type") == "item.completed"
                    and event.get("item", {}).get("type") == "agent_message"
                ):
                    print("\n提取的 agent_message:")
                    print(event["item"]["text"])
            except json.JSONDecodeError:
                pass

    print("\n" + "=" * 70)
    print("测试2: 设置 CODEX_HOME 到测试目录（包含配置）")
    print("=" * 70)

    # 设置 CODEX_HOME 到包含配置的目录
    import os

    env = os.environ.copy()
    env["CODEX_HOME"] = (
        "D:/desktop/软件开发/agents-hub/tests/explore/多agent架构/local_data/codex_home"
    )

    result2 = subprocess.run(
        [str(codex_path), "exec", "--json", prompt],
        capture_output=True,
        text=True,
        cwd="D:/desktop/软件开发/agents-hub",
        env=env,
        shell=True,
        encoding="utf-8",
        errors="ignore",
    )

    print(f"返回码: {result2.returncode}")
    print(f"stdout 长度: {len(result2.stdout)}")
    print(f"stderr: {result2.stderr}")

    # 解析 JSONL 输出
    lines2 = result2.stdout.strip().split("\n")
    for line in lines2:
        if line.strip():
            try:
                event = json.loads(line)
                if (
                    event.get("type") == "item.completed"
                    and event.get("item", {}).get("type") == "agent_message"
                ):
                    print("\n提取的 agent_message:")
                    print(event["item"]["text"])
            except json.JSONDecodeError:
                pass


if __name__ == "__main__":
    test_direct_codex_call()
