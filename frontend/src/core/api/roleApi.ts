/**
 * 角色管理相关 API 接口
 *
 * 提供角色的 CRUD 操作和 Skill 关联管理
 */

import apiClient, { mockableRequest } from './client';
import type {
  RoleApiResponse,
  RoleSkillApiItem,
  ToolCatalogResponse,
} from '@/shared/types/api-schemas';
import type {
  CreateRoleRequest,
  UpdateRoleRequest,
  AddSkillRequest,
  DeleteResponse,
} from '@/shared/types/api-requests';

// ==================== 头像 URL 构建 ====================

const AVATAR_BASE_PATH = '/roles/avatars/files';

/**
 * 根据头像文件名构建完整的访问 URL
 *
 * 后端返回文件名（如 "circle-blue.svg"），前端通过此函数拼接完整 URL。
 */
export function buildAvatarUrl(filename: string): string {
  const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
  return `${baseURL}${AVATAR_BASE_PATH}/${filename}`;
}

// ==================== Mock 数据 ====================

const MOCK_ROLES: RoleApiResponse[] = [
  {
    name: 'Leader',
    platform: 'claude',
    avatar: 'circle-blue.svg',
    abilities: ['任务分派', '团队协调', '进度管理'],
    type: 'leader',
    scope: null,
    description: '团队领导者，负责任务分配和协调',
    skills: [
      {
        id: 'skill-architecture',
        name: 'architecture',
        description: '系统架构分析和设计方案推荐',
      },
    ],
    disabled_tools: [],
  },
  {
    name: 'Designer',
    platform: 'claude',
    avatar: 'square-green.svg',
    abilities: ['UI设计', 'UX设计', '原型制作'],
    type: 'team_member',
    scope: null,
    description: '设计师，负责界面和交互设计',
    skills: [
      {
        id: 'skill-doc-generation',
        name: 'doc-generation',
        description: '根据代码自动生成技术文档和API说明',
      },
    ],
    disabled_tools: [],
  },
  {
    name: 'Developer',
    platform: 'codex',
    avatar: 'hexagon-amber.svg',
    abilities: ['代码编写', '代码审查', '单元测试'],
    type: 'team_member',
    scope: null,
    description: '开发工程师，负责代码实现',
    skills: [
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
    disabled_tools: [],
  },
  {
    name: 'Tester',
    platform: 'claude',
    avatar: 'triangle-red.svg',
    abilities: ['测试用例编写', '缺陷发现', '回归测试'],
    type: 'team_member',
    scope: null,
    description: '测试工程师，负责质量保障',
    skills: [],
    disabled_tools: [],
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
  skills: [],
  disabled_tools: [],
};

const MOCK_AVATARS: string[] = [
  'circle-blue.svg',
  'square-green.svg',
  'hexagon-amber.svg',
  'triangle-red.svg',
  'star-purple.svg',
];

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

let mockSkillCounter = 0;

/**
 * 为角色添加 Skill
 */
export async function addSkillToRole(name: string, skillId: string): Promise<RoleSkillApiItem> {
  const requestData: AddSkillRequest = { skill_id: skillId };
  const mockSkill: RoleSkillApiItem = {
    id: `mock-skill-${++mockSkillCounter}`,
    name: skillId,
    description: `Mock skill: ${skillId}`,
  };
  return mockableRequest(
    () => apiClient.post<RoleSkillApiItem>(`/roles/${name}/skills`, requestData),
    mockSkill
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

/**
 * 获取工具目录
 */
export async function getToolCatalog(): Promise<ToolCatalogResponse> {
  return mockableRequest(() => apiClient.get<ToolCatalogResponse>('/roles/tools/catalog'), {
    groups: [],
  });
}
