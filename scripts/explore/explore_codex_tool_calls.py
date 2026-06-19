"""探索 Codex session 文件中的工具调用格式

用法: python scripts/explore/explore_codex_tool_calls.py
"""
import json
from pathlib import Path

SESSION_FILE = Path(
    r"D:\desktop\软件开发\agents-hub\local_data\agents\通用审查助手\work_root\sessions\2026\06\19"
    r"\rollout-2026-06-19T08-52-08-019edd5d-207f-7273-9784-e7275f1e04a2.jsonl"
)


def load_lines(path: Path) -> list[dict]:
    messages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def analyze_types(messages: list[dict]):
    """统计所有事件类型"""
    types: dict[str, int] = {}
    for msg in messages:
        t = msg.get("type", "?")
        if t == "response_item":
            pt = msg.get("payload", {}).get("type", "?")
            key = f"response_item.{pt}"
        else:
            key = t
        types[key] = types.get(key, 0) + 1

    print("=" * 60)
    print("事件类型统计")
    print("=" * 60)
    for k, v in sorted(types.items()):
        print(f"  {k}: {v}")
    print()


def analyze_function_calls(messages: list[dict]):
    """分析 function_call 类型的结构"""
    calls = []
    for msg in messages:
        if msg.get("type") != "response_item":
            continue
        payload = msg.get("payload", {})
        if payload.get("type") == "function_call":
            args_str = payload.get("arguments", "{}")
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {}
            calls.append({
                "name": payload.get("name", ""),
                "call_id": payload.get("call_id", ""),
                "arguments": args,
            })

    print("=" * 60)
    print(f"function_call 统计: 共 {len(calls)} 个")
    print("=" * 60)

    # 按 name 分组
    by_name: dict[str, int] = {}
    for c in calls:
        by_name[c["name"]] = by_name.get(c["name"], 0) + 1

    print("\n工具调用分布:")
    for name, count in sorted(by_name.items(), key=lambda x: -x[1]):
        print(f"  {name}: {count}")

    # 展示前 3 个示例
    print("\n前 3 个 function_call 示例:")
    for i, c in enumerate(calls[:3]):
        print(f"\n  [{i+1}] name={c['name']}, call_id={c['call_id']}")
        args_preview = json.dumps(c["arguments"], ensure_ascii=False)
        print(f"      arguments: {args_preview[:200]}")


def analyze_message_items(messages: list[dict]):
    """分析 message 类型的结构"""
    items = []
    for msg in messages:
        if msg.get("type") != "response_item":
            continue
        payload = msg.get("payload", {})
        if payload.get("type") == "message":
            items.append(payload)

    print()
    print("=" * 60)
    print(f"message 统计: 共 {len(items)} 个")
    print("=" * 60)

    by_role: dict[str, int] = {}
    for item in items:
        role = item.get("role", "?")
        by_role[role] = by_role.get(role, 0) + 1

    print("\n角色分布:")
    for role, count in sorted(by_role.items()):
        print(f"  {role}: {count}")

    # 检查 content 结构
    print("\nassistant message content block types:")
    for item in items:
        if item.get("role") == "assistant":
            content = item.get("content", [])
            block_types = [b.get("type", "?") for b in content]
            print(f"  block_types: {block_types}")
            break


