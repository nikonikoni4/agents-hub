"""测试 GroupChatContext 的消息压缩机制 - 长对话版本"""

import asyncio
from team import Team, GroupChat, GroupChatType
from agents_hub.roles import RoleManager
from agents_hub.agent_bridge.models import AgentPlatform, AgentResult
from agents_hub.roles.models import RoleType
from datetime import datetime


async def test_compact_long():
    """测试消息压缩功能 - 包含大量对话"""
    # 1. 初始化角色
    role_manager = RoleManager()

    # 创建带有描述的角色
    role_manager.create_role(
        "小李",
        AgentPlatform.CLAUDE,
        type=RoleType.TEAM_MEMBER,
        description="负责前端开发和UI设计，擅长React和Vue框架",
    )
    role_manager.create_role(
        "小赵",
        AgentPlatform.CODEX,
        type=RoleType.TEAM_MEMBER,
        description="负责后端开发和数据库设计，擅长Python和PostgreSQL",
    )
    role_manager.create_role(
        "小王",
        AgentPlatform.CLAUDE,
        type=RoleType.TEAM_MEMBER,
        description="负责测试和质量保证，擅长自动化测试和性能优化",
    )
    role_manager.create_role(
        "Leader",
        AgentPlatform.CLAUDE,
        type=RoleType.LEADER,
        description="团队领导，负责任务分配、进度跟踪和技术决策",
    )

    # 2. 创建团队和群聊
    team_member_list = ["小李", "小赵", "小王"]
    team = Team(team_name="开发团队", team_members_name=team_member_list)
    group_chat = GroupChat(
        team,
        GroupChatType.MANAGER_ORCHESTRATE,
        project_path="D:/desktop/软件开发/agents-hub/tests/explore/多agent架构",
        group_chat_id="961084b7-f4b8-47d3-baed-d82b05163ed1",
    )

    # 3. 启动群聊（会生成初始消息）
    await group_chat.start()

    print("=" * 70)
    print("群聊启动完成，查看初始消息：")
    print(f"消息数量: {len(group_chat.group_chat_context.group_chat_session.messages)}")

    # 4. 模拟一个完整的项目讨论过程
    print("\n" + "=" * 70)
    print("模拟项目讨论过程，添加大量对话...")
    add_project_discussion = (
        True if group_chat.group_chat_context.group_chat_session.last_compacted_loc == 0 else False
    )
    group_chat.group_chat_context.group_chat_session.last_compacted_loc = 0
    # 项目启动阶段
    if add_project_discussion:
        project_discussion = [
            (
                "Leader",
                "大家好！我们接到一个新项目：开发一个电商平台的用户管理系统。这个系统需要支持用户注册、登录、个人信息管理、订单历史查询等功能。预计开发周期是3周。",
            ),
            (
                "Leader",
                "小李，你负责前端部分，需要设计用户友好的界面。小赵，你负责后端API和数据库设计。小王，你负责制定测试计划和执行测试。大家有什么问题吗？",
            ),
            (
                "小李",
                "收到！我有几个问题：1. 这个系统需要支持移动端吗？2. UI设计风格有什么要求？3. 需要支持第三方登录（如微信、支付宝）吗？",
            ),
            (
                "小赵",
                "我也有一些技术问题：1. 用户量预期是多少？这关系到数据库设计。2. 需要支持分布式部署吗？3. 对于用户密码，我们使用什么加密方式？",
            ),
            (
                "小王",
                "关于测试，我想确认：1. 需要做性能测试吗？并发用户数的目标是多少？2. 安全测试的范围包括哪些？3. 是否需要自动化测试覆盖率达到特定指标？",
            ),
            # Leader 回答问题
            (
                "Leader",
                "好问题！让我逐一回答。小李：1. 需要支持移动端，采用响应式设计。2. UI风格要简洁现代，参考京东和淘宝的设计。3. 第一期只支持手机号+验证码登录，第三方登录放到二期。",
            ),
            (
                "Leader",
                "小赵：1. 预期用户量是10万级别，要考虑后续扩展到百万级。2. 暂时单机部署，但架构要支持后续分布式改造。3. 密码使用bcrypt加密，加盐处理。",
            ),
            (
                "Leader",
                "小王：1. 需要做性能测试，目标是支持1000并发用户。2. 安全测试重点是SQL注入、XSS攻击、CSRF防护。3. 单元测试覆盖率要达到80%以上。",
            ),
            # 需求细化阶段
            (
                "小李",
                "明白了！那我开始设计页面原型。主要页面包括：登录页、注册页、个人中心、订单列表、订单详情。我计划使用React + Ant Design组件库，这样开发效率会比较高。",
            ),
            (
                "小赵",
                "我开始设计数据库表结构。主要包括：用户表(users)、订单表(orders)、订单详情表(order_items)、地址表(addresses)。用户表需要存储：手机号、密码哈希、昵称、头像、注册时间、最后登录时间等。",
            ),
            (
                "小王",
                "我会准备测试环境和测试数据。测试计划包括：功能测试（注册、登录、信息修改）、性能测试（并发登录、查询）、安全测试（SQL注入、XSS）、兼容性测试（不同浏览器）。",
            ),
            # 技术讨论阶段
            (
                "小李",
                "关于前端架构，我建议使用Redux进行状态管理，用户信息、订单数据都存在全局状态中。另外，我会使用React Router做路由管理，axios做HTTP请求封装。",
            ),
            (
                "小赵",
                "后端我打算用FastAPI框架，它性能好而且支持异步。API设计遵循RESTful规范：POST /api/users/register 注册，POST /api/users/login 登录，GET /api/users/profile 获取个人信息，PUT /api/users/profile 更新信息。",
            ),
            (
                "小赵",
                "关于数据库，我会使用PostgreSQL，它的JSON支持很好，后续如果需要存储用户的扩展信息会很方便。另外，我会给常用查询字段（手机号、用户ID）建立索引，提高查询性能。",
            ),
            (
                "小王",
                "我建议使用pytest做单元测试，Selenium做UI自动化测试，Locust做性能测试。另外，我会配置CI/CD流程，每次代码提交都自动运行测试。",
            ),
            # 开发进度同步
            (
                "Leader",
                "很好！大家的方案都很专业。现在我们进入开发阶段。我建议每天下午5点进行进度同步，遇到问题及时在群里讨论。",
            ),
            (
                "小李",
                "第一天进度：我已经完成了项目脚手架搭建，配置好了React + Redux + Router。登录页和注册页的UI已经完成，明天开始对接后端API。",
            ),
            (
                "小赵",
                "第一天进度：数据库表结构已经设计完成并创建。用户注册和登录的API已经开发完成，包括手机号验证、密码加密、JWT token生成。明天开始做个人信息相关的API。",
            ),
            (
                "小王",
                "第一天进度：测试环境已经搭建完成，准备了100条测试用户数据。编写了用户注册和登录的测试用例，等后端API稳定后开始执行测试。",
            ),
            # 问题讨论
            (
                "小李",
                "我在对接登录API时遇到了跨域问题，浏览器报CORS错误。小赵，你能在后端配置一下CORS吗？需要允许我本地的开发服务器地址 http://localhost:3000。",
            ),
            (
                "小赵",
                "好的，我马上配置。我会在FastAPI中添加CORS中间件，允许你的开发地址。另外，我建议生产环境只允许我们的正式域名，提高安全性。",
            ),
            (
                "小李",
                "谢谢！还有一个问题，关于token的存储，我是存在localStorage还是sessionStorage？或者用httpOnly的cookie？",
            ),
            (
                "小赵",
                "建议用httpOnly的cookie，这样可以防止XSS攻击窃取token。我会在登录接口返回时设置cookie，前端不需要手动处理token。",
            ),
            (
                "小王",
                "我在测试时发现一个问题：用户注册时，如果手机号已存在，后端返回的错误信息不够明确。建议返回具体的错误码和错误描述，方便前端展示友好的提示。",
            ),
            (
                "小赵",
                "好建议！我会统一错误响应格式：{code: 错误码, message: 错误描述, data: null}。比如手机号已存在返回 {code: 40001, message: '该手机号已注册', data: null}。",
            ),
            # 第二天进度
            (
                "小李",
                "第二天进度：登录和注册功能已经完成并测试通过。个人中心页面UI完成，正在对接个人信息查询和修改的API。遇到一个问题：用户头像上传应该怎么处理？",
            ),
            (
                "小赵",
                "第二天进度：个人信息的增删改查API已完成。关于头像上传，我建议使用对象存储服务（如阿里云OSS），前端直接上传到OSS，然后把URL保存到数据库。这样不占用我们服务器带宽。",
            ),
            (
                "Leader",
                "小赵的方案不错。不过考虑到成本，第一期我们先用本地存储，把图片存在服务器的uploads目录。后续用户量大了再迁移到OSS。",
            ),
            (
                "小赵",
                "好的，那我实现一个文件上传接口：POST /api/upload/avatar，接收multipart/form-data格式的图片，保存后返回访问URL。",
            ),
            (
                "小王",
                "第二天进度：完成了注册和登录功能的测试，发现2个bug：1. 密码长度小于6位时没有提示。2. 手机号格式验证不够严格，可以输入非数字字符。",
            ),
            (
                "小李",
                "感谢小王！我马上修复这两个问题。前端会加上实时验证，密码至少6位，手机号只能输入11位数字。",
            ),
            # 第三天进度
            (
                "小李",
                "第三天进度：个人信息页面完成，包括查看和编辑功能。头像上传功能已实现，支持预览和裁剪。订单列表页面UI完成，明天对接订单API。",
            ),
            (
                "小赵",
                "第三天进度：订单相关的API开发完成，包括订单列表查询（支持分页）、订单详情查询。添加了订单状态字段：待支付、已支付、配送中、已完成、已取消。",
            ),
            (
                "小王",
                "第三天进度：个人信息功能测试完成，发现1个bug：修改昵称时，如果包含特殊字符（如<script>）没有过滤，存在XSS风险。",
            ),
            (
                "小赵",
                "好的，我会在后端添加输入验证和HTML转义，防止XSS攻击。另外，我会限制昵称长度在2-20个字符之间，只允许中文、英文、数字和常用符号。",
            ),
            # 性能优化讨论
            (
                "小王",
                "我做了性能测试，发现订单列表查询比较慢，500个并发用户时响应时间超过2秒。小赵，能优化一下吗？",
            ),
            (
                "小赵",
                "我看一下慢查询日志。应该是订单表数据量大，而且查询时关联了用户表。我会做几个优化：1. 给订单表的user_id和create_time字段加索引。2. 使用Redis缓存热门订单数据。3. 订单列表不返回详细信息，只返回必要字段。",
            ),
            (
                "小李",
                "前端我也可以优化：1. 订单列表使用虚拟滚动，只渲染可见区域的订单。2. 图片使用懒加载。3. 添加骨架屏，提升用户体验。",
            ),
            (
                "Leader",
                "很好！性能优化要前后端配合。小王，优化后再测一次，看能不能达到1000并发的目标。",
            ),
            # 最终测试阶段
            (
                "小王",
                "经过优化，性能测试通过了！1000并发用户时，平均响应时间在500ms以内。安全测试也完成了，没有发现SQL注入和XSS漏洞。单元测试覆盖率达到85%。",
            ),
            (
                "小李",
                "前端开发已经全部完成，在Chrome、Firefox、Safari三个浏览器上测试通过。移动端适配也没问题，在iPhone和Android手机上都能正常使用。",
            ),
            (
                "小赵",
                "后端开发完成，所有API都经过测试。数据库性能优化完成，添加了必要的索引。日志系统已配置，方便后续排查问题。",
            ),
            (
                "Leader",
                "太好了！大家辛苦了。明天我们进行最终的集成测试，没问题的话就可以部署到生产环境了。这个项目大家配合得很好，按时保质完成了任务！",
            ),
        ]

        # 添加所有对话消息
        for agent_name, content in project_discussion:
            msg = AgentResult(
                agent_name=agent_name,
                text=content,
                session_id=f"test_session_{agent_name}",
                platform=AgentPlatform.CLAUDE
                if agent_name in ["Leader", "小李", "小王"]
                else AgentPlatform.CODEX,
                role_type=RoleType.LEADER if agent_name == "Leader" else RoleType.TEAM_MEMBER,
                timestamp=datetime.now().isoformat(),
            )
            group_chat.group_chat_context.group_chat_session.add_message(msg)

        group_chat.group_chat_context.save_group_chat_session()
    print(f"当前总消息数量: {len(group_chat.group_chat_context.group_chat_session.messages)}")

    # 5. 执行消息压缩
    print("\n" + "=" * 70)
    print("开始压缩消息...")
    await group_chat.compact_history()

    # 6. 查看压缩历史
    print("\n" + "=" * 70)
    print("查看压缩历史：")
    compact_history = group_chat.group_chat_context.load_compact_history()

    if compact_history:
        for i, record in enumerate(compact_history):
            print(f"\n{'=' * 70}")
            print(f"压缩记录 {i + 1}:")
            print(f"时间: {record['create_at']}")
            print(f"\n总体摘要:")
            print(f"  {record['content']['summary']}")
            print(f"\n各成员专属信息:")
            for agent_name in ["Leader", "小李", "小赵", "小王"]:
                if agent_name in record["content"]:
                    print(f"  [{agent_name}]: {record['content'][agent_name]}")
    else:
        print("暂无压缩记录")

    # 7. 获取各个 agent 的上下文
    print("\n" + "=" * 70)
    print("获取各个 agent 的上下文：")
    for agent_name in ["Leader", "小李", "小赵", "小王"]:
        print(f"\n{'=' * 70}")
        print(f"{agent_name} 的完整上下文:")
        print("-" * 70)
        context = group_chat.get_agent_context(agent_name)
        print(context)

    # 8. 验证压缩效果
    print("\n" + "=" * 70)
    print("压缩效果统计:")
    print(
        f"  last_compacted_loc: {group_chat.group_chat_context.group_chat_session.last_compacted_loc}"
    )
    print(f"  总消息数: {len(group_chat.group_chat_context.group_chat_session.messages)}")
    print(f"  已压缩消息数: {group_chat.group_chat_context.group_chat_session.last_compacted_loc}")
    print(
        f"  未压缩消息数: {len(group_chat.group_chat_context.group_chat_session.get_uncompact_messages())}"
    )


if __name__ == "__main__":
    asyncio.run(test_compact_long())
