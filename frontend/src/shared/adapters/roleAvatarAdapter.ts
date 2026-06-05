/**
 * Role 头像聚合适配器
 *
 * 职责：
 * - 构建 role name → avatar 的映射表
 * - 供 session 和 chat 特性复用
 */

import { listRoles } from '@/core/api/roleApi';

/**
 * 构建角色名到头像 SVG 的映射
 *
 * @returns Map<roleName, avatarSvgString | null>
 */
export async function buildRoleAvatarMap(): Promise<Map<string, string | null>> {
  const roles = await listRoles();
  return new Map(roles.map((r) => [r.name, r.avatar]));
}
