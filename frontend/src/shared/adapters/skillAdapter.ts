/**
 * Skill 相关 Adapter
 *
 * 提供 Skill API 响应到 Domain 类型的转换和聚合功能
 */

import type { SkillApiItem, RoleSkillApiItem } from '@/shared/types/api-schemas';

// TODO: 需要时在 types/domain.ts 中定义 Domain 类型
// import type { SkillDetail } from '@/shared/types/domain';

// ==================== 基础转换函数 ====================

/**
 * 将 API Skill 响应转换为前端业务模型
 *
 * @param apiSkill - API 响应的 Skill 数据
 * @returns 前端业务模型
 *
 * @example
 * const apiSkill = await getSkill('code-review');
 * const skill = adaptSkill(apiSkill);
 */
export function adaptSkill(apiSkill: SkillApiItem) {
  // TODO: 实现转换逻辑
  // 示例：
  // return {
  //   id: apiSkill.name,
  //   displayName: apiSkill.name,
  //   description: apiSkill.description,
  // };
  return apiSkill;
}

/**
 * 批量转换 Skill 列表
 *
 * @param apiSkills - API 响应的 Skill 列表
 * @returns 前端业务模型列表
 */
export function adaptSkillList(apiSkills: SkillApiItem[]) {
  return apiSkills.map(adaptSkill);
}

/**
 * 将 API 角色 Skill 响应转换为前端业务模型
 *
 * @param apiRoleSkill - API 响应的角色 Skill 数据
 * @returns 前端业务模型
 *
 * @example
 * const apiSkills = await getRoleSkills('Developer');
 * const skills = apiSkills.map(adaptRoleSkill);
 */
export function adaptRoleSkill(apiRoleSkill: RoleSkillApiItem) {
  // TODO: 实现转换逻辑
  // 示例：
  // return {
  //   id: apiRoleSkill.id,
  //   name: apiRoleSkill.name,
  //   description: apiRoleSkill.description,
  // };
  return apiRoleSkill;
}

/**
 * 批量转换角色 Skill 列表
 *
 * @param apiRoleSkills - API 响应的角色 Skill 列表
 * @returns 前端业务模型列表
 */
export function adaptRoleSkillList(apiRoleSkills: RoleSkillApiItem[]) {
  return apiRoleSkills.map(adaptRoleSkill);
}

// ==================== 聚合函数 ====================

/**
 * 聚合：获取 Skill 及其使用该 Skill 的角色列表
 *
 * @param skillName - Skill 名称
 * @returns Skill 及其使用者的聚合数据
 *
 * @example
 * const skillWithUsers = await aggregateSkillWithUsers('code-review');
 * console.log(skillWithUsers.skill);
 * console.log(skillWithUsers.usedByRoles);
 */
export async function aggregateSkillWithUsers(_skillName: string) {
  // TODO: 实现聚合逻辑
  // 示例：
  // const [skillData, rolesData] = await Promise.all([
  //   getSkill(skillName),
  //   listRoles(), // 获取所有角色
  // ]);
  //
  // // 过滤出使用该 Skill 的角色
  // const usedByRoles = await Promise.all(
  //   rolesData.map(async (role) => {
  //     const skills = await getRoleSkills(role.name);
  //     return skills.some(s => s.name === skillName) ? role : null;
  //   })
  // ).then(roles => roles.filter(Boolean));
  //
  // return {
  //   skill: adaptSkill(skillData),
  //   usedByRoles: usedByRoles.map(adaptRole),
  // };

  throw new Error('aggregateSkillWithUsers not implemented');
}
