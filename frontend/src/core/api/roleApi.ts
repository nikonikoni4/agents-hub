/**
 * 角色管理相关 API 接口
 *
 * 提供角色的 CRUD 操作和 Skill 关联管理
 */

import apiClient, { mockableRequest } from './client';
import type { RoleApiResponse, RoleSkillApiItem } from '@/shared/types/api-schemas';
import type {
  CreateRoleRequest,
  UpdateRoleRequest,
  AddSkillRequest,
  DeleteResponse,
} from '@/shared/types/api-requests';

// ==================== Mock 数据 ====================

// SVG 头像内容（存储完整 SVG 字符串）
const AVATAR_CIRCLE =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="30" fill="#4F46E5"/><circle cx="32" cy="24" r="10" fill="#fff"/><path d="M16 48c0-8.837 7.163-16 16-16s16 7.163 16 16" fill="#fff"/></svg>';

const AVATAR_SQUARE =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x="4" y="4" width="56" height="56" rx="8" fill="#059669"/><circle cx="32" cy="24" r="10" fill="#fff"/><path d="M16 48c0-8.837 7.163-16 16-16s16 7.163 16 16" fill="#fff"/></svg>';

const AVATAR_HEXAGON =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><polygon points="32,2 58,17 58,47 32,62 6,47 6,17" fill="#D97706"/><circle cx="32" cy="24" r="10" fill="#fff"/><path d="M16 48c0-8.837 7.163-16 16-16s16 7.163 16 16" fill="#fff"/></svg>';

const AVATAR_TRIANGLE =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><polygon points="32,4 60,56 4,56" fill="#DC2626"/><circle cx="32" cy="30" r="8" fill="#fff"/><path d="M20 48c0-6.627 5.373-12 12-12s12 5.373 12 12" fill="#fff"/></svg>';

const AVATAR_STAR =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><polygon points="32,2 39,24 62,24 43,38 50,60 32,46 14,60 21,38 2,24 25,24" fill="#7C3AED"/><circle cx="32" cy="28" r="8" fill="#fff"/></svg>';

const MOCK_ROLES: RoleApiResponse[] = [
  {
    name: 'Leader',
    platform: 'claude',
    avatar: AVATAR_CIRCLE,
    abilities: ['任务分派', '团队协调', '进度管理'],
    type: 'leader',
    scope: null,
    description: '团队领导者，负责任务分配和协调',
  },
  {
    name: 'Designer',
    platform: 'claude',
    avatar: AVATAR_SQUARE,
    abilities: ['UI设计', 'UX设计', '原型制作'],
    type: 'team_member',
    scope: null,
    description: '设计师，负责界面和交互设计',
  },
  {
    name: 'Developer',
    platform: 'codex',
    avatar: AVATAR_HEXAGON,
    abilities: ['代码编写', '代码审查', '单元测试'],
    type: 'team_member',
    scope: null,
    description: '开发工程师，负责代码实现',
  },
  {
    name: 'Tester',
    platform: 'claude',
    avatar: AVATAR_TRIANGLE,
    abilities: ['测试用例编写', '缺陷发现', '回归测试'],
    type: 'team_member',
    scope: null,
    description: '测试工程师，负责质量保障',
  },
];

const MOCK_NEW_ROLE: RoleApiResponse = {
  name: 'New Role',
  platform: 'claude',
  avatar: null,
  abilities: [],
  type: 'team_member',
  scope: null,
  description: 'Newly created role',
};

const MOCK_ROLE_SKILLS = new Map<string, RoleSkillApiItem[]>([
  [
    'Leader',
    [
      {
        id: 'skill-architecture',
        name: 'architecture',
        description: '系统架构分析和设计方案推荐',
      },
    ],
  ],
  [
    'Designer',
    [
      {
        id: 'skill-doc-generation',
        name: 'doc-generation',
        description: '根据代码自动生成技术文档和API说明',
      },
    ],
  ],
  [
    'Developer',
    [
      {
        id: 'skill-code-review',
        name: 'code-review',
        description: '自动化代码质量检查和最佳实践建议',
      },
      {
        id: 'skill-test-writing',
        name: 'test-writing',
        description: '智能生成单元测试和集成测试用例',
      },
    ],
  ],
]);

const MOCK_AVATARS: string[] = [
  AVATAR_CIRCLE,
  AVATAR_SQUARE,
  AVATAR_HEXAGON,
  AVATAR_TRIANGLE,
  AVATAR_STAR,
];

const MOCK_SKILL: RoleSkillApiItem = {
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
export async function createRole(data: CreateRoleRequest): Promise<RoleApiResponse> {
  return mockableRequest(() => apiClient.post<RoleApiResponse>('/roles', data), MOCK_NEW_ROLE);
}

/**
 * 获取单个角色信息
 */
export async function getRoleInfo(name: string): Promise<RoleApiResponse> {
  const mockRole = MOCK_ROLES.find((r) => r.name === name);
  return mockableRequest(
    () => apiClient.get<RoleApiResponse>(`/roles/${name}`),
    mockRole ?? MOCK_ROLES[0]!
  );
}

/**
 * 列出所有角色
 */
export async function listRoles(): Promise<RoleApiResponse[]> {
  return mockableRequest(() => apiClient.get<RoleApiResponse[]>('/roles'), MOCK_ROLES);
}

/**
 * 更新角色信息
 */
export async function updateRole(name: string, data: UpdateRoleRequest): Promise<RoleApiResponse> {
  return mockableRequest(
    () => apiClient.patch<RoleApiResponse>(`/roles/${name}`, data),
    MOCK_ROLES[0]!
  );
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
export async function getRoleSkills(name: string): Promise<RoleSkillApiItem[]> {
  return mockableRequest(
    () => apiClient.get<RoleSkillApiItem[]>(`/roles/${name}/skills`),
    MOCK_ROLE_SKILLS.get(name) ?? []
  );
}

/**
 * 为角色添加 Skill
 */
export async function addSkillToRole(name: string, skillId: string): Promise<RoleSkillApiItem> {
  const requestData: AddSkillRequest = { skill_id: skillId };
  return mockableRequest(
    () => apiClient.post<RoleSkillApiItem>(`/roles/${name}/skills`, requestData),
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
