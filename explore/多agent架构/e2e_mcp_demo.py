"""
MCP 工具系统 E2E 演示脚本

演示内容：
1. 创建群聊（Manager + 3 个 Worker）
2. 启动 MCP Server
3. 测试 MCP 工具调用

团队成员：
- Leader（Manager）：团队领导，负责任务分配
- 小李（架构师）：负责系统架构设计
- 小赵（PRD）：负责产品需求文档
- 小钱（执行和测试）：负责开发执行和测试
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents_hub.config import config
from agents_hub.config.types import AgentPlatform
from agents_hub.core.foundation import GroupChatType
from agents_hub.core.orchestration import GroupChat, group_chat_manager
from agents_hub.core.orchestration.team import Team
from agents_hub.mcp.server import (
    archive_task_list,
    assign_tasks_to_team,
    call_agent,
    check_agent_call,
)
from agents_hub.roles import RoleManager
from agents_hub.utils.logger import setup_logging


# ============================================================================
# 配置
# ============================================================================

# 使用 config.data_path 作为基础路径
AGENTS_DIR = config.data_path / "agents"
PROJECT_PATH = str(config.data_path)
GROUP_CHAT_ID = "e2e_demo_chat"

# 团队成员配置
TEAM_MEMBERS = {
    # "codex_test": {
    #     "description": "团队领导，负责任务分配、进度跟踪和技术决策",
    #     "type": "leader",
    # },
    "Leader": {
        "description": "团队领导，负责任务分配、进度跟踪和技术决策",
        "type": "leader",
    },
    "小李": {
        "description": "架构师，负责系统架构设计和技术方案",
        "type": "team_member",
    },
    "小赵": {
        "description": "PRD，负责产品需求文档和需求分析",
        "type": "team_member",
    },
    "小钱": {
        "description": "执行和测试，负责开发执行和质量保证",
        "type": "team_member",
    },
}


# ============================================================================
# 辅助函数
# ============================================================================


def ensure_roles_exist():
    """确保所有团队成员的 role 存在，并更新 CLAUDE.md"""
    role_manager = RoleManager(agents_dir=AGENTS_DIR)
    existing_roles = role_manager.list_role_names()

    for role_name, member_config in TEAM_MEMBERS.items():
        if role_name not in existing_roles:
            print(f"  创建角色: {role_name}")
            role_manager.create_role(
                name=role_name,
                platform=AgentPlatform.CLAUDE,
                description=member_config["description"],
                type=member_config["type"],
            )
        else:
            print(f"  角色已存在: {role_name}")

        # 更新 CLAUDE.md 中的角色描述
        update_claude_md_identity(role_name, member_config["description"])


def update_claude_md_identity(role_name: str, description: str):
    """
    更新 CLAUDE.md 中的角色描述

    使用 <identity> 标签包装，每次只替换不重复添加。

    Args:
        role_name: 角色名称
        description: 角色描述
    """
    work_root = AGENTS_DIR / role_name / "work_root"
    claude_md_path = work_root / "CLAUDE.md"

    # 确保 work_root 目录存在
    if not work_root.exists():
        return

    # 定义标记
    start_marker = "<IDENTITY_START/>"
    end_marker = "<IDENTITY_END/>"

    # 构造新的 identity 内容
    identity_content = f"""{start_marker}
## 身份信息

你的名字：{role_name}
你的角色：{description}
{end_marker}"""

    if claude_md_path.exists():
        # 读取现有内容
        content = claude_md_path.read_text(encoding="utf-8")

        # 检查是否已存在 identity 标记
        if start_marker in content and end_marker in content:
            # 替换现有内容
            import re

            pattern = f"{re.escape(start_marker)}.*?{re.escape(end_marker)}"
            content = re.sub(pattern, identity_content, content, flags=re.DOTALL)
        else:
            # 在文件开头添加
            content = identity_content + "\n\n" + content
    else:
        # 创建新文件
        content = identity_content + "\n"

    # 写入文件
    claude_md_path.write_text(content, encoding="utf-8")
    print(f"   ✓ 已更新 {role_name} 的 CLAUDE.md")


def print_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_mcp_tool_help():
    """打印 MCP 工具使用说明"""
    print_separator("MCP 工具使用说明")
    print("""
可用的 MCP 工具：

1. call_agent - 派活给团队成员
   参数：
   - agent_token: 调用者的身份令牌
   - send_to: 目标 Agent 名称
   - content: 消息内容
   - need_response: 是否需要响应（默认 True）
   - timeout_seconds: 超时时间（默认 300 秒）

2. assign_tasks_to_team - 覆盖式更新任务列表（Leader-only）
   参数：
   - agent_token: 调用者的身份令牌
   - tasks: 任务列表 [{"task_id": "...", "owner": "...", "content": "...", "status": "..."}]

