/**
 * 角色管理模块类型定义
 */

import type { RoleWithSkills } from '@/shared/adapters/roleAdapter';
import type { AgentPlatform } from '@/shared/types/api-schemas';

/**
 * 聚合后的团队数据（包含完整的成员角色对象）
 */
export interface TeamWithMembers {
  name: string;
  members: RoleWithSkills[];
}

/**
 * 创建角色表单数据
 */
export interface CreateRoleFormData {
  name: string;
  platform: AgentPlatform;
  avatar: string | null;
  description: string;
  skills: string[];
  enabled_tools: string[];
}

/**
 * Tab 类型
 */
export type RoleManagementTab = 'teams' | 'roles';

/**
 * 添加成员模式
 */
export type AddMemberMode = 'existing' | 'create';

// Re-export adapter types for convenience
export type { RoleWithSkills };
