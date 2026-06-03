"""系统配置管理

管理三种路径：
1. 开发环境路径：项目根目录/local_data/
2. 打包环境默认路径：%LOCALAPPDATA%/AgentsHub/data/
3. 数据迁移路径：用户自定义路径（保存在 config.yaml）

优先级：数据迁移路径 > 打包环境默认路径 > 开发环境路径
"""

import sys
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]


class SystemConfig:
    """系统配置（单例）"""

    _instance: Optional["SystemConfig"] = None

    # 默认配置
    _default_config: dict = {
        "data_path": None,  # None 表示使用环境默认路径
        "mcp_port": 8765,  # MCP 服务器运行端口
        "default_manager_name": "manager",  # 默认 manager 角色名
        "default_user_name": "user",  # 默认用户身份名
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化配置"""
        self._is_dev = not getattr(sys, "frozen", False)
        self._config_file = self._get_config_file_path()
        self._config_data: dict = self._default_config.copy()
        self._load_config()

    def _get_config_file_path(self) -> Path:
        """获取配置文件路径（配置文件本身不迁移）"""
        if self._is_dev:
            # 开发环境：项目根目录/config/config.yaml
            return Path("local_data/config/config.yaml")
        else:
            # 打包环境：%LOCALAPPDATA%/AgentsHub/config/config.yaml
            return Path.home() / "AppData" / "Local" / "AgentsHub" / "config" / "config.yaml"

    def _load_config(self):
        """加载配置文件，从 yaml 覆盖默认值"""
        if self._config_file.exists():
            with open(self._config_file, encoding="utf-8") as f:
                saved_config = yaml.safe_load(f) or {}
                # 用保存的值覆盖默认值
                for key in self._config_data:
                    if key in saved_config and saved_config[key] is not None:
                        self._config_data[key] = saved_config[key]

    def _save_config(self):
        """保存配置文件"""
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        # 过滤掉 None 值，只保存用户明确设置的配置
        data_to_save = {k: v for k, v in self._config_data.items() if v is not None}
        with open(self._config_file, "w", encoding="utf-8") as f:
            yaml.dump(data_to_save, f, allow_unicode=True)

    @property
    def data_path(self) -> Path:
        """
        获取数据存储路径

        优先级：
        1. 用户配置的迁移路径（config.yaml 中的 data_path）
        2. 打包环境默认路径（%LOCALAPPDATA%/AgentsHub/data/）
        3. 开发环境路径（项目根目录/local_data/）

        Returns:
            Path: 数据存储路径
        """
        # 1. 用户配置的迁移路径
        user_path = self._config_data.get("data_path")
        if user_path:
            return Path(user_path)

        # 2. 打包环境默认路径
        if not self._is_dev:
            return Path.home() / "AppData" / "Local" / "AgentsHub" / "data"

        # 3. 开发环境路径
        return Path("local_data")

    def set_data_path(self, new_path: Path):
        """
        设置数据迁移路径

        Args:
            new_path: 新的数据存储路径
        """
        self._config_data["data_path"] = str(new_path)
        self._save_config()

    @property
    def mcp_port(self) -> int:
        """获取 MCP 服务器运行端口"""
        return self._config_data["mcp_port"]

    @mcp_port.setter
    def mcp_port(self, port: int):
        """设置 MCP 服务器运行端口"""
        self._config_data["mcp_port"] = port
        self._save_config()

    @property
    def default_manager_name(self) -> str:
        """默认 manager 角色名"""
        return self._config_data["default_manager_name"]

    @property
    def default_user_name(self) -> str:
        """默认用户身份名"""
        return self._config_data["default_user_name"]

    @property
    def is_dev(self) -> bool:
        """是否为开发环境"""
        return self._is_dev


class Config:
    """配置聚合类 - 统一访问所有配置

    提供单一入口访问所有配置模块，支持：
    - 完整路径访问：config.system.data_path
    - 快捷访问：config.data_path

    未来扩展示例：
    - config.agent_bridge.timeout
    - config.mcp_server.port
    """

    _instance: Optional["Config"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化所有配置模块"""
        self.system = SystemConfig()
        # 未来扩展：
        # self.agent_bridge = AgentBridgeConfig()
        # self.mcp_server = MCPServerConfig()

    # ============ 快捷访问属性 ============

    @property
    def data_path(self) -> Path:
        """快捷访问：数据存储路径"""
        return self.system.data_path

    def set_data_path(self, new_path: Path):
        """快捷访问：设置数据迁移路径"""
        self.system.set_data_path(new_path)

    @property
    def mcp_port(self) -> int:
        """快捷访问：MCP 服务器运行端口"""
        return self.system.mcp_port

    @mcp_port.setter
    def mcp_port(self, port: int):
        """快捷访问：设置 MCP 服务器运行端口"""
        self.system.mcp_port = port

    @property
    def is_dev(self) -> bool:
        """快捷访问：是否开发环境"""
        return self.system.is_dev

    @property
    def default_manager_name(self) -> str:
        """快捷访问：默认 Leader 角色名"""
        return self.system.default_manager_name

    @property
    def default_user_name(self) -> str:
        """快捷访问：默认用户身份名"""
        return self.system.default_user_name


# ============ 全局单例 ============

# 统一入口（推荐使用）
config = Config()
