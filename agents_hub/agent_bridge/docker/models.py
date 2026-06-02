"""Docker 模块数据模型"""

from dataclasses import dataclass


@dataclass
class ContainerConfig:
    """容器配置"""

    agent_name: str
    group_chat_id: str
    work_root: str  # Agent 配置目录
    cwd: str  # 工作目录
    container_name: str  # 容器名称
