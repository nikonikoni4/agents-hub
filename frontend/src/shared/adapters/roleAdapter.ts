/**
 * 角色相关 Adapter
 *
 * 提供 Role API 响应到 Domain 类型的转换和聚合功能
 */

import type { RoleApiResponse } from '@/shared/types/api-schemas';

// TODO: 需要时在 types/domain.ts 中定义 TeamMember 类型
// import type { TeamMember } from '@/shared/types/domain';

// ==================== 基础转换函数 ====================

/**
 * 将 API 角色响应转换为前端业务模型
 *
 * @param apiRole - API 响应的角色数据
 * @returns 前端业务模型
 *
 * @example
 * const apiRole = await getRoleInfo('Leader');
 * const teamMember = adaptRole(apiRole);
 */
export function adaptRole(apiRole: RoleApiResponse) {
  // TODO: 实现转换逻辑
  // 示例：
  // return {
  //   id: apiRole.name,
  //   displayName: apiRole.name,
  //   skills: apiRole.abilities,
  //   isLeader: apiRole.type === 'leader',
  //   ...
  // };
  return apiRole;
}

/**
 * 批量转换角色列表
 *
 * @param apiRoles - API 响应的角色列表
 * @returns 前端业务模型列表
 */
export function adaptRoleList(apiRoles: RoleApiResponse[]) {
  return apiRoles.map(adaptRole);
}

// ==================== 聚合函数 ====================

/**
 * 聚合：获取角色及其关联的 Skills 详情
 *
 * @param roleName - 角色名称
 * @returns 角色及其 Skills 的聚合数据
 *
 * @example
 * const roleWithSkills = await aggregateRoleWithSkills('Leader');
 * console.log(roleWithSkills.skills); // Skills 详情列表
 */
export async function aggregateRoleWithSkills(_roleName: string) {
  // TODO: 实现聚合逻辑
  // 示例：
  // const [roleData, skillsData] = await Promise.all([
  //   getRoleInfo(roleName),
  //   getRoleSkills(roleName),
  // ]);
  //
  // return {
  //   ...adaptRole(roleData),
  //   skillDetails: skillsData.map(adaptSkill),
  // };

  throw new Error('aggregateRoleWithSkills not implemented');
}
