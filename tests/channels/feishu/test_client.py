"""FeishuClient 客户端测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.channels.feishu.client import FeishuClient
from agents_hub.channels.feishu.config import FeishuConfig
from agents_hub.channels.feishu.exceptions import FeishuAPIError, FeishuAuthError


@pytest.fixture
def config():
    return FeishuConfig(app_id="test_id", app_secret="test_secret")


def test_client_init(config):
    """客户端初始化不抛异常"""
    client = FeishuClient(config)

    assert client.config is config
    assert client._client is None


@pytest.mark.asyncio
async def test_client_connect_sets_client(config):
    """connect() 初始化 lark 客户端"""
    mock_lark = MagicMock()
    mock_builder = MagicMock()
    mock_client = MagicMock()

    mock_lark.Client.builder.return_value = mock_builder
    mock_builder.app_id.return_value = mock_builder
    mock_builder.app_secret.return_value = mock_builder
    mock_builder.domain.return_value = mock_builder
    mock_builder.build.return_value = mock_client

    with patch("agents_hub.channels.feishu.client._load_lark", return_value=(mock_lark, "https://open.feishu.cn", "https://open.larksuite.com")):
        client = FeishuClient(config)
        await client.connect()

    assert client._client is mock_client


@pytest.mark.asyncio
async def test_client_disconnect_clears_client(config):
    """disconnect() 清理客户端"""
    mock_lark = MagicMock()
    mock_builder = MagicMock()
    mock_builder.app_id.return_value = mock_builder
    mock_builder.app_secret.return_value = mock_builder
    mock_builder.domain.return_value = mock_builder
    mock_builder.build.return_value = MagicMock()
    mock_lark.Client.builder.return_value = mock_builder

    with patch("agents_hub.channels.feishu.client._load_lark", return_value=(mock_lark, "https://open.feishu.cn", "https://open.larksuite.com")):
        client = FeishuClient(config)
        await client.connect()
        assert client._client is not None

        await client.disconnect()
        assert client._client is None


@pytest.mark.asyncio
async def test_client_send_message_raises_if_not_connected(config):
    """未连接时发送消息抛异常"""
    client = FeishuClient(config)

    with pytest.raises(RuntimeError, match="not connected"):
        await client.send_message("oc_xxx", "hello")


@pytest.mark.asyncio
async def test_client_send_message_success(config):
    """成功发送消息"""
    mock_lark = MagicMock()
    mock_builder = MagicMock()
    mock_client_instance = MagicMock()

    mock_lark.Client.builder.return_value = mock_builder
    mock_builder.app_id.return_value = mock_builder
    mock_builder.app_secret.return_value = mock_builder
    mock_builder.domain.return_value = mock_builder
    mock_builder.build.return_value = mock_client_instance

    # 模拟 API 响应成功
    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data = MagicMock()
    mock_response.data.message_id = "msg_123"
    mock_client_instance.im.v1.message.create.return_value = mock_response

    with patch("agents_hub.channels.feishu.client._load_lark", return_value=(mock_lark, "https://open.feishu.cn", "https://open.larksuite.com")):
        client = FeishuClient(config)
        await client.connect()

        async def fake_run_in_executor(executor, fn):
            return fn()

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = fake_run_in_executor
            result = await client.send_message("oc_xxx", '{"text":"hello"}')

    assert result["message_id"] == "msg_123"


@pytest.mark.asyncio
async def test_client_send_message_api_error(config):
    """API 返回错误时抛 FeishuAPIError"""
    mock_lark = MagicMock()
    mock_builder = MagicMock()
    mock_client_instance = MagicMock()

    mock_lark.Client.builder.return_value = mock_builder
    mock_builder.app_id.return_value = mock_builder
    mock_builder.app_secret.return_value = mock_builder
    mock_builder.domain.return_value = mock_builder
    mock_builder.build.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.success.return_value = False
    mock_response.code = 99991668
    mock_response.msg = "invalid param"
    mock_client_instance.im.v1.message.create.return_value = mock_response

    with patch("agents_hub.channels.feishu.client._load_lark", return_value=(mock_lark, "https://open.feishu.cn", "https://open.larksuite.com")):
        client = FeishuClient(config)
        await client.connect()

        async def fake_run_in_executor(executor, fn):
            return fn()

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = fake_run_in_executor
            with pytest.raises(FeishuAPIError):
                await client.send_message("oc_xxx", "hello")


@pytest.mark.asyncio
async def test_client_send_message_auth_error(config):
    """认证失败时抛 FeishuAuthError"""
    mock_lark = MagicMock()
    mock_builder = MagicMock()
    mock_client_instance = MagicMock()

    mock_lark.Client.builder.return_value = mock_builder
    mock_builder.app_id.return_value = mock_builder
    mock_builder.app_secret.return_value = mock_builder
    mock_builder.domain.return_value = mock_builder
    mock_builder.build.return_value = mock_client_instance

    mock_response = MagicMock()
    mock_response.success.return_value = False
    mock_response.code = 99991663
    mock_response.msg = "auth failed"
    mock_client_instance.im.v1.message.create.return_value = mock_response

    with patch("agents_hub.channels.feishu.client._load_lark", return_value=(mock_lark, "https://open.feishu.cn", "https://open.larksuite.com")):
        client = FeishuClient(config)
        await client.connect()

        async def fake_run_in_executor(executor, fn):
            return fn()

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = fake_run_in_executor
            with pytest.raises(FeishuAuthError):
                await client.send_message("oc_xxx", "hello")
