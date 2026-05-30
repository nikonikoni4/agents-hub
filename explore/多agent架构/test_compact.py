"""测试 GroupChatContext 的消息压缩机制"""
import asyncio
from team import Team, GroupChat, GroupChatType
from agents_hub.roles import RoleManager
from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.roles.models import RoleType


async def test_compact():
    """测试消息压缩功能"""
    # 1. 初始化角色
    role_manager = RoleManager()

    # 创建带有描述的角色
    role_manager.create_role(
        "小李",
        AgentPlatform.CLAUDE,
        type=RoleType.TEAM_MEMBER,
        description="负责前端开发和UI设计"
    )
    role_manager.create_role(
        "小赵",
        AgentPlatform.CODEX,
        type=RoleType.TEAM_MEMBER,
        description="负责后端开发和数据库设计"
    )
    role_manager.create_role(
        "Leader",
        AgentPlatform.CLAUDE,
        type=RoleType.LEADER,
        description="团队领导，负责任务分配和协调"
    )

    # 2. 创建团队和群聊
    team_member_list = ["小李", "小赵"]
    team = Team(team_name="测试", team_members_name=team_member_list)
    group_chat = GroupChat(
        team,
        GroupChatType.MANAGER_ORCHESTRATE,
        project_path='D:/desktop/软件开发/agents-hub'
    )

    # 3. 启动群聊（会生成初始消息）
    await group_chat.start()

    print("=" * 50)
    print("群聊启动完成，查看初始消息：")
    print(f"消息数量: {len(group_chat.group_chat_context.group_chat_session.messages)}")
    for msg in group_chat.group_chat_context.group_chat_session.messages:
        print(f"[{msg['agent_name']}]: {msg['content'][:50]}...")

    # 4. 第一次尝试压缩（token 数量可能不足 1000）
    print("\n" + "=" * 50)
    print("第一次尝试压缩...")
    await group_chat.compact_history()

    # 5. 模拟添加更多消息（如果需要测试压缩）
    print("\n" + "=" * 50)
    print("添加更多测试消息...")

    # 手动添加一些测试消息
    from agents_hub.agent_bridge.models import AgentResult
    from datetime import datetime

    test_messages = [
        AgentResult(
            agent_name="Leader",
            text="我们需要开发一个新的用户管理系统，小李负责前端界面，小赵负责后端API。",
            session_id="test_session_1",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.LEADER,
            timestamp=datetime.now().isoformat()
        ),
        AgentResult(
            agent_name="小李",
            text="收到！我会设计一个简洁美观的用户界面，包括登录、注册和用户列表页面。",
            session_id="test_session_2",
            platform=AgentPlatform.CLAUDE,
            role_type=RoleType.TEAM_MEMBER,
            timestamp=datetime.now().isoformat()
        ),
        AgentResult(
            agent_name="小赵",
            text="明白！我会设计RESTful API，包括用户CRUD操作和身份验证接口。",
            session_id="test_session_3",
            platform=AgentPlatform.CODEX,
            role_type=RoleType.TEAM_MEMBER,
            timestamp=datetime.now().isoformat()
        ),
    ]

    for msg in test_messages:
        group_chat.group_chat_context.group_chat_session.add_message(msg)

    group_chat.group_chat_context.save_group_chat_session()

    print(f"当前消息数量: {len(group_chat.group_chat_context.group_chat_session.messages)}")

    # 6. 第二次尝试压缩
    print("\n" + "=" * 50)
    print("第二次尝试压缩...")
    await group_chat.compact_history()

    # 7. 查看压缩历史
    print("\n" + "=" * 50)
    print("查看压缩历史：")
    compact_history = group_chat.group_chat_context.load_compact_history()

    if compact_history:
        for i, record in enumerate(compact_history):
            print(f"\n压缩记录 {i + 1}:")
            print(f"时间: {record['create_at']}")
            print(f"总体摘要: {record['content']['summary']}")
            for agent_name in ["Leader", "小李", "小赵"]:
                if agent_name in record['content']:
                    print(f"{agent_name} 专属信息: {record['content'][agent_name]}")
    else:
        print("暂无压缩记录（消息 token 数量可能未达到阈值 1000）")

    # 8. 获取各个 agent 的上下文
    print("\n" + "=" * 50)
    print("获取各个 agent 的上下文：")
    for agent_name in ["Leader", "小李", "小赵"]:
        print(f"\n{agent_name} 的上下文:")
        context = group_chat.get_agent_context(agent_name)
        print(context)

    # 9. 验证 last_compacted_loc 更新
    print("\n" + "=" * 50)
    print(f"last_compacted_loc: {group_chat.group_chat_context.group_chat_session.last_compacted_loc}")
    print(f"总消息数: {len(group_chat.group_chat_context.group_chat_session.messages)}")


if __name__ == "__main__":
    asyncio.run(test_compact())
