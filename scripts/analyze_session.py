"""分析 Claude Code 会话历史 JSONL 文件。

用法:
    python analyze_session.py <session_id> [--config-dir DIR] [--tool-call-result]
    python analyze_session.py --path <path_to_jsonl> [--tool-call-result]

参数:
    session_id          会话 UUID
    --path              直接指定 JSONL 文件路径
    --config-dir DIR    Claude 配置目录，默认 ~/.claude
    --tool-call-result  是否显示工具调用详情（调用输入 + 返回结果）
    --output-md FILE    将输出保存为 Markdown 文件
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def find_session_file(config_dir: Path, session_id: str) -> Path | None:
    """递归搜索 {session_id}.jsonl 文件。"""
    for f in config_dir.rglob(f"{session_id}.jsonl"):
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


def group_assistant_chunks(messages: list[dict]) -> list[dict]:
    """将 assistant 消息按 message.id 合并，重建完整响应。

    JSONL 中一个 assistant 响应被拆成多行（每行一个 content block），
    通过 message.id 关联。这里将它们合并为一条完整消息。
    """
    # 按 message.id 分组
    chunks_by_msg_id: dict[str, list[dict]] = defaultdict(list)
    non_assistant = []
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
        else:
            non_assistant.append(msg)

    # 合并每个 message.id 的 content blocks
    merged_assistants = []
    for msg_id, chunks in chunks_by_msg_id.items():
        meta = assistant_meta[msg_id]
        all_content = []
        usage = None
        stop_reason = None

        for chunk in chunks:
            inner = chunk.get("message", {})
            content_blocks = inner.get("content", [])
            all_content.extend(content_blocks)
            if inner.get("usage"):
                usage = inner["usage"]
            if inner.get("stop_reason"):
                stop_reason = inner["stop_reason"]

        merged = {
            **meta,
            "content": all_content,
            "usage": usage,
            "stop_reason": stop_reason,
        }
        merged_assistants.append(merged)

    return merged_assistants


def build_conversation(messages: list[dict]) -> list[dict]:
    """构建对话列表，按时间顺序排列。

    返回消息类型：
    - user: 用户消息
    - assistant: 助手响应（已合并 chunks）
    - tool_result: 工具调用结果
    - system: 系统消息
    - attachment: 附件/钩子
    """
    # 分离不同类型
    user_msgs = []
    tool_results = []
    system_msgs = []
    other_msgs = []

    for msg in messages:
        t = msg.get("type")
        if t == "assistant":
            continue  # 单独处理
        elif t == "user":
            content = msg.get("message", {}).get("content")
            # 判断是普通用户消息还是工具结果
            if isinstance(content, list) and content and content[0].get("type") == "tool_result":
                tool_results.append(msg)
            else:
                user_msgs.append(msg)
        elif t == "system":
            system_msgs.append(msg)
        elif t == "attachment":
            other_msgs.append(msg)
        # 忽略 file-history-snapshot, last-prompt, ai-title, permission-mode, queue-operation

    # 合并 assistant chunks
    assistant_msgs = group_assistant_chunks(messages)

    # 按时间戳排序所有消息
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


def format_user_message(msg: dict) -> str:
    """格式化用户消息。"""
    content = msg.get("message", {}).get("content", "")
    if isinstance(content, str):
        return content
    return str(content)


def format_assistant_message(msg: dict, show_tool_calls: bool) -> list[str]:
    """格式化助手消息，返回多个输出行。"""
    lines = []
    for block in msg.get("content", []):
        block_type = block.get("type")
        if block_type == "thinking":
            thinking = block.get("thinking", "")
            # 截断过长的 thinking
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
                # 截断过长的输入
                if len(input_str) > 800:
                    input_str = input_str[:800] + "\n..."
                lines.append(f"  [tool_call] {tool_name}")
                for iline in input_str.split("\n"):
                    lines.append(f"    {iline}")
            else:
                lines.append(f"  [tool_call] {block.get('name', '')}")
    return lines


def format_tool_result(msg: dict, show_details: bool) -> list[str]:
    """格式化工具调用结果。"""
    if not show_details:
        return []

    lines = []
    content = msg.get("message", {}).get("content", [])
    if isinstance(content, list):
        for item in content:
            if item.get("type") == "tool_result":
                result_content = item.get("content", "")
                # content 可能是 list（多个内容块）或 string
                if isinstance(result_content, list):
                    result_content = json.dumps(result_content, ensure_ascii=False, indent=2)
                elif not isinstance(result_content, str):
                    result_content = str(result_content)
                # 尝试解析 JSON 字符串
                try:
                    parsed = json.loads(result_content)
                    result_content = json.dumps(parsed, ensure_ascii=False, indent=2)
                except (json.JSONDecodeError, TypeError):
                    pass
                # 截断过长结果
                if len(result_content) > 1000:
                    result_content = result_content[:1000] + "\n..."
                lines.append(f"  [tool_result]")
                for rline in result_content.split("\n"):
                    lines.append(f"    {rline}")
    return lines


def format_system_message(msg: dict) -> str:
    """格式化系统消息。"""
    subtype = msg.get("subtype", "")
    content = msg.get("content", "")
    if subtype == "turn_duration":
        dur = msg.get("durationMs", 0)
        count = msg.get("messageCount", 0)
        return f"  [system] turn_duration: {dur}ms, {count} messages"
    return f"  [system:{subtype}] {content[:200]}" if content else f"  [system:{subtype}]"


def format_attachment(msg: dict) -> str:
    """格式化附件消息。"""
    att = msg.get("attachment", {})
    att_type = att.get("type", "")
    return f"  [attachment:{att_type}]"


def detect_streaming(messages: list[dict]) -> bool:
    """检测是否为流式输出（基于 assistant 消息的 chunk 拆分模式）。"""
    msg_ids = set()
    for msg in messages:
        if msg.get("type") == "assistant":
            inner = msg.get("message", {})
            msg_id = inner.get("id", "")
            if msg_id:
                msg_ids.add(msg_id)

    # 统计每个 message.id 出现的次数
    id_counts: dict[str, int] = defaultdict(int)
    for msg in messages:
        if msg.get("type") == "assistant":
            inner = msg.get("message", {})
            msg_id = inner.get("id", "")
            if msg_id:
                id_counts[msg_id] += 1

    # 如果有任何 message.id 出现超过 1 次，说明是流式（chunk 拆分）存储
    has_chunks = any(count > 1 for count in id_counts.values())
    return has_chunks


def analyze_session(session_id: str, config_dir: str, show_tool_calls: bool, session_path: str = None, output_md: str = None):
    """主分析函数。"""
    # 确定会话文件路径
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
        print(f"搜索会话 {session_id} ...")
        session_file = find_session_file(config_path, session_id)
        if not session_file:
            print(f"错误: 未找到会话 {session_id}", file=sys.stderr)
            print(f"搜索路径: {config_path}", file=sys.stderr)
            sys.exit(1)

    print(f"找到文件: {session_file}")
    print()

    messages = load_messages(session_file)
    output_lines = []

    def print_and_collect(text=""):
        print(text)
        output_lines.append(text)

    print_and_collect(f"总消息数: {len(messages)}")

    # 检测流式/非流式
    is_streaming = detect_streaming(messages)
    mode = "流式 (streaming, chunk 拆分存储)" if is_streaming else "非流式 (完整消息存储)"
    print_and_collect(f"存储模式: {mode}")

    # 统计
    type_counts: dict[str, int] = defaultdict(int)
    for msg in messages:
        type_counts[msg.get("type", "unknown")] += 1
    print_and_collect(f"消息类型: {dict(type_counts)}")

    # 获取模型信息
    models = set()
    for msg in messages:
        if msg.get("type") == "assistant":
            model = msg.get("message", {}).get("model")
            if model:
                models.add(model)
    if models:
        print_and_collect(f"使用模型: {', '.join(models)}")

    print_and_collect()
    print_and_collect("=" * 60)
    print_and_collect("对话内容")
    print_and_collect("=" * 60)
    print_and_collect()

    # 构建对话
    conversation = build_conversation(messages)

    for msg_type, msg in conversation:
        if msg_type == "user":
            # 跳过 meta 消息（如 /clear）
            if msg.get("isMeta"):
                continue
            content = format_user_message(msg)
            if content:
                print_and_collect(f"[用户] {content}")
                print_and_collect()

        elif msg_type == "assistant":
            # 确定角色标识
            role = "助手"
            attr_agent = msg.get("attributionAgent")
            attr_skill = msg.get("attributionSkill")
            if attr_agent:
                role = f"子代理({attr_agent})"
            elif attr_skill:
                role = f"技能({attr_skill})"

            model = msg.get("model", "")
            stop = msg.get("stop_reason", "")

            # 显示 token 使用
            usage = msg.get("usage")
            usage_str = ""
            if usage:
                in_tok = usage.get("input_tokens", 0)
                out_tok = usage.get("output_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                usage_str = f" [in:{in_tok} out:{out_tok} cache:{cache_read}]"

            print_and_collect(f"[{role}] ({model}){usage_str}")

            lines = format_assistant_message(msg, show_tool_calls)
            for line in lines:
                print_and_collect(line)
            print_and_collect()

        elif msg_type == "tool_result":
            if show_tool_calls:
                lines = format_tool_result(msg, show_details=True)
                if lines:
                    for line in lines:
                        print_and_collect(line)
                    print_and_collect()

        elif msg_type == "system":
            print_and_collect(format_system_message(msg))
            print_and_collect()

        elif msg_type == "attachment":
            # 附件通常不需要显示
            pass

    # 如果指定了输出 md 文件，保存到文件
    if output_md:
        if output_md == "auto":
            # 自动生成文件名
            if session_path:
                stem = Path(session_path).stem
            else:
                stem = session_id
            md_path = Path(f"{stem}_analysis.md").resolve()
        else:
            md_path = Path(output_md).expanduser().resolve()
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"\n输出已保存到: {md_path}")


def main():
    parser = argparse.ArgumentParser(
        description="分析 Claude Code 会话历史 JSONL 文件"
    )
    parser.add_argument(
        "session_id",
        nargs="?",
        help="会话 UUID"
    )
    parser.add_argument(
        "--path",
        help="直接指定 JSONL 文件路径"
    )
    parser.add_argument(
        "--config-dir",
        default="~/.claude",
        help="Claude 配置目录，默认 ~/.claude",
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
        help="将输出保存为 Markdown 文件（不指定文件名时自动生成）"
    )

    args = parser.parse_args()

    # 验证参数
    if not args.path and not args.session_id:
        parser.error("必须提供 session_id 或 --path 参数")

    analyze_session(
        args.session_id,
        args.config_dir,
        args.tool_call_result,
        args.path,
        args.output_md
    )


if __name__ == "__main__":
    main()
