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

// ==================== 通用类型 ====================

/**
 * 上传文件信息
 */
export interface UploadedFileInfo {
  file_name: string; // 原始文件名
  file_path: string; // 存储路径（相对于项目根目录）
  file_type: string; // 文件类型（mime type）
  file_size: number; // 文件大小（字节）
}

// ==================== 枚举类型 ====================

/**
 * Agent 平台类型
 * 对应后端枚举
 */
export type AgentPlatform = 'claude' | 'codex' | 'opencode';

/**
 * 角色类型
 * 对应后端枚举
 */
export type RoleType = 'leader' | 'team_member' | 'system';

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
 * 文件修改信息
 * 对应后端: FileMetadata dataclass
 */
export interface ModifiedFileInfo {
  /** 文件路径（相对于 cwd） */
  path: string;
  /** 文件状态 */
  status: 'added' | 'modified' | 'deleted';
  /** 新增行数 */
  additions: number;
  /** 删除行数 */
  deletions: number;
  /** 快照 ID */
  snapshot_id: string;
  /** diff 是否可用 */
  diff_available: boolean;
  /** diff 错误信息（如果有） */
  diff_error: string | null;
}

/**
 * 权限请求信息
 * 对应后端: PermissionRequestInfo schema
 */
export interface PermissionRequestInfo {
  /** 权限请求唯一 ID */
  request_id: string;
  /** 权限请求标题 */
  title: string;
  /** 权限请求详细描述 */
  content: string;
  /** 请求状态 */
  status: 'pending' | 'approved' | 'rejected';
  /** 请求发起者名称 */
  requested_by: string;
}

/**
 * 消息信息
 * 对应后端: MessageInfo schema
 */
export interface MessageApiItem {
  /** 消息自增 id */
  id: number;
  /** 发送者名称（agent 角色名或 'user'） */
  speaker: string;
  /** 消息内容 */
  content: string;
  /** 时间戳（ISO 8601 格式） */
  timestamp: string;
  /** 来源平台 */
  platform: string;
  /** 文件列表 */
  files?: UploadedFileInfo[];
  /** 当前工作目录 */
  cwd?: string;
  /** 文件修改信息列表 */
  modified_files?: ModifiedFileInfo[];
  /** git diff 范围（如：refs/heads/main...HEAD） */
  git_diff_range?: string;
  /** 权限请求信息（仅权限请求消息包含） */
  permission_request?: PermissionRequestInfo;
  /** 网页预览信息 */
  web_preview?: WebPreviewInfo;
  /** 工具调用列表 */
  tool_calls?: ToolCall[];
}

/**
 * 网页预览信息
 * 对应后端: WebPreviewInfo schema
 */
