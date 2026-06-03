"""API routes package."""

from .config import router as config_router
from .group_chat import router as group_chats_router
from .roles import router as roles_router
from .skills import router as skills_router

__all__ = ["config_router", "roles_router", "skills_router", "group_chats_router"]
