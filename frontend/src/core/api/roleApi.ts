/**
 * 角色管理相关 API 接口
 *
 * 提供角色的 CRUD 操作和 Skill 关联管理
 */

import apiClient, { mockableRequest } from './client';
import type { Role, RoleSkill } from '@/shared/types/models';
import type {
  CreateRoleRequest,
  UpdateRoleRequest,
  AddSkillRequest,
  DeleteResponse,
} from '@/shared/types/api';

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

const MOCK_NEW_ROLE: Role = {
  name: 'New Role',
  platform: 'claude',
  avatar: null,
  abilities: [],
  type: 'team_member',
  scope: null,
  description: 'Newly created role',
};

const MOCK_ROLE_SKILLS = new Map<string, RoleSkill[]>([
  [
    'Leader',
    [
      {
        id: 'skill-brainstorming',
        name: 'brainstorming',
        description: '头脑风暴和需求分析',
      },
    ],
  ],
  [
    'Developer',
    [
      {
        id: 'skill-tdd',
        name: 'test-driven-development',
        description: '测试驱动开发',
      },
      {
        id: 'skill-code-review',
        name: 'code-review',
        description: '代码审查',
      },
    ],
  ],
]);

const MOCK_AVATARS: string[] = [
  'avatar1.png',
  'avatar2.png',
  'avatar3.png',
  'avatar4.png',
  'avatar5.png',
];

const MOCK_SKILL: RoleSkill = {
  id: 'mock-skill',
  name: 'Mock Skill',
  description: 'A mock skill for testing',
};

const MOCK_DELETE_RESPONSE: DeleteResponse = {
  message: 'Successfully deleted',
};

// ==================== API 接口 ====================

/**
 * 创建角色
 */
export async function createRole(data: CreateRoleRequest): Promise<Role> {
  return mockableRequest(() => apiClient.post<Role>('/roles', data), MOCK_NEW_ROLE);
}

/**
 * 获取单个角色信息
 */
export async function getRoleInfo(name: string): Promise<Role> {
  const mockRole = MOCK_ROLES.find((r) => r.name === name);
  return mockableRequest(() => apiClient.get<Role>(`/roles/${name}`), mockRole ?? MOCK_ROLES[0]!);
}

/**
 * 列出所有角色
 */
export async function listRoles(): Promise<Role[]> {
  return mockableRequest(() => apiClient.get<Role[]>('/roles'), MOCK_ROLES);
}

/**
 * 更新角色信息
 */
export async function updateRole(name: string, data: UpdateRoleRequest): Promise<Role> {
  return mockableRequest(() => apiClient.patch<Role>(`/roles/${name}`, data), MOCK_ROLES[0]!);
}

/**
 * 删除角色
 */
export async function deleteRole(name: string): Promise<DeleteResponse> {
  return mockableRequest(
    () => apiClient.delete<DeleteResponse>(`/roles/${name}`),
    MOCK_DELETE_RESPONSE
  );
}

/**
 * 列出角色关联的 Skills
 */
export async function getRoleSkills(name: string): Promise<RoleSkill[]> {
  return mockableRequest(
    () => apiClient.get<RoleSkill[]>(`/roles/${name}/skills`),
    MOCK_ROLE_SKILLS.get(name) ?? []
  );
}

/**
 * 为角色添加 Skill
 */
export async function addSkillToRole(name: string, skillId: string): Promise<RoleSkill> {
  const requestData: AddSkillRequest = { skill_id: skillId };
  return mockableRequest(
    () => apiClient.post<RoleSkill>(`/roles/${name}/skills`, requestData),
    MOCK_SKILL
  );
}

/**
 * 移除角色的 Skill
 */
export async function removeSkillFromRole(name: string, skillId: string): Promise<DeleteResponse> {
  return mockableRequest(
    () => apiClient.delete<DeleteResponse>(`/roles/${name}/skills/${skillId}`),
    MOCK_DELETE_RESPONSE
  );
}

/**
 * 列出所有可用头像
 */
export async function listAvatars(): Promise<string[]> {
  return mockableRequest(() => apiClient.get<string[]>('/roles/avatars'), MOCK_AVATARS);
}
