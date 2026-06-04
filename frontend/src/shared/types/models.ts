/**
 * 核心数据模型
 *
 * 与后端 Pydantic schemas 对应的 TypeScript 类型定义
 */

// ==================== 枚举类型 ====================

export type AgentPlatform = 'claude' | 'codex';
export type RoleType = 'leader' | 'team_member';
export type GroupChatType = 'sequence_execute' | 'manager_orchestrate';
export type SessionType = 'main' | 'btw';
export type MessageType = 'task' | 'notification';
export type CallStatus = 'pending' | 'running' | 'completed' | 'failed' | 'timeout';
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

// ==================== 消息相关 ====================

/**
 * 消息信息
 * 对应后端 MessageInfo schema
 */
export interface Message {
  speaker: string; // 发送者名称（agent 角色名或 'user'）
  content: string; // 消息内容
  timestamp: string; // 时间戳
  platform: string; // 来源平台
}

/**
 * Agent 消息（内部传递）
 * 对应后端 AgentMessage
 */
export interface AgentMessage {
  call_id: string;
  content: string;
  send_from: string;
  send_to: string;
  session_type: SessionType;
  message_type: MessageType;
  timestamp: string;
}

// ==================== 角色相关 ====================

/**
 * 角色信息
 * 对应后端 RoleResponse / RoleInfo
 */
export interface Role {
  name: string;
  platform: AgentPlatform;
  avatar: string | null;
  abilities: string[];
  type: RoleType | null;
  scope: string[] | null;
  description: string | null;
}

/**
 * Agent 信息（与 Role 相同）
 */
export type Agent = Role;

/**
 * 全局 Skill 信息
 * 对应后端 SkillResponse（来自 /api/v1/skills）
 */
export interface Skill {
  name: string;
  description: string;
}

/**
 * 角色关联的 Skill 信息
 * 对应后端 RoleSkillResponse（来自 /api/v1/roles/{name}/skills）
 */
export interface RoleSkill {
  id: string;
  name: string;
  description: string;
}

// ==================== 群聊相关 ====================

/**
 * 群聊详细信息
 * 对应后端 GroupChatInfo
 */
export interface GroupChat {
  group_chat_id: string;
  group_chat_name: string;
  project_path: string;
  created_at: string;
  group_type: GroupChatType;
  is_active: boolean;
}

/**
 * 群聊摘要（列表展示）
 * 对应后端 GroupChatSummary
 */
export interface GroupChatSummary {
  group_chat_id: string;
  group_chat_name: string;
  project_path: string;
  is_active: boolean;
  created_at: string;
}

/**
 * 群聊成员运行时信息
 * 对应后端 GroupChatMember
 */
export interface GroupChatMember {
  name: string;
  main_session: string | null;
  btw_session: string[];
  cwd: string | null;
  use_docker: boolean;
}

// ==================== 会话相关 ====================

/**
 * Agent 上下文状态
 * 对应后端 AgentContextState
 */
export interface AgentContextState {
  last_loaded_compact_index: number;
  last_loaded_message_index: number;
}

/**
 * Agent 会话信息
 * 对应后端 AgentSessionInfo
 */
export interface AgentSessionInfo {
  main_session: string;
  btw_session: string[];
  context_state: AgentContextState;
  token: string;
  cwd: string;
  use_docker: boolean;
}

// ==================== 配置相关 ====================

/**
 * 系统配置信息
 * 对应后端 ConfigInfo
 */
export interface SystemConfig {
  data_path: string | null;
  mcp_port: number;
  default_user_name: string;
  use_docker: boolean;
  docker_image: string;
}
