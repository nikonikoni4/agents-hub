"""团队数据模型"""

from pydantic import BaseModel


class TeamInfo(BaseModel):
    """团队信息

    Attributes:
        name: 团队名称（唯一标识）
        members: 成员角色名称列表
    """

    name: str
    members: list[str]
