/**
 * 团队适配器 - 聚合团队数据
 */

import { getTeam, listTeams } from '@/core/api/teamApi';
import type { TeamApiResponse } from '@/shared/types/api-schemas';

/**
 * 团队数据（包含成员名称列表）
 */
export interface TeamData {
  name: string;
  members: string[];
}

/**
 * 适配单个团队数据
 */
export function adaptTeam(apiTeam: TeamApiResponse): TeamData {
  return {
    name: apiTeam.name,
    members: apiTeam.members,
  };
}

/**
 * 聚合单个团队数据
 */
export async function aggregateTeam(teamName: string): Promise<TeamData> {
  const team = await getTeam(teamName);
  return adaptTeam(team);
}

/**
 * 聚合所有团队数据
 */
export async function aggregateAllTeams(): Promise<TeamData[]> {
  const teams = await listTeams();
  return teams.map(adaptTeam);
}
