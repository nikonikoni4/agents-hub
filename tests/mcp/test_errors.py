"""
MCP 错误响应工具测试

契约驱动测试：
- make_error_response(): 生成统一格式的错误响应
- 9 个错误码常量
"""

from agents_hub.mcp.errors import (
    AGENT_CALL_NOT_FOUND,
    AGENT_NOT_FOUND,
    AGENT_OFFLINE,
    GROUP_CHAT_NOT_FOUND,
    INTERNAL_ERROR,
    INVALID_AGENT_CALL_STATE,
    INVALID_TASK_FORMAT,
    INVALID_TOKEN,
    PERMISSION_DENIED,
    TASK_LIST_NOT_FOUND,
    make_error_response,
)

# ============================================================================
# 错误码常量测试
# ============================================================================


def test_all_error_codes_exist() -> None:
    """
    契约：所有 10 个错误码常量存在且值正确

    验证方式：
    1. 验证每个错误码常量的值

    如果失败，说明：错误码定义缺失或值变更
    """
    assert INVALID_TOKEN == "INVALID_TOKEN"
    assert PERMISSION_DENIED == "PERMISSION_DENIED"
    assert GROUP_CHAT_NOT_FOUND == "GROUP_CHAT_NOT_FOUND"
    assert AGENT_NOT_FOUND == "AGENT_NOT_FOUND"
    assert TASK_LIST_NOT_FOUND == "TASK_LIST_NOT_FOUND"
    assert AGENT_CALL_NOT_FOUND == "AGENT_CALL_NOT_FOUND"
    assert INVALID_AGENT_CALL_STATE == "INVALID_AGENT_CALL_STATE"
    assert INVALID_TASK_FORMAT == "INVALID_TASK_FORMAT"
    assert AGENT_OFFLINE == "AGENT_OFFLINE"
    assert INTERNAL_ERROR == "INTERNAL_ERROR"


def test_error_codes_count() -> None:
    """
    契约：恰好有 10 个错误码常量

    验证方式：
    1. 导入所有错误码
    2. 验证数量

    如果失败，说明：错误码数量变更
    """
    error_codes = [
        INVALID_TOKEN,
        PERMISSION_DENIED,
        GROUP_CHAT_NOT_FOUND,
        AGENT_NOT_FOUND,
        TASK_LIST_NOT_FOUND,
        AGENT_CALL_NOT_FOUND,
        INVALID_AGENT_CALL_STATE,
        INVALID_TASK_FORMAT,
        AGENT_OFFLINE,
        INTERNAL_ERROR,
    ]
    assert len(error_codes) == 10, f"应有 10 个错误码，实际: {len(error_codes)}"


# ============================================================================
# make_error_response() 测试
# ============================================================================


def test_basic_error_response() -> None:
    """
    契约：基本错误响应格式正确

    验证方式：
    1. 调用 make_error_response(code, message)
    2. 验证返回 {"error": {"code": "...", "message": "..."}}
    3. 验证不包含 details 字段

    如果失败，说明：基本格式错误
    """
    response = make_error_response(code=INVALID_TOKEN, message="身份令牌无效或已过期")
    assert "error" in response
    assert response["error"]["code"] == "INVALID_TOKEN"
    assert response["error"]["message"] == "身份令牌无效或已过期"
    assert "details" not in response["error"]


def test_error_response_with_details() -> None:
    """
    契约：包含 details 时正确返回

    验证方式：
    1. 调用 make_error_response(code, message, details={...})
    2. 验证 details 字段存在且正确

    如果失败，说明：details 处理逻辑错误
    """
    details = {"token": "abc123", "reason": "expired"}
    response = make_error_response(code=PERMISSION_DENIED, message="权限不足", details=details)
    assert "error" in response
    assert response["error"]["code"] == "PERMISSION_DENIED"
    assert response["error"]["message"] == "权限不足"
    assert response["error"]["details"] == details


def test_error_response_with_none_details() -> None:
    """
    契约：details 为 None 时不包含 details 字段

    验证方式：
    1. 调用 make_error_response(code, message, details=None)
    2. 验证 "details" not in response["error"]

    如果失败，说明：None 处理逻辑错误
    """
    response = make_error_response(code=INTERNAL_ERROR, message="内部错误", details=None)
    assert "error" in response
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert "details" not in response["error"]


def test_error_response_with_empty_details() -> None:
    """
    契约：details 为空字典时包含 details: {}

    验证方式：
    1. 调用 make_error_response(code, message, details={})
    2. 验证 details 字段存在且为空字典

    如果失败，说明：空字典处理逻辑错误
    """
    response = make_error_response(code=AGENT_NOT_FOUND, message="Agent 不存在", details={})
    assert "error" in response
    assert response["error"]["code"] == "AGENT_NOT_FOUND"
    assert response["error"]["details"] == {}


def test_error_response_complex_details() -> None:
    """
    契约：复杂嵌套 details 正确返回

    验证方式：
    1. 准备包含嵌套结构的 details
    2. 调用 make_error_response()
    3. 验证嵌套结构完整

    如果失败，说明：深拷贝或引用处理错误
    """
    details = {
        "agent_id": "agent_123",
        "available_agents": ["agent_1", "agent_2"],
        "metadata": {"timestamp": "2026-05-31T10:00:00Z", "request_id": "req_456"},
    }
    response = make_error_response(code=AGENT_NOT_FOUND, message="Agent 不存在", details=details)
    assert response["error"]["details"] == details
    assert response["error"]["details"]["metadata"]["timestamp"] == "2026-05-31T10:00:00Z"


def test_all_error_codes_can_be_used() -> None:
    """
    契约：所有错误码都可以正常使用

    验证方式：
    1. 遍历所有错误码
    2. 调用 make_error_response()
    3. 验证返回正确

    如果失败，说明：某个错误码处理异常
    """
    error_codes = [
        INVALID_TOKEN,
        PERMISSION_DENIED,
        GROUP_CHAT_NOT_FOUND,
        AGENT_NOT_FOUND,
        TASK_LIST_NOT_FOUND,
        AGENT_CALL_NOT_FOUND,
        INVALID_AGENT_CALL_STATE,
        INVALID_TASK_FORMAT,
        AGENT_OFFLINE,
        INTERNAL_ERROR,
    ]

    for code in error_codes:
        response = make_error_response(code=code, message=f"测试 {code}")
        assert response["error"]["code"] == code
        assert response["error"]["message"] == f"测试 {code}"