3. archive_task_list - 归档当前 ACTIVE 列表（Leader-only）
   参数：
   - agent_token: 调用者的身份令牌

4. check_agent_call - 查询 AgentCall 状态
   参数：
   - agent_token: 调用者的身份令牌
   - call_id: AgentCall ID

MCP Server 地址: http://localhost:8001/mcp
""")


# ============================================================================
# E2E 测试场景
# ============================================================================


async def test_scenario_1_token_generation(group_chat: GroupChat):
    """场景 1：验证 token 生成"""
    print_separator("场景 1：验证 token 生成")

    # 获取所有成员的 token
    tokens = {}
    for member_name in TEAM_MEMBERS:
        session = group_chat.group_chat_context.agent_member_info.get(member_name)
        if session:
            tokens[member_name] = session.token
            print(f"  {member_name}: {session.token[:20]}...")

    # 验证 token 可以解析
    print("\n验证 token 解析：")
    for member_name, token in tokens.items():
        result = group_chat_manager.resolve_token(token)
        if result:
            agent_name, gc_id = result
            print(f"  ✓ {member_name} -> agent={agent_name}, group_chat={gc_id}")
        else:
            print(f"  ✗ {member_name} token 解析失败")

    return tokens


async def test_scenario_2_call_agent(group_chat: GroupChat, tokens: dict):
    """场景 2：Manager 派活给 Worker"""
    print_separator("场景 2：Manager 派活给 Worker")

    manager_token = tokens["Leader"]

    # Manager 派活给小李（架构师）
    print("\n1. Manager 派活给小李（架构师）：")
    result = call_agent(
        agent_token=manager_token,
        send_to="小李",
        content="请设计用户认证模块的架构方案",
        need_response=True,
        timeout_seconds=60,
    )

    if "call_id" in result:
        call_id = result["call_id"]
        print(f"   ✓ 派活成功，call_id: {call_id}")

        # 查询状态
        status = check_agent_call(agent_token=manager_token, call_id=call_id)
        print(f"   ✓ 状态查询: {status.get('status', 'unknown')}")
    else:
        print(f"   ✗ 派活失败: {result}")

    # Manager 派活给小赵（PRD）
    print("\n2. Manager 派活给小赵（PRD）：")
    result = call_agent(
        agent_token=manager_token,
        send_to="小赵",
        content="请编写用户认证模块的 PRD 文档",
        need_response=False,  # 不需要响应
    )

    if "call_id" in result:
        print(f"   ✓ 派活成功，call_id: {result['call_id']}")
    else:
        print(f"   ✗ 派活失败: {result}")

    # Manager 派活给小钱（执行和测试）
    print("\n3. Manager 派活给小钱（执行和测试）：")
    result = call_agent(
        agent_token=manager_token,
        send_to="小钱",
        content="请准备用户认证模块的测试用例",
        need_response=True,
    )

    if "call_id" in result:
        print(f"   ✓ 派活成功，call_id: {result['call_id']}")
    else:
        print(f"   ✗ 派活失败: {result}")


async def test_scenario_3_assign_tasks(group_chat: GroupChat, tokens: dict):
    """场景 3：Manager 分配任务"""
    print_separator("场景 3：Manager 分配任务")

    manager_token = tokens["Leader"]

    # 分配任务
    tasks = [
        {
            "task_id": "task_001",
            "owner": "小李",
            "content": "设计用户认证架构",
            "status": "pending",
        },
        {
            "task_id": "task_002",
            "owner": "小赵",
            "content": "编写认证模块 PRD",
            "status": "pending",
        },
        {
            "task_id": "task_003",
            "owner": "小钱",
            "content": "编写认证模块测试用例",
            "status": "pending",
        },
    ]

    print("\n1. 分配任务列表：")
    result = assign_tasks_to_team(agent_token=manager_token, tasks=tasks)

    if "error" not in result:
        print(f"   ✓ 分配成功")
        print(f"   - 创建: {result.get('created', 0)} 个任务")
        print(f"   - 更新: {result.get('updated', 0)} 个任务")
        print(f"   - 不变: {result.get('unchanged', 0)} 个任务")
    else:
        print(f"   ✗ 分配失败: {result}")

    # 更新任务状态
    print("\n2. 更新任务状态：")
    tasks_update = [
        {
            "task_id": "task_001",
            "owner": "小李",
            "content": "设计用户认证架构",
            "status": "running",
        },
        {
            "task_id": "task_002",
            "owner": "小赵",
            "content": "编写认证模块 PRD",
            "status": "completed",
        },
        {
            "task_id": "task_003",
            "owner": "小钱",
            "content": "编写认证模块测试用例",
            "status": "pending",
        },
    ]

    result = assign_tasks_to_team(agent_token=manager_token, tasks=tasks_update)

    if "error" not in result:
        print(f"   ✓ 更新成功")
        print(f"   - 创建: {result.get('created', 0)} 个任务")
        print(f"   - 更新: {result.get('updated', 0)} 个任务")
        print(f"   - 不变: {result.get('unchanged', 0)} 个任务")
    else:
        print(f"   ✗ 更新失败: {result}")

    # 测试 Worker 无权分配任务
    print("\n3. 测试 Worker 权限限制：")
    worker_token = tokens["小李"]
    result = assign_tasks_to_team(
        agent_token=worker_token,
        tasks=[
            {"task_id": "task_004", "owner": "小钱", "content": "测试任务", "status": "pending"}
        ],
    )

    if "error" in result and result["error"]["code"] == "PERMISSION_DENIED":
        print(f"   ✓ 权限限制生效: {result['error']['message']}")
    else:
        print(f"   ✗ 权限限制未生效")


async def test_scenario_4_archive_tasks(group_chat: GroupChat, tokens: dict):
    """场景 4：归档任务"""
    print_separator("场景 4：归档任务")

    manager_token = tokens["Leader"]

    # 归档任务
    print("\n归档当前任务列表：")
    result = archive_task_list(agent_token=manager_token)

    if "error" not in result:
        print(f"   ✓ 归档成功")
        print(f"   - 归档任务数: {result.get('archived_count', 0)}")
        print(f"   - 归档时间: {result.get('archived_at', 'unknown')}")
    else:
        print(f"   ✗ 归档失败: {result}")

    # 测试 Worker 无权归档
    print("\n测试 Worker 权限限制：")
    worker_token = tokens["小钱"]
    result = archive_task_list(agent_token=worker_token)

    if "error" in result and result["error"]["code"] == "PERMISSION_DENIED":
        print(f"   ✓ 权限限制生效: {result['error']['message']}")
    else:
        print(f"   ✗ 权限限制未生效")


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数"""
    print_separator("MCP 工具系统 E2E 演示")

    # 打印配置信息
    print(f"\n数据路径: {config.data_path}")
    print(f"Agent 目录: {AGENTS_DIR}")

    # 1. 初始化日志
    print("\n1. 初始化日志系统...")
    setup_logging(log_dir=config.data_path / "logs")

    # 2. 确保所有 role 存在
    print("\n2. 检查并创建团队成员...")
    ensure_roles_exist()

    # 3. 创建 Team
    print("\n3. 创建 Team...")
    team = Team(team_members_name=list(TEAM_MEMBERS.keys()))
    print(f"   ✓ Team 创建成功: {team.team_members_name}")

    # 4. 创建 GroupChat
    print("\n4. 创建 GroupChat...")
    group_chat = GroupChat(
        team=team,
        group_type=GroupChatType.MANAGER_ORCHESTRATE,
        project_path=PROJECT_PATH,
        group_chat_id=GROUP_CHAT_ID,
    )
    print(f"   ✓ GroupChat 创建成功: {GROUP_CHAT_ID}")

    # 5. 启动群聊
    print("\n5. 启动群聊...")
    await group_chat.start()
    print("   ✓ 群聊启动成功")

    # 注册到 GroupChatManager
    group_chat_manager.register(GROUP_CHAT_ID, group_chat)
    print("   ✓ 已注册到 GroupChatManager")

    try:
        # 6. 运行测试场景
        tokens = await test_scenario_1_token_generation(group_chat)
        # await test_scenario_2_call_agent(group_chat, tokens)
        # await test_scenario_3_assign_tasks(group_chat, tokens)
        # await test_scenario_4_archive_tasks(group_chat, tokens)

        # 7. 打印 MCP 工具说明
        print_mcp_tool_help()

        # 8. 启动 MCP Server（保持运行）
        print_separator("启动 MCP Server")
        print("\nMCP Server 正在启动...")
        print("地址: http://localhost:8001/mcp")
        print("\n按 Ctrl+C 停止服务器\n")

        # 导入并启动 MCP
        from agents_hub.mcp.server import mcp

        # 使用 asyncio.create_task 在后台运行
        mcp_task = asyncio.create_task(mcp.run_async(transport="http", host="localhost", port=8001))

        # 保持运行
        try:
            await mcp_task
        except asyncio.CancelledError:
            print("\nMCP Server 已停止")

    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在停止...")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 清理
        print("\n清理资源...")
        await group_chat_manager.unregister(GROUP_CHAT_ID)
        print("✓ 已从 GroupChatManager 注销")


if __name__ == "__main__":
    # Windows 兼容性

    asyncio.run(main())
