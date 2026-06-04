/**
 * 角色适配器 - 聚合角色和技能数据
 */

import { getRoleInfo, getRoleSkills, listRoles } from '@/core/api/roleApi';
import type { RoleApiResponse, RoleSkillApiItem } from '@/shared/types/api-schemas';

/**
 * 聚合后的角色数据（包含技能列表）
 */
export interface RoleWithSkills extends RoleApiResponse {
  skills: RoleSkillApiItem[];
}

/**
 * 获取单个角色及其技能
 */
export async function fetchRoleWithSkills(roleName: string): Promise<RoleWithSkills> {
  const [role, skills] = await Promise.all([getRoleInfo(roleName), getRoleSkills(roleName)]);
  return { ...role, skills };
}

/**
 * 获取所有角色及其技能
 */
export async function fetchAllRolesWithSkills(): Promise<RoleWithSkills[]> {
  const roles = await listRoles();
  return Promise.all(roles.map((role) => fetchRoleWithSkills(role.name)));
}
