"""E2E API 测试共享配置

使用方式：
1. 启动服务器：uvicorn agents_hub.api.app:app --port 8000
2. 运行测试：pytest tests/e2e/api/ -v
3. 自定义地址：E2E_BASE_URL=http://localhost:9000 pytest tests/e2e/api/ -v
"""

import os

import pytest
import requests

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")
API_PREFIX = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="session")
def base_url():
    return API_PREFIX


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.timeout = 10
    return s


@pytest.fixture()
def api(session, base_url):
    """提供一个绑定好 base_url 的 requests session 便捷对象"""

    class Api:
        def __init__(self):
            self.session = session
            self.base = base_url

        def get(self, path, **kw):
            return self.session.get(f"{self.base}{path}", **kw)

        def post(self, path, **kw):
            return self.session.post(f"{self.base}{path}", **kw)

        def patch(self, path, **kw):
            return self.session.patch(f"{self.base}{path}", **kw)

        def put(self, path, **kw):
            return self.session.put(f"{self.base}{path}", **kw)

        def delete(self, path, **kw):
            return self.session.delete(f"{self.base}{path}", **kw)

    return Api()
