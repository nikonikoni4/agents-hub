"""Claude Code session JSONL parser.

Parses raw Claude Code session logs and extracts meaningful conversation data,
filtering out operational noise (hooks, attachments, system events, queue ops).

Usage:
    python claude_code_session_parser.py <input.jsonl> [-o output.jsonl]
    python claude_code_session_parser.py 927e0e2c-2c69-40d4-9e6a-f494a92efe4a.jsonl

Output format — one JSON object per line:
    {
        "turn_id": 1,
        "role": "user" | "assistant",
        "timestamp": "2026-05-31T06:49:29.764Z",
        "content": [
            {"type": "text", "text": "..."},
            {"type": "tool_use", "id": "...", "name": "Read", "input": {...}},
            {"type": "tool_result", "tool_use_id": "...", "content": "..."}
        ],
        "prompt_id": "..."        // only for user messages
        "attribution_skill": "..." // only for assistant messages triggered by a skill
    }

Filtered entry types:
    - attachment (hook_success, hook_additional_context, skill_listing,
      command_permissions, nested_memory, task_reminder)
    - system (stop_hook_summary)
    - queue-operation, mode, custom-title, last-prompt
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


# Entry types that carry conversation content
_MEANINGFUL_TYPES = {"user", "assistant"}

# Entry types to silently skip
_NOISE_TYPES = {
    "attachment", "system", "queue-operation",
    "mode", "custom-title", "last-prompt",
}

# Patterns for --clean mode: strip injected boilerplate from user text
_RE_COMMAND_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.DOTALL)
_RE_COMMAND_TAGS = re.compile(
    r"<command-(?:message|name)>.*?</command-(?:message|name)>",
    re.DOTALL,
)
_RE_SKILL_BLOCK = re.compile(
    r"Base directory for this skill:.*$",
    re.DOTALL,
)
_RE_SYSTEM_REMINDER = re.compile(
    r"<system-reminder>.*?</system-reminder>",
    re.DOTALL,
)
_RE_INTERRUPTED = re.compile(r"^\[Request interrupted by user\]\s*$")


def _clean_text(text: str) -> str:
    """Strip injected boilerplate from user-facing text (clean mode).

    Extracts command-args (the user's actual message) and removes skill
    instructions, system-reminders, and other injected content.
    """
    # Extract command-args content (the user's real input)
    args_match = _RE_COMMAND_ARGS.search(text)
    if args_match:
        text = args_match.group(1)
    # Strip remaining noise
    text = _RE_COMMAND_TAGS.sub("", text)
    text = _RE_SKILL_BLOCK.sub("", text)
    text = _RE_SYSTEM_REMINDER.sub("", text)
    text = _RE_INTERRUPTED.sub("", text)
    return text.strip()


def _extract_content(message: dict, clean: bool = False) -> list[dict]:
    """Extract clean content items from a message object.

    Filters out noise content types (e.g. system-reminder tags injected
    into user messages) while preserving text, tool_use, and tool_result.
    """
    raw = message.get("content", [])
    items: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")

        if item_type == "text":
            text = item.get("text", "")
            if text:
                if clean:
                    text = _clean_text(text)
                if text:
                    items.append({"type": "text", "text": text})

        elif item_type == "tool_use":
            items.append({
                "type": "tool_use",
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "input": item.get("input", {}),
            })

        elif item_type == "tool_result":
            content = item.get("content", "")
            # content can be a string or a list of content blocks
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = "\n".join(text_parts)
            items.append({
                "type": "tool_result",
                "tool_use_id": item.get("tool_use_id", ""),
                "content": content,
            })

    return items


def parse_session(path: str | Path, clean: bool = False) -> list[dict]:
    """Parse a Claude Code session JSONL file into clean conversation turns.

    Args:
        path: Path to the session .jsonl file.
        clean: If True, strip injected boilerplate (skill instructions,
               command tags, system-reminder blocks) from user text.

    Returns a list of turn dicts, one per line that carries conversation content.
    """
    turns: list[dict] = []
    turn_counter = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)

            entry_type = entry.get("type")
            if entry_type in _NOISE_TYPES:
                continue
            if entry_type not in _MEANINGFUL_TYPES:
                continue

            message = entry.get("message", {})
            content = _extract_content(message, clean=clean)
            if not content:
                continue

            turn_counter += 1
            turn: dict[str, Any] = {
                "turn_id": turn_counter,
                "role": entry_type,
                "timestamp": entry.get("timestamp", ""),
                "content": content,
            }

            # User messages may carry a prompt_id linking request→response
            prompt_id = entry.get("promptId")
            if prompt_id:
                turn["prompt_id"] = prompt_id

            # Assistant messages may be attributed to a skill
            skill = entry.get("attributionSkill")
            if skill:
                turn["attribution_skill"] = skill

            turns.append(turn)

    return turns


def parse_session_meta(path: str | Path) -> dict:
    """Extract session-level metadata from the first entry that has full info."""
    meta: dict = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            sid = entry.get("sessionId")
            if sid and "sessionId" not in meta:
                meta["session_id"] = sid
            # Version/cwd/gitBranch only appear on certain entry types
            if entry.get("version") and "version" not in meta:
                meta["version"] = entry.get("version", "")
                meta["cwd"] = entry.get("cwd", "")
                meta["git_branch"] = entry.get("gitBranch", "")
                meta["entrypoint"] = entry.get("entrypoint", "")
                break
    return meta


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parse Claude Code session JSONL")
    parser.add_argument("input", help="Path to the session .jsonl file")
    parser.add_argument("-o", "--output", help="Output path (default: stdout)")
    parser.add_argument(
        "--clean", action="store_true",
        help="Strip injected boilerplate (skill instructions, command tags, system-reminders)",
    )
    args = parser.parse_args()

    meta = parse_session_meta(args.input)
    turns = parse_session(args.input, clean=args.clean)

    result = {
        "meta": meta,
        "turn_count": len(turns),
        "turns": turns,
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {len(turns)} turns to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
