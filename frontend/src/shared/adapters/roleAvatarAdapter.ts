/**
 * Role 头像聚合适配器
 *
 * 职责：
 * - 构建 role name → avatar 的映射表
 * - 在数据源头统一处理 null → 字符 fallback
 * - 供 session 和 chat 特性复用
 */

import { listRoles } from '@/core/api/roleApi';
import type { AvatarData } from '@/shared/types/domain';
import { buildCharAvatar, buildSvgAvatar } from '@/shared/types/domain';

/**
 * 构建角色名到头像数据的映射
 *
 * 在 adapter 层统一处理：null 转换为字符 fallback，前端组件无需判断
 *
 * @returns Map<roleName, AvatarData>
 */
export async function buildRoleAvatarMap(): Promise<Map<string, AvatarData>> {
  const roles = await listRoles();
  return new Map(
    roles.map((r) => [
      r.name,
      r.avatar ? buildSvgAvatar(r.avatar) : buildCharAvatar(r.name),
    ])
  );
}
