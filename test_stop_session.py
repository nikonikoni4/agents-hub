"""测试 stop_session 功能的验证脚本"""

import asyncio
import sys

# 测试导入
try:
    from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
    from agents_hub.agent_bridge.executors.codex import CodexExecutor
    from agents_hub.agent_bridge.executors.opencode import OpenCodeExecutor
    from agents_hub.agent_bridge.executors.docker_base import DockerExecutor
    from agents_hub.agent_bridge.bridge import AgentBridge
    print("[OK] 所有导入成功")
except Exception as e:
    print(f"[FAIL] 导入失败: {e}")
    sys.exit(1)


def test_executor_has_stop_session():
    """测试所有 Executor 都有 stop_session 方法"""
    errors = []

    # 测试本地 Executor
    for executor_class in [ClaudeExecutor, CodexExecutor, OpenCodeExecutor]:
        executor = executor_class()
        if not hasattr(executor, "stop_session"):
            errors.append(f"{executor_class.__name__} 缺少 stop_session 方法")
        if not hasattr(executor, "_processes"):
            errors.append(f"{executor_class.__name__} 缺少 _processes 属性")
        if not hasattr(executor, "_lock"):
            errors.append(f"{executor_class.__name__} 缺少 _lock 属性")

    # 测试 DockerExecutor 基类
    from agents_hub.agent_bridge.docker.manager import DockerManager
    docker_manager = DockerManager()

    # 无法直接实例化抽象类，但可以检查方法存在
    if not hasattr(DockerExecutor, "stop_session"):
        errors.append("DockerExecutor 缺少 stop_session 方法")

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return False
    else:
        print("[OK] 所有 Executor 都有 stop_session 方法")
        return True


def test_agent_bridge_has_stop_session():
    """测试 AgentBridge 有 stop_session 方法"""
    bridge = AgentBridge()
    if not hasattr(bridge, "stop_session"):
        print("[FAIL] AgentBridge 缺少 stop_session 方法")
        return False
    else:
        print("[OK] AgentBridge 有 stop_session 方法")
        return True


def test_group_chat_has_stop_agent_process():
    """测试 GroupChat 有 _stop_agent_process 方法"""
    try:
        from agents_hub.core.orchestration.group_chat import GroupChat
        if not hasattr(GroupChat, "_stop_agent_process"):
            print("[FAIL] GroupChat 缺少 _stop_agent_process 方法")
            return False
        else:
            print("[OK] GroupChat 有 _stop_agent_process 方法")
            return True
    except Exception as e:
        print(f"[FAIL] 导入 GroupChat 失败: {e}")
        return False


async def test_stop_session_signature():
    """测试 stop_session 方法签名"""
    from agents_hub.config.types import AgentPlatform

    bridge = AgentBridge()

    # 测试方法签名（不实际调用）
    try:
        # 检查方法是否可调用
        import inspect
        sig = inspect.signature(bridge.stop_session)
        params = list(sig.parameters.keys())

        expected_params = ["platform", "session_id", "use_docker"]
        if params != expected_params:
            print(f"[FAIL] stop_session 签名错误: 期望 {expected_params}, 实际 {params}")
            return False

        print("[OK] stop_session 方法签名正确")
        return True
    except Exception as e:
        print(f"[FAIL] 检查方法签名失败: {e}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("测试 stop_session 功能实现")
    print("=" * 60)

    results = []

    # 同步测试
    results.append(("Executor 有 stop_session", test_executor_has_stop_session()))
    results.append(("AgentBridge 有 stop_session", test_agent_bridge_has_stop_session()))
    results.append(("GroupChat 有 _stop_agent_process", test_group_chat_has_stop_agent_process()))

    # 异步测试
    loop = asyncio.get_event_loop()
    results.append(("stop_session 签名正确", loop.run_until_complete(test_stop_session_signature())))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n所有测试通过！")
        return 0
    else:
        print("\n部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
