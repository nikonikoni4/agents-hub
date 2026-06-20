"""Claude CLI 执行器"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator

from agents_hub.agent_bridge.exceptions import CLIExecutionError, CLINotFoundError
from agents_hub.config.types import CLAUDE_COMMAND
from agents_hub.roles.models import RoleConfig
from agents_hub.utils import get_logger

logger = get_logger(__name__)


class ClaudeExecutor:
    """执行 Claude CLI 命令"""

    def __init__(self):
        # 进程追踪字典：key = session_id, value = Process
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._lock = asyncio.Lock()

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """
        启动 Claude CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）
            cwd: 项目目录路径（可选，设置 CLI 工作目录）
            fork_from: 源会话 ID（可选，用于从群聊 fork 会话到单聊）
            system_prompt: 系统提示词（可选，通过 --append-system-prompt 注入）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        cmd = self._build_command(
            prompt, config, session_id, fork_from, system_prompt=system_prompt
        )
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
            logger.error(f"Claude CLI not found: {CLAUDE_COMMAND}")
            raise CLINotFoundError(platform="Claude", command=CLAUDE_COMMAND) from e

        # 注册进程（如果有 session_id）
        if session_id:
            async with self._lock:
                self._processes[session_id] = process

        try:
            assert process.stdout is not None
            logger.debug(
                "[ClaudeExecutor] 进程已启动: pid=%s, session_id=%s",
                process.pid,
                session_id,
            )
            buffer = ""
            line_count = 0
            while True:
                logger.debug(
                    "[ClaudeExecutor] read 等待: pid=%s, session_id=%s, line_count=%d",
                    process.pid,
                    session_id,
                    line_count,
                )
                chunk = await process.stdout.read(256 * 1024)  # 256KB
                if not chunk:
                    logger.debug(
                        "[ClaudeExecutor] read 返回空 (EOF): pid=%s, session_id=%s, line_count=%d",
                        process.pid,
                        session_id,
                        line_count,
                    )
                    break
                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    decoded = line.strip()
                    if decoded:
                        line_count += 1
                        logger.debug("[ClaudeExecutor] raw line: %s", decoded[:200])
                        yield decoded
            if buffer.strip():
                yield buffer.strip()

            logger.debug(
                "[ClaudeExecutor] stdout 流结束: pid=%s, session_id=%s, line_count=%d",
                process.pid,
                session_id,
                line_count,
            )

            # 等待进程结束并检查返回码
            # Bug fix: 添加超时防止永久阻塞
            # 参考: docs/history-bugs/2026-06-20-codex-process-wait-blocking.md
            process_wait_timeout = int(os.getenv("PROCESS_WAIT_TIMEOUT", "30"))
            logger.debug(
                "[ClaudeExecutor] 等待进程退出: pid=%s, session_id=%s",
                process.pid,
                session_id,
            )
            try:
                await asyncio.wait_for(process.wait(), timeout=process_wait_timeout)
                logger.debug(
                    "[ClaudeExecutor] 进程已退出: pid=%s, session_id=%s, returncode=%s",
                    process.pid,
                    session_id,
                    process.returncode,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[ClaudeExecutor] 进程等待超时(%ds)，强制终止: pid=%s, session_id=%s, line_count=%d. "
                    "可能原因：进程僵尸、子进程未关闭、资源未释放。stdout 已完整读取，继续执行。",
                    process_wait_timeout,
                    process.pid,
                    session_id,
                    line_count,
                )
                try:
                    process.kill()
                    # 不等待 kill 完成，避免再次阻塞
                except Exception as e:
                    logger.debug("[ClaudeExecutor] 强制终止进程失败: %s", e)
                # 不抛出异常，因为 stdout 已经完整读取，CLI 执行成功

            if process.returncode != 0:
                assert process.stderr is not None
                stderr = await process.stderr.read()
                stderr_text = stderr.decode("utf-8")
                logger.error(f"Claude CLI exited with code {process.returncode}: {stderr_text}")
                raise CLIExecutionError(
                    platform="Claude", exit_code=process.returncode or 1, stderr=stderr_text
                )
        finally:
            # 清理进程引用
            if session_id:
                async with self._lock:
                    self._processes.pop(session_id, None)

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> list:
        """构建 Claude CLI 命令"""
        cmd = [
            CLAUDE_COMMAND,
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
        ]

        if config.bare:
            cmd.append("--bare")

        if fork_from:
            # fork 会话：从源会话创建新分支
            cmd.extend(["--fork-session", "--resume", fork_from])
        elif session_id:
            # 恢复已有会话
            cmd.extend(["--resume", session_id])

        if system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])

        # 添加禁用工具列表（必须使用 = 格式）
        if config.disabled_tools:
            cmd.append(f"--disallowedTools={','.join(config.disabled_tools)}")

        cmd.append(prompt)
        return cmd

    async def stop_session(self, session_id: str):
        """
        立即终止指定 session 的进程

        Args:
            session_id: 会话 ID
        """
        async with self._lock:
            process = self._processes.get(session_id)
            if process:
                try:
                    process.kill()  # 立即 SIGKILL (Unix) 或 TerminateProcess (Windows)
                    await process.wait()
                    logger.info(f"[ClaudeExecutor] 已终止 session {session_id} 的进程")
                except ProcessLookupError:
                    # 进程已经退出
                    logger.debug(f"[ClaudeExecutor] session {session_id} 的进程已不存在")
                finally:
                    self._processes.pop(session_id, None)

    def _build_env(self, config: RoleConfig) -> dict:
        """构建环境变量"""
        env = os.environ.copy()
        if config.work_root:
            env["CLAUDE_CONFIG_DIR"] = config.work_root
        return env