def simulate_current_parser(messages: list[dict]):
    """模拟当前 parse_codex_session 逻辑"""
    print()
    print("=" * 60)
    print("模拟当前 parse_codex_session 逻辑")
    print("=" * 60)

    _VALID_ROLES = frozenset({"user", "assistant", "system", "tool"})
    result = []

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")
        if msg_type != "response_item":
            continue
        payload = msg.get("payload", {})
        pt = payload.get("type", "")

        # 当前代码只处理 content 数组中的 block
        if pt == "message":
            role = payload.get("role", "")
            if role not in _VALID_ROLES:
                continue
            texts = []
            tool_calls = []
            for block in payload.get("content", []):
                bt = block.get("type", "")
                if bt in ("input_text", "output_text"):
                    texts.append(block.get("text", ""))
                elif bt == "tool_use":
                    tool_calls.append({
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input", {}),
                    })

            if texts or tool_calls:
                result.append({
                    "role": role,
                    "content_preview": "\n".join(texts)[:100],
                    "tool_calls_count": len(tool_calls),
                })

    print(f"\n当前解析结果: {len(result)} 条消息")
    print(f"其中包含 tool_calls 的: {sum(1 for r in result if r['tool_calls_count'] > 0)} 条")
    print("\n结论: 当前代码只处理 message.content 中的 tool_use block。")
    print("Codex 的 function_call 是顶层 response_item，不在 message.content 中。")
    print("因此当前 parse_codex_session 无法提取 Codex 的工具调用！")


def simulate_fixed_parser(messages: list[dict]):
    """模拟修复后的解析逻辑"""
    print()
    print("=" * 60)
    print("模拟修复后的 parse_codex_session 逻辑")
    print("=" * 60)

    _VALID_ROLES = frozenset({"user", "assistant", "system", "tool"})
    result = []
    # 收集所有 function_call，按 turn 分组
    pending_tool_calls: dict[str, dict] = {}  # call_id -> tool_call_info

    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")
        if msg_type != "response_item":
            continue
        payload = msg.get("payload", {})
        pt = payload.get("type", "")

        if pt == "message":
            role = payload.get("role", "")
            if role not in _VALID_ROLES:
                continue
            texts = []
            for block in payload.get("content", []):
                bt = block.get("type", "")
                if bt in ("input_text", "output_text"):
                    texts.append(block.get("text", ""))

            if texts:
                result.append({
                    "role": role,
                    "content": "\n".join(texts)[:100],
                    "tool_calls": None,
                })

        elif pt == "function_call":
            call_id = payload.get("call_id", "")
            name = payload.get("name", "")
            try:
                args = json.loads(payload.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            pending_tool_calls[call_id] = {
                "id": call_id,
                "name": name,
                "input": args,
            }

        elif pt == "function_call_output":
            # 当遇到 output 时，将对应的 function_call 附加到最近的 assistant 消息
            call_id = payload.get("call_id", "")
            if call_id in pending_tool_calls:
                tc = pending_tool_calls.pop(call_id)
                # 找最近的 assistant 消息
                for r in reversed(result):
                    if r["role"] == "assistant":
                        if r["tool_calls"] is None:
                            r["tool_calls"] = []
                        r["tool_calls"].append(tc)
                        break

    print(f"\n修复后解析结果: {len(result)} 条消息")
    tc_count = sum(1 for r in result if r.get("tool_calls"))
    print(f"其中包含 tool_calls 的: {tc_count} 条")

    print("\n带 tool_calls 的消息:")
    for r in result:
        if r.get("tool_calls"):
            names = [tc["name"] for tc in r["tool_calls"]]
            print(f"  role={r['role']}, tools={names}")


if __name__ == "__main__":
    messages = load_lines(SESSION_FILE)
    print(f"加载 {len(messages)} 条记录\n")

    analyze_types(messages)
    analyze_function_calls(messages)
    analyze_message_items(messages)
    simulate_current_parser(messages)
    simulate_fixed_parser(messages)

    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("""
Codex session 格式与 Claude 完全不同:

| 特征 | Claude | Codex |
|------|--------|-------|
| 工具调用位置 | assistant message 的 content block | 顶层 response_item |
| 类型标识 | block.type = "tool_use" | payload.type = "function_call" |
| 参数字段 | block.input (dict) | payload.arguments (JSON string) |
| ID 字段 | block.id | payload.call_id |
| 结果格式 | tool result message | response_item.function_call_output |

当前 parse_codex_session() 中的 tool_use 处理永远无法触发。
需要重构为处理顶层 function_call response_item。
""")
