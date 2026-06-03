/**
 * 角色管理相关 API 接口
 *
 * 提供角色的 CRUD 操作和 Skill 关联管理
 */

import apiClient, { mockableRequest } from './client';
import type {
  Role,
  Skill,
  CreateRoleRequest,
  UpdateRoleRequest,
  AddSkillRequest,
} from '@/shared/types';

// ==================== Mock 数据 ====================

const MOCK_ROLES: Role[] = [
  {
    name: 'Leader',
    platform: 'claude',
    avatar: 'avatar1.png',
    abilities: ['任务分派', '团队协调', '进度管理'],
    type: 'leader',
    scope: null,
    description: '团队领导者，负责任务分配和协调',
  },
  {
    name: 'Developer',
    platform: 'codex',
    avatar: 'avatar2.png',
    abilities: ['代码编写', '代码审查', '单元测试'],
    type: 'team_member',
    scope: null,
    description: '开发工程师，负责代码实现',
  },
  {
    name: 'Tester',
    platform: 'claude',
    avatar: null,
    abilities: ['测试用例编写', '缺陷发现', '回归测试'],
    type: 'team_member',
    scope: null,
    description: '测试工程师，负责质量保障',
  },
];

const MOCK_SKILLS: Skill[] = [
  {
    id: 'skill-001',
    name: 'brainstorming',
    description: '头脑风暴和需求分析',
  },
  {
    id: 'skill-002',
    name: 'test-driven-development',
    description: '测试驱动开发',
  },
  {
    id: 'skill-003',
    name: 'code-review',
    description: '代码审查',
  },
];

const MOCK_AVATARS: string[] = [
  'avatar1.png',
  'avatar2.png',
  'avatar3.png',
  'avatar4.png',
  'avatar5.png',
];

// ==================== API 接口 ====================

/**
 * 创建角色
 */
export async function createRole(data: CreateRoleRequest): Promise<Role> {
  return mockableRequest(() => apiClient.post('/roles', data), {
    ...data,
    avatar: data.avatar || null,
    abilities: data.abilities || [],
    type: data.type || 'team_member',
    scope: data.scope || null,
    description: data.description || null,
  });
}

/**
 * 获取单个角色信息
 */
export async function getRoleInfo(name: string): Promise<Role> {
  return mockableRequest(
    () => apiClient.get(`/roles/${name}`),
    MOCK_ROLES.find((r) => r.name === name)!
  );
}

/**
 * 列出所有角色
 */
export async function listRoles(): Promise<Role[]> {
  return mockableRequest(() => apiClient.get('/roles'), MOCK_ROLES);
}

/**
 * 更新角色信息
 */
export async function updateRole(name: string, data: UpdateRoleRequest): Promise<Role> {
  return mockableRequest(() => apiClient.patch(`/roles/${name}`, data), MOCK_ROLES[0]!);
}

/**
 * 删除角色
 */
export async function deleteRole(name: string): Promise<{ message: string }> {
  return mockableRequest(() => apiClient.delete(`/roles/${name}`), {
    message: `Role '${name}' deleted successfully`,
  });
}

/**
 * 列出角色关联的 Skills
 */
export async function getRoleSkills(name: string): Promise<Skill[]> {
  return mockableRequest(() => apiClient.get(`/roles/${name}/skills`), [MOCK_SKILLS[0]!]);
}

/**
 * 为角色添加 Skill
 */
export async function addSkillToRole(name: string, skillId: string): Promise<Skill> {
  const data: AddSkillRequest = { skill_id: skillId };
  return mockableRequest(() => apiClient.post(`/roles/${name}/skills`, data), MOCK_SKILLS[0]!);
}

/**
 * 移除角色的 Skill
 */
export async function removeSkillFromRole(
  name: string,
  skillId: string
): Promise<{ message: string }> {
  return mockableRequest(() => apiClient.delete(`/roles/${name}/skills/${skillId}`), {
    message: `Skill '${skillId}' removed from role '${name}'`,
  });
}

/**
 * 列出所有可用头像
 */
export async function listAvatars(): Promise<string[]> {
  return mockableRequest(() => apiClient.get('/roles/avatars'), MOCK_AVATARS);
}
