/**
 * API 请求和响应类型定义
 *
 * 与后端 Pydantic request/response schemas 对应
 */

import type { AgentPlatform, RoleType } from './api-schemas';

// ==================== 群聊相关 ====================

/**
 * 创建群聊请求
 * 对应后端 GroupChatCreate
 */
export interface CreateGroupChatRequest {
  team_members: string[]; // 团队成员角色名列表（至少1个）
  project_path: string; // 项目路径
  group_chat_name?: string | null; // 群聊名称，不提供则使用 group_chat_id
}

/**
 * 发送消息请求
 * 对应后端 MessageCreate
 */
export interface SendMessageRequest {
  content: string; // 消息内容（非空）
  members: string[]; // 群聊中所有 agent 名称列表
}

/**
 * 切换 Docker 沙箱请求
 * 对应后端 UseDockerUpdate
 */
export interface UpdateDockerModeRequest {
  use_docker: boolean; // 是否启用 Docker 沙箱
}

// ==================== 角色相关 ====================

/**
 * 创建角色请求
 * 对应后端 RoleCreateRequest
 *
 * 注意：除 name 和 platform 外，其他字段在后端有默认值，前端可不传
 */
export interface CreateRoleRequest {
  name: string; // 必填
  platform: AgentPlatform; // 必填
  avatar?: string | null; // 可选，默认 null
  abilities?: string[]; // 可选，默认 []
  type?: RoleType | null; // 可选，默认 null
  scope?: string[] | null; // 可选，默认 null
  description?: string | null; // 可选，默认 null
}

/**
 * 更新角色请求（所有字段都是可选的）
 * 对应后端 RoleUpdateRequest
 */
export interface UpdateRoleRequest {
  avatar?: string | null;
  abilities?: string[] | null;
  description?: string | null;
}

/**
 * 添加 Skill 请求
 * 对应后端 RoleSkillRequest
 */
export interface AddSkillRequest {
  skill_id: string;
}

// ==================== Skill 相关 ====================

/**
 * 创建 Skill 请求
 * 对应后端 SkillCreateRequest
 */
export interface CreateSkillRequest {
  url: string; // skill 的网络地址
}

// ==================== 团队相关 ====================

/**
 * 创建团队请求
 * 对应后端 TeamCreateRequest
 */
export interface CreateTeamRequest {
  name: string; // 团队名称（唯一标识）
  members: string[]; // 成员角色名称列表
}

/**
 * 更新团队请求
 * 对应后端 TeamUpdateRequest
 */
export interface UpdateTeamRequest {
  name?: string | null; // 团队名称
  members?: string[] | null; // 成员角色名称列表
}

// ==================== 配置相关 ====================

/**
 * 更新系统配置请求
 * 对应后端 ConfigUpdate
 */
export interface UpdateConfigRequest {
  data_path?: string | null;
  mcp_port?: number | null; // 1-65535
  default_user_name?: string | null;
  use_docker?: boolean | null;
}

// ==================== 通用响应 ====================

/**
 * 通用成功响应
 */
export interface SuccessResponse {
  message: string;
}

/**
 * 删除操作响应
 */
export interface DeleteResponse {
  message: string;
}

/**
 * API 错误响应
 */
export interface ErrorResponse {
  error_code: string;
  message: string;
  type: string;
  details?: Record<string, any>;
}

/**
 * 角色特定错误码
 */
export enum RoleErrorCode {
  ROLE_NOT_FOUND = 'ROLE_NOT_FOUND',
  ROLE_ALREADY_EXISTS = 'ROLE_ALREADY_EXISTS',
  SKILL_NOT_FOUND = 'SKILL_NOT_FOUND',
  SKILL_ALREADY_EXISTS = 'SKILL_ALREADY_EXISTS',
  PLATFORM_CONFIG_NOT_FOUND = 'PLATFORM_CONFIG_NOT_FOUND',
}
