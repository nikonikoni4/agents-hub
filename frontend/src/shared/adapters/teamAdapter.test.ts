/**
 * teamAdapter 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adaptTeam, aggregateTeam, aggregateAllTeams } from './teamAdapter';
import * as teamApi from '@/core/api/teamApi';

vi.mock('@/core/api/teamApi');

describe('teamAdapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('adaptTeam', () => {
    it('should adapt team API response to TeamData', () => {
      const mockTeam = {
        name: 'Frontend Team',
        members: ['Designer', 'Developer'],
      };

      const result = adaptTeam(mockTeam);

      expect(result).toEqual({
        name: 'Frontend Team',
        members: ['Designer', 'Developer'],
      });
    });
  });

  describe('aggregateTeam', () => {
    it('should aggregate team data', async () => {
      const mockTeam = {
        name: 'Frontend Team',
        members: ['Designer', 'Developer'],
      };

      vi.mocked(teamApi.getTeam).mockResolvedValue(mockTeam);

      const result = await aggregateTeam('Frontend Team');

      expect(result.name).toBe('Frontend Team');
      expect(result.members).toEqual(['Designer', 'Developer']);
      expect(teamApi.getTeam).toHaveBeenCalledWith('Frontend Team');
    });
  });

  describe('aggregateAllTeams', () => {
    it('should aggregate all teams', async () => {
      const mockTeams = [
        { name: 'Frontend Team', members: ['Designer'] },
        { name: 'Backend Team', members: ['Developer'] },
      ];

      vi.mocked(teamApi.listTeams).mockResolvedValue(mockTeams);

      const result = await aggregateAllTeams();

      expect(result).toHaveLength(2);
      expect(result[0]!.name).toBe('Frontend Team');
      expect(result[0]!.members).toEqual(['Designer']);
    });
  });
});
