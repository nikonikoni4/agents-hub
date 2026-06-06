"""读取Claude Code会话内容。

用法:
    python skills/spec-verifier/scripts/session_reader.py <session_id> <claude_config_dir>

参数:
    session_id: 会话ID
    claude_config_dir: Claude配置目录路径

输出:
    会话内容的JSON格式摘要
"""

import json
import sys
from pathlib import Path


def find_session_file(session_id: str, config_dir: Path) -> Path:
    """查找会话文件。"""
    # Claude Code的会话文件通常存储在 ~/.claude/sessions/ 目录下
    sessions_dir = config_dir / "sessions"

    if not sessions_dir.exists():
        raise FileNotFoundError(f"会话目录不存在: {sessions_dir}")

    # 查找匹配的会话文件
    for session_file in sessions_dir.glob("*.json"):
        if session_id in session_file.stem:
            return session_file

    raise FileNotFoundError(f"未找到会话: {session_id}")


def read_session_content(session_file: Path) -> dict:
    """读取会话内容。"""
    with open(session_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def extract_key_info(session_data: dict) -> dict:
    """提取关键信息。"""
    messages = session_data.get('messages', [])

    # 提取用户消息
    user_messages = []
    for msg in messages:
        if msg.get('role') == 'user':
            user_messages.append({
                'content': msg.get('content', ''),
                'timestamp': msg.get('timestamp', '')
            })

    # 提取AI生成的文档
    ai_documents = []
    for msg in messages:
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            # 检查是否包含文档内容
            if any(keyword in content.lower() for keyword in ['spec', 'plan', 'specification', 'document']):
                ai_documents.append({
                    'content': content,
                    'timestamp': msg.get('timestamp', '')
                })

    return {
        'session_id': session_data.get('session_id', ''),
        'user_messages': user_messages,
        'ai_documents': ai_documents,
        'total_messages': len(messages)
    }


def main():
    if len(sys.argv) != 3:
        print("用法: python session_reader.py <session_id> <claude_config_dir>")
        sys.exit(1)

    session_id = sys.argv[1]
    config_dir = Path(sys.argv[2])

    try:
        # 查找会话文件
        session_file = find_session_file(session_id, config_dir)
        print(f"找到会话文件: {session_file}")

        # 读取会话内容
        session_data = read_session_content(session_file)

        # 提取关键信息
        key_info = extract_key_info(session_data)

        # 输出结果
        print(json.dumps(key_info, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
