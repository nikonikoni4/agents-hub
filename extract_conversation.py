import json
import sys

def extract_user_decisions(jsonl_path):
    """Extract user messages that contain decision-making content"""

    key_terms = {
        'file_types': ['代码文件', '文档文件', '.py', '.md', '.txt'],
        'data_collection': ['Agent 传入', 'git range', '文件列表'],
        'data_structure': ['diff_available', 'diff_error', 'snapshot_id', 'modified_files'],
        'caching': ['后端缓存', '前端缓存', 'local_data'],
        'module': ['foundation', 'mcp', 'service'],
        'ui': ['折叠', '展开', '文件卡片', 'FileChangesCard', '预览', 'Diff']
    }

    decisions = []

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                data = json.loads(line)
                msg_type = data.get('type')

                # Extract user messages
                if msg_type == 'user':
                    msg = data.get('message', {})
                    if isinstance(msg, dict):
                        content = msg.get('content', [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    text = item.get('text', '')

                                    # Check if this message contains decision keywords
                                    for category, terms in key_terms.items():
                                        if any(term in text for term in terms):
                                            decisions.append({
                                                'line': i + 1,
                                                'category': category,
                                                'text': text[:1000]
                                            })
                                            break

                # Also extract assistant messages with options
                elif msg_type == 'assistant':
                    text = data.get('text', '')
                    if any(marker in text for marker in ['选项', 'Option', '方案 A', '方案 B', '方案 C']):
                        decisions.append({
                            'line': i + 1,
                            'category': 'options_presented',
                            'text': text[:2000]
                        })

            except Exception as e:
                continue

    return decisions

if __name__ == '__main__':
    jsonl_path = r'D:\数据文档\claude_yunyi\projects\D--desktop------agents-hub--claude-worktrees-task-3-file-diff\669376d0-36c5-47a0-94d2-7a77889b9e7f.jsonl'

    decisions = extract_user_decisions(jsonl_path)

    print(f"Found {len(decisions)} decision-related messages\n")

    for d in decisions[:20]:
        print(f"=== Line {d['line']} - Category: {d['category']} ===")
        print(d['text'])
        print("\n" + "="*80 + "\n")
