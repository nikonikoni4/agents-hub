"""
MCP 错误响应工具测试
"""
import pytest
from agents_hub.mcp.errors import (
    # 错误码常量
    INVALID_TOKEN,
    PERMISSION_DENIED,
    GROUP_CHAT_NOT_FOUND,
    AGENT_NOT_FOUND,
    TASK_LIST_NOT_FOUND,
    AGENT_CALL_NOT_FOUND,
    INVALID_TASK_FORMAT,
    AGENT_OFFLINE,
    INTERNAL_ERROR,
    # 错误响应函数
    make_error_response,
)


class TestErrorCodes:
    """测试错误码常量"""

    def test_all_error_codes_exist(self):
        """测试所有 9 个错误码常量存在"""
        assert INVALID_TOKEN == "INVALID_TOKEN"
        assert PERMISSION_DENIED == "PERMISSION_DENIED"
        assert GROUP_CHAT_NOT_FOUND == "GROUP_CHAT_NOT_FOUND"
        assert AGENT_NOT_FOUND == "AGENT_NOT_FOUND"
        assert TASK_LIST_NOT_FOUND == "TASK_LIST_NOT_FOUND"
        assert AGENT_CALL_NOT_FOUND == "AGENT_CALL_NOT_FOUND"
        assert INVALID_TASK_FORMAT == "INVALID_TASK_FORMAT"
        assert AGENT_OFFLINE == "AGENT_OFFLINE"
        assert INTERNAL_ERROR == "INTERNAL_ERROR"


class TestMakeErrorResponse:
    """测试 make_error_response 函数"""

    def test_basic_error_response(self):
        """测试基本错误响应格式"""
        response = make_error_response(
            code=INVALID_TOKEN,
            message="身份令牌无效或已过期"
        )

        assert "error" in response
        assert response["error"]["code"] == "INVALID_TOKEN"
        assert response["error"]["message"] == "身份令牌无效或已过期"
        assert "details" not in response["error"]

    def test_error_response_with_details(self):
        """测试包含 details 的错误响应"""
        details = {
            "token": "abc123",
            "reason": "expired"
        }
        response = make_error_response(
            code=PERMISSION_DENIED,
            message="权限不足",
            details=details
        )

        assert "error" in response
        assert response["error"]["code"] == "PERMISSION_DENIED"
        assert response["error"]["message"] == "权限不足"
        assert response["error"]["details"] == details

    def test_error_response_with_empty_details(self):
        """测试 details 为空字典的情况"""
        response = make_error_response(
            code=AGENT_NOT_FOUND,
            message="Agent 不存在",
            details={}
        )

        assert "error" in response
        assert response["error"]["code"] == "AGENT_NOT_FOUND"
        assert response["error"]["message"] == "Agent 不存在"
        assert response["error"]["details"] == {}

    def test_error_response_with_none_details(self):
        """测试 details 为 None 的情况（不包含 details 字段）"""
        response = make_error_response(
            code=INTERNAL_ERROR,
            message="内部错误",
            details=None
        )

        assert "error" in response
        assert response["error"]["code"] == "INTERNAL_ERROR"
        assert response["error"]["message"] == "内部错误"
        assert "details" not in response["error"]

    def test_all_error_codes_can_be_used(self):
        """测试所有错误码都可以正常使用"""
        error_codes = [
            INVALID_TOKEN,
            PERMISSION_DENIED,
            GROUP_CHAT_NOT_FOUND,
            AGENT_NOT_FOUND,
            TASK_LIST_NOT_FOUND,
            AGENT_CALL_NOT_FOUND,
            INVALID_TASK_FORMAT,
            AGENT_OFFLINE,
            INTERNAL_ERROR,
        ]

        for code in error_codes:
            response = make_error_response(code=code, message=f"测试 {code}")
            assert response["error"]["code"] == code
            assert response["error"]["message"] == f"测试 {code}"

    def test_error_response_with_complex_details(self):
        """测试包含复杂 details 的错误响应"""
        details = {
            "agent_id": "agent_123",
            "available_agents": ["agent_1", "agent_2"],
            "metadata": {
                "timestamp": "2026-05-31T10:00:00Z",
                "request_id": "req_456"
            }
        }
        response = make_error_response(
            code=AGENT_NOT_FOUND,
            message="Agent 不存在",
            details=details
        )

        assert response["error"]["details"] == details
        assert response["error"]["details"]["metadata"]["timestamp"] == "2026-05-31T10:00:00Z"
