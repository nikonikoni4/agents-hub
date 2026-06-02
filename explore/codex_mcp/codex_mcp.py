from agents_hub.roles import RoleManager
from agents_hub.config import AgentPlatform

role_manager = RoleManager()
role_manager.create_role(
    name="codex_test",
    platform=AgentPlatform.CODEX,
)