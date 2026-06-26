"""飞书异常类测试"""

from agents_hub.channels.feishu.exceptions import FeishuAPIError, FeishuAuthError, FeishuConnectionError, FeishuError
from agents_hub.exceptions import AgentsHubError, ExternalServiceError


def test_feishu_error_inherits_external_service_error():
    """FeishuError 继承 ExternalServiceError"""
    assert issubclass(FeishuError, ExternalServiceError)
    assert issubclass(FeishuError, AgentsHubError)


def test_feishu_auth_error_inherits_feishu_error():
    """FeishuAuthError 继承 FeishuError"""
    assert issubclass(FeishuAuthError, FeishuError)


def test_feishu_api_error_inherits_feishu_error():
    """FeishuAPIError 继承 FeishuError"""
    assert issubclass(FeishuAPIError, FeishuError)


def test_feishu_connection_error_inherits_feishu_error():
    """FeishuConnectionError 继承 FeishuError"""
    assert issubclass(FeishuConnectionError, FeishuError)


def test_feishu_error_carry_details():
    """异常携带上下文信息"""
    error = FeishuError(
        message="测试错误",
        error_code="FEISHU_TEST",
        details={"chat_id": "oc_xxx"},
    )

    assert error.message == "测试错误"
    assert error.error_code == "FEISHU_TEST"
    assert error.details == {"chat_id": "oc_xxx"}


def test_feishu_error_to_dict():
    """异常可转换为字典"""
    error = FeishuAPIError(message="API 错误", details={"code": 99991663})
    d = error.to_dict()

    assert d["error_code"] == "FeishuAPIError"
    assert d["message"] == "API 错误"
    assert d["details"] == {"code": 99991663}
    assert d["type"] == "FeishuAPIError"
