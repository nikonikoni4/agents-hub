/**
 * API 契约类型定义
 *
 * 本文件包含严格对应后端 Pydantic schemas 的 TypeScript 类型定义。
 *
 * 命名规范：
 * - Response 类型：{资源名}ApiResponse（单个资源的完整响应）
 * - List Item 类型：{资源名}ApiItem（列表中的项）
 *
 * 注意：
 * - 保持后端字段名（snake_case）
 * - 保持后端数据类型（如日期使用 string）
 * - 每个类型都标注对应的后端 schema 名称
 */

// ==================== 枚举类型 ====================

/**
 * Agent 平台类型
 * 对应后端枚举
 */
export type AgentPlatform = 'claude' | 'codex';

/**
 * 角色类型
 * 对应后端枚举
 */
export type RoleType = 'leader' | 'team_member';

/**
 * 群聊类型
 * 对应后端枚举
 * - sequence_execute: 顺序执行模式
 * - manager_orchestrate: 管理者编排模式
 */
export type GroupChatType = 'sequence_execute' | 'manager_orchestrate';

/**
 * 会话类型
 * 对应后端枚举
 * - main: 主会话
 * - btw: BTW 会话（between）
 */
export type SessionType = 'main' | 'btw';

/**
 * 消息类型
 * 对应后端枚举
 * - task: 任务消息
 * - notification: 通知消息
 */
export type MessageType = 'task' | 'notification';

/**
 * 调用状态
 * 对应后端枚举
 */
export type CallStatus = 'pending' | 'running' | 'completed' | 'failed' | 'timeout';

/**
 * 任务状态
 * 对应后端枚举
 */
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

// ==================== 消息相关 ====================

/**
 * 消息信息
 * 对应后端: MessageInfo schema
 */
export interface MessageApiItem {
  /** 发送者名称（agent 角色名或 'user'） */
  speaker: string;
  /** 消息内容 */
  content: string;
  /** 时间戳（ISO 8601 格式） */
  timestamp: string;
  /** 来源平台 */
  platform: string;
}

/**
 * Agent 内部消息
 * 对应后端: AgentMessage schema
 */
export interface AgentMessageApiItem {
  /** 调用 ID */
  call_id: string;
  /** 消息内容 */
  content: string;
  /** 发送者名称 */
  send_from: string;
  /** 接收者名称 */
  send_to: string;
  /** 会话类型 */
  session_type: SessionType;
  /** 消息类型 */
  message_type: MessageType;
  /** 时间戳（ISO 8601 格式） */
  timestamp: string;
}

// ==================== 角色相关 ====================

/**
 * 角色信息（完整响应）
 * 对应后端: RoleResponse / RoleInfo schema
 */
export interface RoleApiResponse {
  /** 角色名称（唯一标识） */
  name: string;
  /** 所属平台 */
  platform: AgentPlatform;
  /** 头像 URL */
  avatar: string | null;
  /** 能力列表 */
  abilities: string[];
  /** 角色类型 */
  type: RoleType | null;
  /** 作用域 */
  scope: string[] | null;
  /** 角色描述 */
  description: string | null;
}

/**
 * 全局 Skill 信息
 * 对应后端: SkillResponse schema（来自 /api/v1/skills）
 */
export interface SkillApiItem {
  /** Skill 名称 */
  name: string;
  /** Skill 描述 */
  description: string;
}

/**
 * 角色关联的 Skill 信息
 * 对应后端: RoleSkillResponse schema（来自 /api/v1/roles/{name}/skills）
 */
export interface RoleSkillApiItem {
  /** Skill ID */
  id: string;
  /** Skill 名称 */
  name: string;
  /** Skill 描述 */
  description: string;
}

// ==================== 群聊相关 ====================

/**
 * 群聊详细信息（完整响应）
 * 对应后端: GroupChatInfo schema
 */
export interface GroupChatApiResponse {
  /** 群聊 ID */
  group_chat_id: string;
  /** 群聊名称 */
  group_chat_name: string;
  /** 项目路径 */
  project_path: string;
  /** 创建时间（ISO 8601 格式） */
  created_at: string;
  /** 群聊类型 */
  group_type: GroupChatType;
  /** 是否活跃 */
  is_active: boolean;
}

/**
 * 群聊成员运行时信息
 * 对应后端: GroupChatMember schema
 */
export interface GroupChatMemberApiItem {
  /** 成员名称（角色名） */
  name: string;
  /** 主会话 ID */
  main_session: string | null;
  /** BTW 会话 ID 列表 */
  btw_session: string[];
  /** 当前工作目录 */
  cwd: string | null;
  /** 是否使用 Docker 沙箱 */
  use_docker: boolean;
}

// ==================== 会话相关 ====================

/**
 * Agent 上下文状态
 * 对应后端: AgentContextState schema
 */
export interface AgentContextStateApiResponse {
  /** 最后加载的紧凑索引 */
  last_loaded_compact_index: number;
  /** 最后加载的消息索引 */
  last_loaded_message_index: number;
}

/**
 * Agent 会话信息
 * 对应后端: AgentSessionInfo schema
 */
export interface AgentSessionInfoApiResponse {
  /** 主会话 ID */
  main_session: string;
  /** BTW 会话 ID 列表 */
  btw_session: string[];
  /** 上下文状态 */
  context_state: AgentContextStateApiResponse;
  /** 认证 Token */
  token: string;
  /** 当前工作目录 */
  cwd: string;
  /** 是否使用 Docker 沙箱 */
  use_docker: boolean;
}

// ==================== 团队相关 ====================

/**
 * 团队信息（完整响应）
 * 对应后端: TeamResponse schema
 */
export interface TeamApiResponse {
  /** 团队名称（唯一标识） */
  name: string;
  /** 成员角色名称列表 */
  members: string[];
}

// ==================== 配置相关 ====================

/**
 * 系统配置信息
 * 对应后端: ConfigInfo schema
 */
export interface SystemConfigApiResponse {
  /** 数据存储路径 */
  data_path: string | null;
  /** MCP 服务端口 */
  mcp_port: number;
  /** 默认用户名 */
  default_user_name: string;
  /** 是否使用 Docker 沙箱 */
  use_docker: boolean;
  /** Docker 镜像名称 */
  docker_image: string;
}

// ==================== Session 相关 ====================

/**
 * 群聊 Session 列表项（扩展版）
 * 对应后端: GroupChatInfo + 扩展字段
 * 注意：后端需要添加 last_speaker、last_message、last_update_at 字段
 */
export interface GroupChatInfoApiResponse {
  /** 群聊 ID */
  group_chat_id: string;
  /** 群聊名称 */
  group_chat_name: string;
  /** 项目路径 */
  project_path: string;
  /** 创建时间（ISO 8601 格式） */
  created_at: string;
  /** 群聊类型 */
  group_type: GroupChatType;
  /** 是否活跃 */
  is_active: boolean;

  // Session 列表扩展字段（后端待添加）
  /** 最后发言者 */
  last_speaker: string | null;
  /** 最后消息内容 */
  last_message: string | null;
  /** 最后更新时间（ISO 8601 格式） */
  last_update_at: string | null;
}

/**
 * 本地存储的 last_view 记录
 * 用于计算未读状态
 */
export interface LastViewRecord {
  /** 群聊 ID */
  group_chat_id: string;
  /** 最后查看时间（ISO 8601 格式） */
  last_view_at: string;
}
