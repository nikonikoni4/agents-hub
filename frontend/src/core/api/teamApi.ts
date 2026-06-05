/**
 * 团队相关 API 接口
 *
 * 提供团队的 CRUD 操作
 */

import apiClient, { mockableRequest } from './client';
import type {
  TeamApiResponse,
  CreateTeamRequest,
  UpdateTeamRequest,
  SuccessResponse,
} from '@/shared/types';

// ==================== Mock 数据 ====================

const MOCK_TEAMS: TeamApiResponse[] = [
  {
    name: 'Frontend Team',
    members: ['Designer', 'Developer'],
  },
  {
    name: 'Backend Team',
    members: ['Developer', 'Tester'],
  },
  {
    name: 'Product Team',
    members: ['Designer', 'Leader'],
  },
];

const MOCK_NEW_TEAM: TeamApiResponse = {
  name: 'New Team',
  members: ['Leader', 'Developer'],
};

// ==================== API 接口 ====================

/**
 * 获取所有团队
 */
export async function listTeams(): Promise<TeamApiResponse[]> {
  return mockableRequest(() => apiClient.get<TeamApiResponse[]>('/teams'), MOCK_TEAMS);
}

/**
 * 获取单个团队信息
 */
export async function getTeam(name: string): Promise<TeamApiResponse> {
  const mockTeam = MOCK_TEAMS.find((t) => t.name === name) ?? MOCK_TEAMS[0]!;
  return mockableRequest(() => apiClient.get<TeamApiResponse>(`/teams/${name}`), mockTeam);
}

/**
 * 创建团队
 */
export async function createTeam(data: CreateTeamRequest): Promise<TeamApiResponse> {
  return mockableRequest(() => apiClient.post<TeamApiResponse>('/teams', data), MOCK_NEW_TEAM);
}

/**
 * 更新团队信息
 */
export async function updateTeam(name: string, data: UpdateTeamRequest): Promise<TeamApiResponse> {
  const existing = MOCK_TEAMS.find((t) => t.name === name) ?? MOCK_TEAMS[0]!;
  return mockableRequest(() => apiClient.patch<TeamApiResponse>(`/teams/${name}`, data), {
    name: data.name ?? existing.name,
    members: data.members ?? existing.members,
  });
}

/**
 * 删除团队
 */
export async function deleteTeam(name: string): Promise<SuccessResponse> {
  return mockableRequest(() => apiClient.delete<SuccessResponse>(`/teams/${name}`), {
    message: `Team '${name}' 删除成功`,
  });
}
