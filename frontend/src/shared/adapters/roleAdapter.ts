/**
 * 角色适配器 - API 响应直接包含 skills，无需聚合
 */

import { getRoleInfo, listRoles } from '@/core/api/roleApi';
import type { RoleApiResponse } from '@/shared/types/api-schemas';

/**
 * 聚合后的角色数据（API 已包含 skills，直接透传）
 */
export type RoleWithSkills = RoleApiResponse;

/**
 * 获取单个角色（含 skills）
 */
export async function aggregateRoleWithSkills(roleName: string): Promise<RoleWithSkills> {
  return getRoleInfo(roleName);
}

/**
 * 获取所有角色（含 skills）
 */
export async function aggregateAllRolesWithSkills(): Promise<RoleWithSkills[]> {
  return listRoles();
}
