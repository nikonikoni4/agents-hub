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
    members: ['Designer'],
  },
];

const MOCK_TEAM: TeamApiResponse = {
  name: 'Test Team',
  members: ['Agent1', 'Agent2', 'Agent3'],
};

const MOCK_NEW_TEAM: TeamApiResponse = {
  name: 'New Team',
  members: ['NewAgent1', 'NewAgent2'],
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
  return mockableRequest(() => apiClient.get<TeamApiResponse>(`/teams/${name}`), MOCK_TEAM);
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
  return mockableRequest(() => apiClient.patch<TeamApiResponse>(`/teams/${name}`, data), {
    name: data.name ?? MOCK_TEAM.name,
    members: data.members ?? MOCK_TEAM.members,
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
