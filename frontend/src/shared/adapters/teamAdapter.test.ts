/**
 * teamAdapter 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchTeamWithMembers, fetchAllTeamsWithMembers } from './teamAdapter';
import * as teamApi from '@/core/api/teamApi';
import * as roleAdapter from './roleAdapter';

vi.mock('@/core/api/teamApi');
vi.mock('./roleAdapter');

describe('teamAdapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchTeamWithMembers', () => {
    it('should aggregate team with member details', async () => {
      const mockTeam = {
        name: 'Frontend Team',
        members: ['Designer', 'Developer'],
      };

      const mockRoles = [
        {
          name: 'Designer',
          platform: 'claude' as const,
          avatar: null,
          abilities: [],
          type: 'team_member' as const,
          scope: null,
          description: 'A',
          skills: [],
        },
        {
          name: 'Developer',
          platform: 'codex' as const,
          avatar: null,
          abilities: [],
          type: 'team_member' as const,
          scope: null,
          description: 'B',
          skills: [],
        },
      ];

      vi.mocked(teamApi.getTeam).mockResolvedValue(mockTeam);
      vi.mocked(roleAdapter.fetchRoleWithSkills).mockImplementation((name) =>
        Promise.resolve(mockRoles.find((r) => r.name === name)!)
      );

      const result = await fetchTeamWithMembers('Frontend Team');

      expect(result.name).toBe('Frontend Team');
      expect(result.members).toHaveLength(2);
      expect(result.members[0]!.name).toBe('Designer');
      expect(roleAdapter.fetchRoleWithSkills).toHaveBeenCalledTimes(2);
    });
  });

  describe('fetchAllTeamsWithMembers', () => {
    it('should aggregate all teams with members', async () => {
      const mockTeams = [
        { name: 'Frontend Team', members: ['Designer'] },
        { name: 'Backend Team', members: ['Developer'] },
      ];

      const mockRole = {
        name: 'Designer',
        platform: 'claude' as const,
        avatar: null,
        abilities: [],
        type: 'team_member' as const,
        scope: null,
        description: '',
        skills: [],
      };

      vi.mocked(teamApi.listTeams).mockResolvedValue(mockTeams);
      vi.mocked(teamApi.getTeam).mockImplementation((name) =>
        Promise.resolve(mockTeams.find((t) => t.name === name)!)
      );
      vi.mocked(roleAdapter.fetchRoleWithSkills).mockResolvedValue(mockRole);

      const result = await fetchAllTeamsWithMembers();

      expect(result).toHaveLength(2);
      expect(result[0]!.members).toHaveLength(1);
    });
  });
});
