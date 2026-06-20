"""Codex CLI 执行器"""

import asyncio
import logging
import os
import shlex
from collections.abc import AsyncIterator

from agents_hub.agent_bridge.exceptions import CLIExecutionError, CLINotFoundError
from agents_hub.config.types import CODEX_COMMAND
from agents_hub.roles.models import RoleConfig
from agents_hub.utils import get_logger


def _sanitize_for_codex_cli(text: str) -> str:
    """清理文本，适配 Codex CLI -c 参数。

    Codex CLI 的 -c 参数不支持换行符，且 value 中的单引号需要正确转义。
    """
    cleaned = text.replace("\n", " ").replace("\r", " ")
    return shlex.quote(cleaned)


logger = get_logger(__name__)


class CodexExecutor:
    """执行 Codex CLI 命令"""

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
        启动 Codex CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话。Codex fork 时传入 fork_codex_session 返回的新 ID）
            cwd: 项目目录路径（可选，通过 -C 参数指定工作目录）
            fork_from: 已弃用。Codex 的 fork 通过 fork_codex_session 在文件层面完成，
                       executor 通过 session_id 恢复新会话，此参数被忽略。
            system_prompt: 系统提示词（可选，通过 -c instructions 注入）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        # 移除换行符，避免 Codex CLI 命令行解析错误
        # 参考: docs/history-bugs/2026-05-28-cli-system-prompt-blocks-simple-requests.md
        prompt = prompt.replace("\n", " ").replace("\r", " ")

        cmd = self._build_command(
            prompt, config, session_id, cwd, fork_from, system_prompt=system_prompt
        )
        env = self._build_env(config)

        logger.info("Codex CLI: %s", " ".join(cmd))
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
            )
        except FileNotFoundError as e:
            logger.error(f"Codex CLI not found: {CODEX_COMMAND}")
            raise CLINotFoundError(platform="Codex", command=CODEX_COMMAND) from e

        # 注册进程（如果有 session_id）
        if session_id:
            async with self._lock:
                self._processes[session_id] = process

        try:
            assert process.stdout is not None
            logger.debug(
                "[CodexExecutor] 进程已启动: pid=%s, session_id=%s",
                process.pid,
                session_id,
            )

            # 按固定块读取并手动切行，避免 asyncio 按行 API
            # 在遇到超长单行输出时抛出 LimitOverrunError。
            # Codex 的单行 JSON 可能非常长（如 command_execution 的 aggregated_output）。
            buffer = ""
            line_count = 0
            while True:
                logger.debug(
                    "[CodexExecutor] read 等待: pid=%s, session_id=%s, line_count=%d",
                    process.pid,
                    session_id,
                    line_count,
                )
                chunk = await process.stdout.read(256 * 1024)
                if not chunk:
                    logger.debug(
                        "[CodexExecutor] read 返回空 (EOF): pid=%s, session_id=%s, line_count=%d",
                        process.pid,
                        session_id,
                        line_count,
                    )
                    break

                buffer += chunk.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    decoded = line.strip()
                    if decoded:
                        line_count += 1
                        yield decoded

            if buffer.strip():
                line_count += 1
                yield buffer.strip()

            logger.debug(
                "[CodexExecutor] stdout 流结束: pid=%s, session_id=%s, line_count=%d",
                process.pid,
                session_id,
                line_count,
            )

            # 等待进程结束并检查返回码
            # Bug fix: 添加超时防止永久阻塞
            # 参考: docs/history-bugs/2026-06-20-codex-process-wait-blocking.md
            process_wait_timeout = int(os.getenv("PROCESS_WAIT_TIMEOUT", "30"))
            logger.debug(
                "[CodexExecutor] 等待进程退出: pid=%s, session_id=%s",
                process.pid,
                session_id,
            )
            try:
                await asyncio.wait_for(process.wait(), timeout=process_wait_timeout)
                logger.debug(
                    "[CodexExecutor] 进程已退出: pid=%s, session_id=%s, returncode=%s",
                    process.pid,
                    session_id,
                    process.returncode,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[CodexExecutor] 进程等待超时(%ds)，强制终止: pid=%s, session_id=%s, line_count=%d. "
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
                    logger.warning("[CodexExecutor] 强制终止进程失败: %s", e)
                # 不抛出异常，因为 stdout 已经完整读取，CLI 执行成功

            if process.returncode != 0:
                assert process.stderr is not None
                stderr = await process.stderr.read()
                stderr_text = stderr.decode("utf-8")
                logger.error(f"Codex CLI exited with code {process.returncode}: {stderr_text}")
                raise CLIExecutionError(
                    platform="Codex", exit_code=process.returncode or 1, stderr=stderr_text
                )
        finally:
            # 清理进程引用
            if session_id:
                async with self._lock:
                    self._processes.pop(session_id, None)

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
                    logger.info(f"[CodexExecutor] 已终止 session {session_id} 的进程")
                except ProcessLookupError:
                    # 进程已经退出
                    logger.debug(f"[CodexExecutor] session {session_id} 的进程已不存在")
                finally:
                    self._processes.pop(session_id, None)

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None,
        cwd: str | None = None,
        fork_from: str | None = None,
        system_prompt: str | None = None,
    ) -> list:
        """构建 Codex CLI 命令。-C 必须在子命令之前。

        Codex 的 fork 通过 fork_codex_session() 在文件层面完成（复制 JSONL 会话文件），
        executor 通过 session_id 恢复新会话，fork_from 参数被忽略。
        """
        cmd = [CODEX_COMMAND]
        if cwd:
            cmd.extend(["-C", cwd])

        if session_id:
            cmd.extend(["exec", "resume", "--json", session_id])
        else:
            cmd.extend(["exec", "--json"])

        if system_prompt:
            cmd.extend(["-c", f"instructions={_sanitize_for_codex_cli(system_prompt)}"])

        cmd.append(prompt)
        return cmd

    def _build_env(self, config: RoleConfig) -> dict:
        """构建环境变量"""
        env = os.environ.copy()
        if config.work_root:
            env["CODEX_HOME"] = config.work_root
        return env
