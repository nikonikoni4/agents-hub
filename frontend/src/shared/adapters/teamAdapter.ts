/**
 * 团队适配器 - 聚合团队和成员角色数据
 */

import { getTeam, listTeams } from '@/core/api/teamApi';
import { fetchRoleWithSkills, type RoleWithSkills } from './roleAdapter';

/**
 * 聚合后的团队数据（包含完整的成员角色对象）
 */
export interface TeamWithMembers {
  name: string;
  members: RoleWithSkills[];
}

/**
 * 获取单个团队及其成员详情
 */
export async function fetchTeamWithMembers(teamName: string): Promise<TeamWithMembers> {
  const team = await getTeam(teamName);
  const members = await Promise.all(team.members.map((name) => fetchRoleWithSkills(name)));
  return { name: team.name, members };
}

/**
 * 获取所有团队及其成员详情
 */
export async function fetchAllTeamsWithMembers(): Promise<TeamWithMembers[]> {
  const teams = await listTeams();
  return Promise.all(teams.map((team) => fetchTeamWithMembers(team.name)));
}
