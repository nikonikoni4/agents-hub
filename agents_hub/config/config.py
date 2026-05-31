"""系统配置管理

管理三种路径：
1. 开发环境路径：项目根目录/local_data/
2. 打包环境默认路径：%LOCALAPPDATA%/AgentsHub/data/
3. 数据迁移路径：用户自定义路径（保存在 config.yaml）

优先级：数据迁移路径 > 打包环境默认路径 > 开发环境路径
"""

import os
import sys
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]


class SystemConfig:
    """系统配置（单例）"""

    _instance: Optional["SystemConfig"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化配置"""
        self._is_dev = not getattr(sys, "frozen", False)
        self._config_file = self._get_config_file_path()
        self._user_data_path: Path | None = None
        self._load_config()

    def _get_config_file_path(self) -> Path:
        """获取配置文件路径（配置文件本身不迁移）"""
        if self._is_dev:
            # 开发环境：项目根目录/config/config.yaml
            return Path("config/config.yaml")
        else:
            # 打包环境：%LOCALAPPDATA%/AgentsHub/config/config.yaml
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if not local_app_data:
                raise RuntimeError("无法获取 LOCALAPPDATA 环境变量")
            return Path(local_app_data) / "AgentsHub" / "config" / "config.yaml"

    def _load_config(self):
        """加载配置文件"""
        if self._config_file.exists():
            with open(self._config_file, encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
                user_path = config_data.get("data_path")
                if user_path:
                    self._user_data_path = Path(user_path)

    def _save_config(self):
        """保存配置文件"""
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        config_data = {}
        if self._user_data_path:
            config_data["data_path"] = str(self._user_data_path)

        with open(self._config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True)

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
        if self._user_data_path:
            return self._user_data_path

        # 2. 打包环境默认路径
        if not self._is_dev:
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if local_app_data:
                return Path(local_app_data) / "AgentsHub" / "data"

        # 3. 开发环境路径
        return Path("local_data")

    def set_data_path(self, new_path: Path):
        """
        设置数据迁移路径

        Args:
            new_path: 新的数据存储路径
        """
        self._user_data_path = new_path
        self._save_config()

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
    def is_dev(self) -> bool:
        """快捷访问：是否开发环境"""
        return self.system.is_dev


# ============ 全局单例 ============

# 统一入口（推荐使用）
config = Config()
