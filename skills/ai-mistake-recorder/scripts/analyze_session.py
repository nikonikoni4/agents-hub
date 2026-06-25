"""分析 Claude Code 或 Codex 平台的会话历史 JSONL 文件。

自动检测平台格式（Claude Code / Codex），统一解析输出。

用法:
    python analyze_session.py <session_id> [--config-dir DIR] [--tool-call-result]
    python analyze_session.py --path <path_to_jsonl> [--tool-call-result]
    python analyze_session.py --path <path_to_jsonl> --platform codex [--tool-call-result]

参数:
    session_id          会话 UUID（仅 Claude Code）
    --path              直接指定 JSONL 文件路径
    --config-dir DIR    配置目录，默认 ~/.claude（Claude Code）或 ~/.codex（Codex）
    --platform          指定平台 (auto|claude|codex)，默认 auto 自动检测
    --tool-call-result  是否显示工具调用详情（调用输入 + 返回结果）
    --output-md FILE    将输出保存为 Markdown 文件
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


# ─── 共享工具函数 ──────────────────────────────────────────────


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


def find_session_file(config_dir: Path, session_id: str) -> Path | None:
    """递归搜索 {session_id}.jsonl 文件。"""
    for f in config_dir.rglob(f"{session_id}.jsonl"):
        return f
    return None


def format_content_for_display(content: str, max_len: int = 2000) -> str:
    """格式化内容用于显示，截断过长文本。"""
    if len(content) > max_len:
        return content[:max_len] + "\n... (truncated)"
    return content


def is_system_instruction(content: str) -> bool:
    """判断是否为系统指令。"""
    markers = [
        "<permissions instructions>",
        "<skills_instructions>",
        "<plugins_instructions>",
        "<environment_context>",
        "<INSTRUCTIONS>",
    ]
    return any(content.strip().startswith(m) for m in markers)


def is_context_metadata(content: str) -> bool:
    """判断是否为上下文元数据（AGENTS.md 等）。"""
    return "AGENTS.md instructions for" in content


# ─── 格式检测 ─────────────────────────────────────────────────


def detect_platform(messages: list[dict]) -> str:
    """自动检测平台格式。

    - Codex: 包含 type=session_meta 的行
    - Claude Code: 包含 type=assistant 且 message 字段有 id
    """
    for msg in messages[:20]:
        if msg.get("type") == "session_meta":
            return "codex"
        if msg.get("type") == "assistant" and "message" in msg:
            return "claude"
    return "claude"  # 默认


# ─── Claude Code 解析器 ───────────────────────────────────────


def claude_group_assistant_chunks(messages: list[dict]) -> list[dict]:
    """将 Claude Code 的 assistant 消息按 message.id 合并。"""
    chunks_by_msg_id: dict[str, list[dict]] = defaultdict(list)
    assistant_meta: dict[str, dict] = {}

    for msg in messages:
        if msg.get("type") == "assistant":
            inner = msg.get("message", {})
            msg_id = inner.get("id", msg.get("uuid", ""))
            chunks_by_msg_id[msg_id].append(msg)
            if msg_id not in assistant_meta:
                assistant_meta[msg_id] = {
                    "parentUuid": msg.get("parentUuid"),
                    "uuid": msg.get("uuid"),
                    "timestamp": msg.get("timestamp"),
                    "type": "assistant",
                    "message_id": msg_id,
                    "model": inner.get("model", ""),
                    "attributionAgent": msg.get("attributionAgent"),
                    "attributionSkill": msg.get("attributionSkill"),
                }

    merged = []
    for msg_id, chunks in chunks_by_msg_id.items():
        meta = assistant_meta[msg_id]
        all_content = []
        usage = None
        stop_reason = None
        for chunk in chunks:
            inner = chunk.get("message", {})
            all_content.extend(inner.get("content", []))
            if inner.get("usage"):
                usage = inner["usage"]
            if inner.get("stop_reason"):
                stop_reason = inner["stop_reason"]
        merged.append({**meta, "content": all_content, "usage": usage, "stop_reason": stop_reason})

    return merged


def claude_build_conversation(messages: list[dict]) -> list[dict]:
    """构建 Claude Code 对话列表。"""
    user_msgs, tool_results, system_msgs, other_msgs = [], [], [], []

    for msg in messages:
        t = msg.get("type")
        if t == "assistant":
            continue
        elif t == "user":
            content = msg.get("message", {}).get("content")
            if isinstance(content, list) and content and content[0].get("type") == "tool_result":
                tool_results.append(msg)
            else:
                user_msgs.append(msg)
        elif t == "system":
            system_msgs.append(msg)
        elif t == "attachment":
            other_msgs.append(msg)

    assistant_msgs = claude_group_assistant_chunks(messages)

    all_msgs = []
    for msg in user_msgs:
        all_msgs.append(("user", msg.get("timestamp", ""), msg))
    for msg in assistant_msgs:
        all_msgs.append(("assistant", msg.get("timestamp", ""), msg))
    for msg in tool_results:
        all_msgs.append(("tool_result", msg.get("timestamp", ""), msg))
    for msg in system_msgs:
        all_msgs.append(("system", msg.get("timestamp", ""), msg))
    for msg in other_msgs:
        all_msgs.append(("attachment", msg.get("timestamp", ""), msg))

    all_msgs.sort(key=lambda x: x[1])
    return [(t, m) for t, _, m in all_msgs]


def claude_detect_streaming(messages: list[dict]) -> bool:
    """检测 Claude Code 是否为流式输出。"""
    id_counts: dict[str, int] = defaultdict(int)
    for msg in messages:
        if msg.get("type") == "assistant":
            msg_id = msg.get("message", {}).get("id", "")
            if msg_id:
                id_counts[msg_id] += 1
    return any(c > 1 for c in id_counts.values())


def claude_extract_meta(messages: list[dict]) -> dict:
    """提取 Claude Code 会话元信息。"""
    models = set()
    for msg in messages:
        if msg.get("type") == "assistant":
            model = msg.get("message", {}).get("model")
            if model:
                models.add(model)
    return {"models": list(models)}


def claude_format_user(msg: dict) -> str:
    content = msg.get("message", {}).get("content", "")
    if isinstance(content, str):
        return content
    return str(content)


def claude_format_assistant(msg: dict, show_tool_calls: bool) -> list[str]:
    lines = []
    for block in msg.get("content", []):
        block_type = block.get("type")
        if block_type == "thinking":
            thinking = block.get("thinking", "")
            if len(thinking) > 500:
                thinking = thinking[:500] + "..."
            lines.append(f"  [thinking] {thinking}")
        elif block_type == "text":
            lines.append(block.get("text", ""))
        elif block_type == "tool_use":
            if show_tool_calls:
                tool_name = block.get("name", "")
                tool_input = block.get("input", {})
                input_str = json.dumps(tool_input, ensure_ascii=False, indent=2)
                if len(input_str) > 800:
                    input_str = input_str[:800] + "\n..."
                lines.append(f"  [tool_call] {tool_name}")
                for iline in input_str.split("\n"):
                    lines.append(f"    {iline}")
            else:
                lines.append(f"  [tool_call] {block.get('name', '')}")
    return lines


def claude_format_tool_result(msg: dict) -> list[str]:
    lines = []
    content = msg.get("message", {}).get("content", [])
    if isinstance(content, list):
        for item in content:
            if item.get("type") == "tool_result":
                result_content = item.get("content", "")
                if isinstance(result_content, list):
                    result_content = json.dumps(result_content, ensure_ascii=False, indent=2)
                elif not isinstance(result_content, str):
                    result_content = str(result_content)
                try:
                    parsed = json.loads(result_content)
                    result_content = json.dumps(parsed, ensure_ascii=False, indent=2)
                except (json.JSONDecodeError, TypeError):
                    pass
                if len(result_content) > 1000:
                    result_content = result_content[:1000] + "\n..."
                lines.append("  [tool_result]")
                for rline in result_content.split("\n"):
                    lines.append(f"    {rline}")
    return lines


# ─── Codex 解析器 ─────────────────────────────────────────────


def codex_extract_meta(messages: list[dict]) -> dict:
    """提取 Codex 会话元信息。"""
    meta = {}
    for msg in messages:
        if msg.get("type") == "session_meta":
            p = msg.get("payload", {})
            meta = {
                "id": p.get("id", ""),
                "timestamp": p.get("timestamp", ""),
                "cwd": p.get("cwd", ""),
                "cli_version": p.get("cli_version", ""),
                "model_provider": p.get("model_provider", ""),
                "git_branch": p.get("git", {}).get("branch", ""),
                "git_commit": p.get("git", {}).get("commit_hash", "")[:12],
            }
            break
    for msg in messages:
        if msg.get("type") == "turn_context":
            p = msg.get("payload", {})
            meta["model"] = p.get("model", "")
            meta["personality"] = p.get("personality", "")
            meta["effort"] = p.get("effort", "")
            break
    return meta


def codex_build_conversation(messages: list[dict]) -> list[dict]:
    """构建 Codex 对话列表，以 response_item 为主，event_msg 只用于元数据。"""
    conversation = []

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")

        if msg_type == "response_item":
            payload = msg.get("payload", {})
            role = payload.get("role", "")
            texts = []
            for block in payload.get("content", []):
                bt = block.get("type", "")
                if bt in ("input_text", "output_text"):
                    texts.append(block.get("text", ""))
            if texts:
                conversation.append(
                    {
                        "role": role,
                        "content": "\n".join(texts),
                        "timestamp": timestamp,
                    }
                )

        elif msg_type == "event_msg":
            payload = msg.get("payload", {})
            et = payload.get("type", "")

            if et == "token_count":
                info = payload.get("info", {})
                usage = info.get("total_token_usage", {})
                conversation.append(
                    {
                        "role": "system",
                        "content": "[token_usage]",
                        "timestamp": timestamp,
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
            elif et == "task_started":
                conversation.append(
                    {
                        "role": "system",
                        "content": f"[task_started] turn_id={payload.get('turn_id', '')}",
                        "timestamp": timestamp,
                    }
                )
            elif et == "task_complete":
                dur = payload.get("duration_ms", 0)
                ttft = payload.get("time_to_first_token_ms", 0)
                conversation.append(
                    {
                        "role": "system",
                        "content": f"[task_complete] duration={dur}ms, time_to_first_token={ttft}ms",
                        "timestamp": timestamp,
                    }
                )

    conversation.sort(key=lambda x: x["timestamp"])
    return conversation


# ─── 主分析函数 ────────────────────────────────────────────────


def analyze_session(
    session_id: str | None,
    config_dir: str,
    show_tool_calls: bool,
    session_path: str | None = None,
    output_md: str | None = None,
    platform: str = "auto",
):
    """主分析函数。"""
    # 确定文件路径
    if session_path:
        session_file = Path(session_path).expanduser().resolve()
        if not session_file.exists():
            print(f"错误: 文件不存在: {session_file}", file=sys.stderr)
            sys.exit(1)
    else:
        config_path = Path(config_dir).expanduser().resolve()
        if not config_path.exists():
            print(f"错误: 配置目录不存在: {config_path}", file=sys.stderr)
            sys.exit(1)
        if not session_id:
            print("错误: 必须提供 session_id 或 --path 参数", file=sys.stderr)
            sys.exit(1)
        print(f"搜索会话 {session_id} ...")
        session_file = find_session_file(config_path, session_id)
        if not session_file:
            print(f"错误: 未找到会话 {session_id}", file=sys.stderr)
            print(f"搜索路径: {config_path}", file=sys.stderr)
            sys.exit(1)

    print(f"文件: {session_file}")
    messages = load_messages(session_file)

    # 检测平台
    if platform == "auto":
        platform = detect_platform(messages)
    print(f"平台: {platform}")
    print()

    output_lines = []

    def out(text=""):
        print(text)
        output_lines.append(text)

    # ─── Claude Code ───
    if platform == "claude":
        meta = claude_extract_meta(messages)
        is_streaming = claude_detect_streaming(messages)

        out(f"总消息数: {len(messages)}")
        mode = "流式 (streaming, chunk 拆分存储)" if is_streaming else "非流式 (完整消息存储)"
        out(f"存储模式: {mode}")

        type_counts: dict[str, int] = defaultdict(int)
        for msg in messages:
            type_counts[msg.get("type", "unknown")] += 1
        out(f"消息类型: {dict(type_counts)}")

        if meta["models"]:
            out(f"使用模型: {', '.join(meta['models'])}")

        out()
        out("=" * 60)
        out("对话内容")
        out("=" * 60)
        out()

        conversation = claude_build_conversation(messages)

        for msg_type, msg in conversation:
            if msg_type == "user":
                if msg.get("isMeta"):
                    continue
                content = claude_format_user(msg)
                if content:
                    out(f"[用户] {content}")
                    out()

            elif msg_type == "assistant":
                role = "助手"
                attr_agent = msg.get("attributionAgent")
                attr_skill = msg.get("attributionSkill")
                if attr_agent:
                    role = f"子代理({attr_agent})"
                elif attr_skill:
                    role = f"技能({attr_skill})"

                model = msg.get("model", "")
                usage = msg.get("usage")
                usage_str = ""
                if usage:
                    in_tok = usage.get("input_tokens", 0)
                    out_tok = usage.get("output_tokens", 0)
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    usage_str = f" [in:{in_tok} out:{out_tok} cache:{cache_read}]"

                out(f"[{role}] ({model}){usage_str}")
                for line in claude_format_assistant(msg, show_tool_calls):
                    out(line)
                out()

            elif msg_type == "tool_result":
                if show_tool_calls:
                    for line in claude_format_tool_result(msg):
                        out(line)
                    if claude_format_tool_result(msg):
                        out()

            elif msg_type == "system":
                subtype = msg.get("subtype", "")
                content = msg.get("content", "")
                if subtype == "turn_duration":
                    dur = msg.get("durationMs", 0)
                    count = msg.get("messageCount", 0)
                    out(f"  [system] turn_duration: {dur}ms, {count} messages")
                else:
                    out(
                        f"  [system:{subtype}] {content[:200]}"
                        if content
                        else f"  [system:{subtype}]"
                    )
                out()

    # ─── Codex ───
    elif platform == "codex":
        meta = codex_extract_meta(messages)

        type_counts: dict[str, int] = defaultdict(int)
        for msg in messages:
            type_counts[msg.get("type", "unknown")] += 1
        out(f"总消息数: {len(messages)}")
        out(f"消息类型: {dict(type_counts)}")

        if meta.get("id"):
            out(f"会话 ID: {meta['id']}")
        if meta.get("cwd"):
            out(f"工作目录: {meta['cwd']}")
        if meta.get("cli_version"):
            out(f"Cli 版本: {meta['cli_version']}")
        if meta.get("model_provider"):
            out(f"模型提供商: {meta['model_provider']}")
        if meta.get("git_branch"):
            out(f"Git 分支: {meta['git_branch']} ({meta.get('git_commit', '')})")
        if meta.get("model"):
            out(f"模型: {meta['model']}")
        if meta.get("personality"):
            out(f"性格: {meta['personality']}")
        if meta.get("effort"):
            out(f"推理强度: {meta['effort']}")

        out()
        out("=" * 60)
        out("对话内容")
        out("=" * 60)
        out()

        conversation = codex_build_conversation(messages)

        for item in conversation:
            role = item["role"]
            content = item["content"]

            if role == "developer":
                if not show_tool_calls and is_system_instruction(content):
                    continue
                out("[developer]")
                out(format_content_for_display(content, 500))
                out()

            elif role == "user":
                if not show_tool_calls and is_context_metadata(content):
                    continue
                out("[用户]")
                out(format_content_for_display(content))
                out()

            elif role == "assistant":
                out("[助手]")
                out(format_content_for_display(content))
                out()

            elif role == "system":
                if content == "[token_usage]":
                    usage = item.get("token_usage", {})
                    ctx_win = item.get("context_window", 0)
                    out(
                        f"[token] in={usage['input_tokens']} "
                        f"cached={usage['cached_input_tokens']} "
                        f"out={usage['output_tokens']} "
                        f"reasoning={usage['reasoning_output_tokens']} "
                        f"total={usage['total_tokens']} "
                        f"ctx_window={ctx_win}"
                    )
                else:
                    out(f"[system] {content}")
                out()

    # ─── 输出 MD ───
    if output_md:
        if output_md == "auto":
            stem = Path(session_path).stem if session_path else (session_id or "session")
            md_path = Path(f"{stem}_analysis.md").resolve()
        else:
            md_path = Path(output_md).expanduser().resolve()
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"\n输出已保存到: {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="分析 Claude Code 或 Codex 平台的会话历史 JSONL 文件"
    )
    parser.add_argument(
        "session_id",
        nargs="?",
        help="会话 UUID（仅 Claude Code）",
    )
    parser.add_argument(
        "--path",
        help="直接指定 JSONL 文件路径",
    )
    parser.add_argument(
        "--config-dir",
        default="~/.claude",
        help="配置目录，默认 ~/.claude",
    )
    parser.add_argument(
        "--platform",
        choices=["auto", "claude", "codex"],
        default="auto",
        help="指定平台 (auto|claude|codex)，默认 auto 自动检测",
    )
    parser.add_argument(
        "--tool-call-result",
        action="store_true",
        help="显示工具调用详情（调用输入 + 返回结果）",
    )
    parser.add_argument(
        "--output-md",
        nargs="?",
        const="auto",
        help="将输出保存为 Markdown 文件（不指定文件名时自动生成）",
    )

    args = parser.parse_args()

    if not args.path and not args.session_id:
        parser.error("必须提供 session_id 或 --path 参数")

    analyze_session(
        args.session_id,
        args.config_dir,
        args.tool_call_result,
        args.path,
        args.output_md,
        args.platform,
    )


if __name__ == "__main__":
    main()
