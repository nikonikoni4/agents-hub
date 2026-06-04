/**
 * 角色管理模块类型定义
 */

import type { RoleWithSkills } from '@/shared/adapters/roleAdapter';
import type { TeamWithMembers } from '@/shared/adapters/teamAdapter';
import type { AgentPlatform } from '@/shared/types/api-schemas';

/**
 * 创建角色表单数据
 */
export interface CreateRoleFormData {
  name: string;
  platform: AgentPlatform;
  avatar: string | null;
  description: string;
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
export type { RoleWithSkills, TeamWithMembers };
