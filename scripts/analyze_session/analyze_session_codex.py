"""分析 Codex 平台会话历史 JSONL 文件。

用法:
    python analyze_session_codex.py --path <path_to_jsonl>
    python analyze_session_codex.py --path <path_to_jsonl> --output-md

参数:
    --path              直接指定 JSONL 文件路径
    --config-dir DIR    Codex 配置目录，默认 ~/.codex
    --tool-call-result  是否显示工具调用详情
    --output-md FILE    将输出保存为 Markdown 文件
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def find_session_file(config_dir: Path, session_id: str) -> Path | None:
    """递归搜索匹配的 session JSONL 文件。"""
    for f in config_dir.rglob(f"*{session_id}*.jsonl"):
        return f
    return None


def load_messages(file_path: Path) -> list[dict]:
    """加载 JSONL 文件，返回所有消息列表。"""
    messages = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages


def extract_session_meta(messages: list[dict]) -> dict:
    """提取会话元信息。"""
    for msg in messages:
        if msg.get("type") == "session_meta":
            payload = msg.get("payload", {})
            return {
                "id": payload.get("id", ""),
                "timestamp": payload.get("timestamp", ""),
                "cwd": payload.get("cwd", ""),
                "cli_version": payload.get("cli_version", ""),
                "source": payload.get("source", ""),
                "model_provider": payload.get("model_provider", ""),
                "base_instructions": payload.get("base_instructions", {}).get("text", "")[:200],
                "git_branch": payload.get("git", {}).get("branch", ""),
                "git_commit": payload.get("git", {}).get("commit_hash", "")[:12],
            }
    return {}


def extract_turn_context(messages: list[dict]) -> dict:
    """提取 turn 上下文信息。"""
    for msg in messages:
        if msg.get("type") == "turn_context":
            payload = msg.get("payload", {})
            return {
                "model": payload.get("model", ""),
                "personality": payload.get("personality", ""),
                "effort": payload.get("effort", ""),
                "approval_policy": payload.get("approval_policy", ""),
                "sandbox_policy": payload.get("sandbox_policy", {}).get("type", ""),
            }
    return {}


def extract_conversation(messages: list[dict]) -> list[dict]:
    """提取对话内容，按时间顺序排列。

    以 response_item 为主提取对话，event_msg 只用于元数据事件
    （token_count、task_started、task_complete），避免重复。

    返回消息列表，每条包含:
    - role: developer / user / assistant / system
    - content: 文本内容
    - timestamp: 时间戳
    - phase: 阶段标识（如有）
    - token_usage: token 使用信息（如有）
    """
    conversation = []

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")

        if msg_type == "response_item":
            payload = msg.get("payload", {})
            role = payload.get("role", "")
            content_blocks = payload.get("content", [])

            # 提取文本内容
            texts = []
            for block in content_blocks:
                block_type = block.get("type", "")
                if block_type == "input_text":
                    texts.append(block.get("text", ""))
                elif block_type == "output_text":
                    texts.append(block.get("text", ""))

            if texts:
                conversation.append(
                    {
                        "role": role,
                        "content": "\n".join(texts),
                        "timestamp": timestamp,
                        "source": "response_item",
                    }
                )

        elif msg_type == "event_msg":
            payload = msg.get("payload", {})
            event_type = payload.get("type", "")

            # 只处理元数据事件，user_message 和 agent_message
            # 已在 response_item 中提取，跳过避免重复

            if event_type == "token_count":
                info = payload.get("info", {})
                usage = info.get("total_token_usage", {})
                conversation.append(
                    {
                        "role": "system",
                        "content": "[token_usage]",
                        "timestamp": timestamp,
                        "source": "event_msg",
                        "token_usage": {
                            "input_tokens": usage.get("input_tokens", 0),
                            "cached_input_tokens": usage.get("cached_input_tokens", 0),
                            "output_tokens": usage.get("output_tokens", 0),
                            "reasoning_output_tokens": usage.get("reasoning_output_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                        "context_window": info.get("model_context_window", 0),
                    }
                )

            elif event_type == "task_started":
                conversation.append(
                    {
                        "role": "system",
                        "content": f"[task_started] turn_id={payload.get('turn_id', '')}",
                        "timestamp": timestamp,
                        "source": "event_msg",
                    }
                )

            elif event_type == "task_complete":
                dur = payload.get("duration_ms", 0)
                ttft = payload.get("time_to_first_token_ms", 0)
                conversation.append(
                    {
                        "role": "system",
                        "content": f"[task_complete] duration={dur}ms, time_to_first_token={ttft}ms",
                        "timestamp": timestamp,
                        "source": "event_msg",
                    }
                )

    # 按时间戳排序
    conversation.sort(key=lambda x: x["timestamp"])
    return conversation


def format_content_for_display(content: str, max_len: int = 2000) -> str:
    """格式化内容用于显示，截断过长文本。"""
    if len(content) > max_len:
        return content[:max_len] + "\n... (truncated)"
    return content


def is_system_instruction(content: str) -> bool:
    """判断是否为系统指令（权限、skills、plugins 等）。"""
    markers = [
        "<permissions instructions>",
        "<skills_instructions>",
        "<plugins_instructions>",
        "<environment_context>",
        "<INSTRUCTIONS>",
    ]
    return any(content.strip().startswith(m) for m in markers)


def is_turn_context_content(content: str) -> bool:
    """判断是否为 turn context 内嵌的用户消息（AGENTS.md 等）。"""
    return "AGENTS.md instructions for" in content


def analyze_session(
    config_dir: str, show_tool_calls: bool, session_path: str = None, output_md: str = None
):
    """主分析函数。"""
    if session_path:
        session_file = Path(session_path).expanduser().resolve()
        if not session_file.exists():
            print(f"错误: 文件不存在: {session_file}", file=sys.stderr)
            sys.exit(1)
    else:
        print("错误: 必须提供 --path 参数", file=sys.stderr)
        sys.exit(1)

    print(f"文件: {session_file}")
    print()

    messages = load_messages(session_file)
    output_lines = []

    def print_and_collect(text=""):
        print(text)
        output_lines.append(text)

    # 统计消息类型
    type_counts: dict[str, int] = defaultdict(int)
    for msg in messages:
        type_counts[msg.get("type", "unknown")] += 1
    print_and_collect(f"总消息数: {len(messages)}")
    print_and_collect(f"消息类型: {dict(type_counts)}")

    # 提取会话元信息
    meta = extract_session_meta(messages)
    if meta:
        print_and_collect(f"会话 ID: {meta['id']}")
        print_and_collect(f"工作目录: {meta['cwd']}")
        print_and_collect(f"Cli 版本: {meta['cli_version']}")
        print_and_collect(f"模型提供商: {meta['model_provider']}")
        print_and_collect(f"Git 分支: {meta['git_branch']} ({meta['git_commit']})")

    # 提取 turn context
    ctx = extract_turn_context(messages)
    if ctx:
        print_and_collect(f"模型: {ctx['model']}")
        print_and_collect(f"性格: {ctx['personality']}")
        print_and_collect(f"推理强度: {ctx['effort']}")

    print_and_collect()
    print_and_collect("=" * 60)
    print_and_collect("对话内容")
    print_and_collect("=" * 60)
    print_and_collect()

    # 提取对话
    conversation = extract_conversation(messages)

    skip_system_instructions = not show_tool_calls

    for item in conversation:
        role = item["role"]
        content = item["content"]
        phase = item.get("phase", "")

        if role == "developer":
            # developer 消息通常是系统指令
            if skip_system_instructions and is_system_instruction(content):
                continue
            print_and_collect("[developer]")
            print_and_collect(format_content_for_display(content, 500))
            print_and_collect()

        elif role == "user":
            # 跳过 AGENTS.md 内嵌指令（除非开启详细模式）
            if skip_system_instructions and is_turn_context_content(content):
                continue
            print_and_collect("[用户]")
            print_and_collect(format_content_for_display(content))
            print_and_collect()

        elif role == "assistant":
            phase_tag = f" ({phase})" if phase else ""
            print_and_collect(f"[助手{phase_tag}]")
            print_and_collect(format_content_for_display(content))
            print_and_collect()

        elif role == "system":
            if content == "[token_usage]":
                usage = item.get("token_usage", {})
                ctx_win = item.get("context_window", 0)
                print_and_collect(
                    f"[token] in={usage['input_tokens']} "
                    f"cached={usage['cached_input_tokens']} "
                    f"out={usage['output_tokens']} "
                    f"reasoning={usage['reasoning_output_tokens']} "
                    f"total={usage['total_tokens']} "
                    f"ctx_window={ctx_win}"
                )
            else:
                print_and_collect(f"[system] {content}")
            print_and_collect()

    # 如果指定了输出 md 文件
    if output_md:
        if output_md == "auto":
            stem = Path(session_path).stem if session_path else "codex_session"
            md_path = Path(f"{stem}_analysis.md").resolve()
        else:
            md_path = Path(output_md).expanduser().resolve()
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"\n输出已保存到: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="分析 Codex 平台会话历史 JSONL 文件")
    parser.add_argument("--path", help="直接指定 JSONL 文件路径")
    parser.add_argument(
        "--config-dir",
        default="~/.codex",
        help="Codex 配置目录，默认 ~/.codex",
    )
    parser.add_argument(
        "--tool-call-result",
        action="store_true",
        help="显示系统指令等详细内容",
    )
    parser.add_argument(
        "--output-md",
        nargs="?",
        const="auto",
        help="将输出保存为 Markdown 文件（不指定文件名时自动生成）",
    )

    args = parser.parse_args()

    if not args.path:
        parser.error("必须提供 --path 参数")

    analyze_session(
        args.config_dir,
        args.tool_call_result,
        args.path,
        args.output_md,
    )


if __name__ == "__main__":
    main()