export interface WebPreviewInfo {
  /** 预览页面 URL */
  url: string;
  /** 页面标题 */
  title?: string;
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
  /** 关联的 Skills */
  skills: RoleSkillApiItem[];
  /** 禁用的工具列表 */
  disabled_tools: string[];
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
  /** Agent 状态：idle/busy */
  status: 'idle' | 'busy';
  /** 上下文窗口大小（单位: K tokens），null 表示未知 */
  context_window: number | null;
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

// ==================== 置顶消息相关 ====================

/**
 * 置顶消息信息
 * 对应后端: PinnedMessageInfo schema
 * GET /pinned-messages 响应列表项
 */
export interface PinnedMessageInfo {
  /** 消息 id */
  message_id: number;
  /** 发送者名称（agent 角色名或 'user'） */
  speaker: string;
  /** 消息内容 */
  content: string;
  /** 消息时间戳（ISO 8601 格式） */
  timestamp: string;
  /** 来源平台 */
  platform: string;
  /** 置顶时间（ISO 8601 格式） */
  pinned_at: string;
}

/**
 * 置顶消息请求
 * 对应后端: PinMessageRequest schema
 * POST /pinned-messages 请求体
 */
export interface PinMessageRequest {
  /** 消息 id */
  message_id: number;
}

/**
 * 置顶操作响应
 * 对应后端: PinOperationResponse schema
 * POST/DELETE /pinned-messages 成功响应
 */
export interface PinOperationResponse {
  /** 操作是否成功 */
  ok: boolean;
}

// ==================== 群成员管理相关 ====================

/**
 * 添加群成员请求
 * 对应后端: AddMembersRequest schema
 * POST /group-chats/{id}/members 请求体
 */
export interface AddMembersRequest {
  /** 成员角色名列表 */
  member_names: string[];
}

// ==================== Agent Call 相关 ====================

/**
 * Agent 调用信息
 * 对应后端: AgentCall dataclass
 */
export interface AgentCallInfo {
  /** 调用 ID */
  call_id: string;
  /** 发送者名称 */
  send_from: string;
  /** 接收者名称 */
  send_to: string;
  /** 消息内容 */
  content: string;
  /** 消息类型 */
  message_type: MessageType;
  /** 调用状态 */
  status: CallStatus;
  /** 创建时间（ISO 8601 格式） */
  created_at: string;
  /** 开始执行时间（ISO 8601 格式） */
  started_at: string | null;
  /** 完成时间（ISO 8601 格式） */
  completed_at: string | null;
  /** 错误信息 */
  error: string | null;
}

// ==================== 任务相关 ====================

/**
 * 任务信息
 * 对应后端: Task dataclass
 */
export interface TaskInfo {
  /** 任务 ID */
  task_id: string;
  /** 负责人名称 */
  owner: string;
  /** 任务内容 */
  content: string;
  /** 任务状态 */
  status: TaskStatus;
  /** 创建者名称 */
  created_by: string;
  /** 创建时间（ISO 8601 格式） */
  created_at: string;
  /** 更新时间（ISO 8601 格式） */
  updated_at: string;
}

/**
 * 任务列表信息
 * 对应后端: TaskList dataclass
 */
export interface TaskListInfo {
  /** 列表 ID */
  list_id: string;
  /** 列表状态 */
  status: 'active' | 'archived';
  /** 任务列表 */
  tasks: TaskInfo[];
  /** 创建时间（ISO 8601 格式） */
  created_at: string;
}

// ==================== 单聊相关 ====================

/** 单聊创建类型 */
export type SingleChatType = 'new' | 'fork' | 'continue_group_chat';

/** 单聊详情响应 - 对应后端 SingleChatResponse */
export interface SingleChatApiResponse {
  single_chat_id: string;
  single_chat_name: string;
  type: SingleChatType;
  agent_name: string;
  platform: AgentPlatform;
  session_id: string | null;
  group_chat_id: string | null;
  cwd: string;
  created_at: string;
  last_active_at: string;
}

/** 创建单聊响应 - 对应后端 CreateSingleChatResponse */
export interface CreateSingleChatApiResponse {
  single_chat_id: string;
  single_chat_name: string;
  type: SingleChatType;
}

/** 工具调用信息 */
export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
}

/** 单聊消息 - 对应后端 SessionMessageResponse */
export interface SingleChatMessageApiItem {
  id: string;
  role: string;
  content: string;
  timestamp: string;
  model: string | null;
  tool_calls?: ToolCall[];
}

// ==================== 工具目录相关 ====================

/**
 * 工具信息
 * 对应后端: ToolInfoResponse schema
 */
export interface ToolInfoResponse {
  name: string;
  description: string;
}

/**
 * 工具分组信息
 * 对应后端: ToolGroupResponse schema
 */
export interface ToolGroupResponse {
  name: string;
  icon: string;
  tools: ToolInfoResponse[];
}

/**
 * 工具目录响应
 * 对应后端: ToolCatalogResponse schema
 */
export interface ToolCatalogResponse {
  groups: ToolGroupResponse[];
}
