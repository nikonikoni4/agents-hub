"""
常量定义

定义系统中使用的常量。
"""

# 压缩阈值（token 数量）
MAX_TOKEN = 1000

# 本地数据存储路径
LOCAL_DATA_PATH = "local_data"

"""
本地数据存储结构：

local_data/
├── agents/                        # Agent 工作目录
│   └── <role_name>/
│       └── <work_root>/
│
└── teams/                         # Team 数据
    └── <team_name>/
        └── <project_path>/
            └── <group_chat_id>/
                ├── <group_chat_id>.jsonl          # 群聊消息历史
                ├── agent_session_state.json       # Agent session 和上下文状态
                └── memory/
                    └── compact_history.jsonl      # 压缩历史

<group_chat_id>.jsonl 格式：
{
    "_type": "meta_data",
    "last_compact_loc": <int>,
    "created_at": <iso_timestamp>,
    "updated_at": <iso_timestamp>
}
{
    "agent_name": <str>,
    "content": <str>,
    "timestamp": <iso_timestamp>,
    "platform": <str>
}

agent_session_state.json 格式：
{
    "<agent_name>": {
        "main_session": <session_id>,
        "btw_session": [<btw_session_id>, ...],
        "context_state": {
            "last_loaded_compact_index": <int>,
            "last_loaded_message_index": <int>
        }
    }
}

compact_history.jsonl 格式：
{
    "create_at": <iso_timestamp>,
    "content": {
        "summary": <str>,
        "<agent_name>": <str>,
        ...
    }
}

<project_path> 解析规则：
传入的 project_path str 将 / : \\ 转化为 -
"""
