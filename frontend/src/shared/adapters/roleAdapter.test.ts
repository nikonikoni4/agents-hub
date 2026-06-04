/**
 * roleAdapter 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { aggregateRoleWithSkills, aggregateAllRolesWithSkills } from './roleAdapter';
import * as roleApi from '@/core/api/roleApi';

vi.mock('@/core/api/roleApi');

describe('roleAdapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('aggregateRoleWithSkills', () => {
    it('should aggregate role info and skills', async () => {
      const mockRole = {
        name: 'Designer',
        platform: 'claude' as const,
        avatar: 'avatar1.png',
        abilities: ['UI设计'],
        type: 'team_member' as const,
        scope: null,
        description: '前端设计师',
      };

      const mockSkills = [{ id: 'skill-1', name: 'design', description: '设计技能' }];

      vi.mocked(roleApi.getRoleInfo).mockResolvedValue(mockRole);
      vi.mocked(roleApi.getRoleSkills).mockResolvedValue(mockSkills);

      const result = await aggregateRoleWithSkills('Designer');

      expect(result).toEqual({ ...mockRole, skills: mockSkills });
      expect(roleApi.getRoleInfo).toHaveBeenCalledWith('Designer');
      expect(roleApi.getRoleSkills).toHaveBeenCalledWith('Designer');
    });
  });

  describe('aggregateAllRolesWithSkills', () => {
    it('should aggregate all roles with skills', async () => {
      const mockRoles = [
        {
          name: 'Designer',
          platform: 'claude' as const,
          avatar: null,
          abilities: [],
          type: 'team_member' as const,
          scope: null,
          description: 'A',
        },
        {
          name: 'Developer',
          platform: 'codex' as const,
          avatar: null,
          abilities: [],
          type: 'team_member' as const,
          scope: null,
          description: 'B',
        },
      ];

      vi.mocked(roleApi.listRoles).mockResolvedValue(mockRoles);
      vi.mocked(roleApi.getRoleInfo).mockImplementation((name) =>
        Promise.resolve(mockRoles.find((r) => r.name === name)!)
      );
      vi.mocked(roleApi.getRoleSkills).mockResolvedValue([]);

      const result = await aggregateAllRolesWithSkills();

      expect(result).toHaveLength(2);
      expect(result[0]!.name).toBe('Designer');
      expect(result[0]!.skills).toEqual([]);
    });
  });
});
