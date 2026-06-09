"""OpenCode CLI 执行器"""

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator

from agents_hub.agent_bridge.exceptions import CLIExecutionError, CLINotFoundError
from agents_hub.config.types import OPENCODE_COMMAND
from agents_hub.roles.models import RoleConfig

logger = logging.getLogger(__name__)


class OpenCodeExecutor:
    """执行 OpenCode CLI 命令"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[dict]:
        """
        启动 OpenCode CLI 并返回解析后的事件流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）
            cwd: 项目目录路径（可选，设置 CLI 工作目录）
            fork_from: 源会话 ID（可选，OpenCode 不支持此参数）
            system_prompt: 系统提示词（可选，通过 OPENCODE_CONFIG_DIR 注入）

        Returns:
            AsyncIterator[dict]: 解析后的事件字典流
        """
        cmd = self._build_command(prompt, config, session_id, system_prompt)
        env = self._build_env(config)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
            )
        except FileNotFoundError as e:
            logger.error(f"OpenCode CLI not found: {OPENCODE_COMMAND}")
            raise CLINotFoundError(platform="OpenCode", command=OPENCODE_COMMAND) from e

        assert process.stdout is not None
        buffer = ""
        while True:
            chunk = await process.stdout.read(256 * 1024)  # 256KB
            if not chunk:
                break
            buffer += chunk.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                decoded = line.strip()
                if decoded:
                    try:
                        event = json.loads(decoded)
                        yield self._transform_event(event)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON: {decoded}")
                        yield {"type": "text", "text": decoded}
        if buffer.strip():
            try:
                event = json.loads(buffer.strip())
                yield self._transform_event(event)
            except json.JSONDecodeError:
                yield {"type": "text", "text": buffer.strip()}

        # 等待进程结束并检查返回码
        await process.wait()
        if process.returncode != 0:
            assert process.stderr is not None
            stderr = await process.stderr.read()
            stderr_text = stderr.decode("utf-8")
            logger.error(f"OpenCode CLI exited with code {process.returncode}: {stderr_text}")
            raise CLIExecutionError(
                platform="OpenCode", exit_code=process.returncode or 1, stderr=stderr_text
            )

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
        system_prompt: str | None = None,
    ) -> list:
        """构建 OpenCode CLI 命令

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID
            system_prompt: agent 名称（对应 agents/ 目录下的 .md 文件名）
        """
        cmd = [OPENCODE_COMMAND, "run", "--format", "json"]

        if session_id:
            cmd.extend(["--session", session_id])

        # system_prompt 传入 agent 名称（如 "nico"、"asdfgh"）
        if system_prompt:
            cmd.extend(["--agent", system_prompt])

        cmd.append(prompt)
        return cmd

    def _build_env(self, config: RoleConfig) -> dict:
        """构建环境变量"""
        env = os.environ.copy()
        if config.work_root:
            env["OPENCODE_CONFIG_DIR"] = config.work_root
        return env

    def _transform_event(self, event: dict) -> dict:
        """
        将 OpenCode 事件转换为统一格式

        OpenCode 事件类型:
        - step_start -> init
        - text -> text_delta
        - step_finish -> turn_complete
        """
        event_type = event.get("type", "")
        part = event.get("part", {})

        if event_type == "step_start":
            return {
                "type": "init",
                "session_id": event.get("sessionID", ""),
                "timestamp": event.get("timestamp", 0),
                "data": part,
            }
        elif event_type == "text":
            return {
                "type": "text_delta",
                "text": part.get("text", ""),
                "session_id": event.get("sessionID", ""),
                "timestamp": event.get("timestamp", 0),
                "time": part.get("time", {}),
            }
        elif event_type == "step_finish":
            return {
                "type": "turn_complete",
                "session_id": event.get("sessionID", ""),
                "timestamp": event.get("timestamp", 0),
                "tokens": part.get("tokens", {}),
                "cost": part.get("cost", 0),
                "reason": part.get("reason", ""),
            }
        else:
            return {
                "type": event_type,
                "session_id": event.get("sessionID", ""),
                "timestamp": event.get("timestamp", 0),
                "data": part,
            }
