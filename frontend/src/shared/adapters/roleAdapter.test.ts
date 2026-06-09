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
    it('should return role with embedded skills', async () => {
      const mockRole = {
        name: 'Designer',
        platform: 'claude' as const,
        avatar: 'avatar1.png',
        abilities: ['UI设计'],
        type: 'team_member' as const,
        scope: null,
        description: '前端设计师',
        skills: [{ id: 'skill-1', name: 'design', description: '设计技能' }],
        disabled_tools: [],
      };

      vi.mocked(roleApi.getRoleInfo).mockResolvedValue(mockRole);

      const result = await aggregateRoleWithSkills('Designer');

      expect(result).toEqual(mockRole);
      expect(result.skills).toHaveLength(1);
      expect(roleApi.getRoleInfo).toHaveBeenCalledWith('Designer');
    });
  });

  describe('aggregateAllRolesWithSkills', () => {
    it('should return all roles with embedded skills', async () => {
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
          disabled_tools: [],
        },
        {
          name: 'Developer',
          platform: 'codex' as const,
          avatar: null,
          abilities: [],
          type: 'team_member' as const,
          scope: null,
          description: 'B',
          skills: [{ id: 'skill-1', name: 'code-review', description: '代码审查' }],
          disabled_tools: [],
        },
      ];

      vi.mocked(roleApi.listRoles).mockResolvedValue(mockRoles);

      const result = await aggregateAllRolesWithSkills();

      expect(result).toHaveLength(2);
      expect(result[0]!.name).toBe('Designer');
      expect(result[0]!.skills).toEqual([]);
      expect(result[1]!.skills).toHaveLength(1);
    });
  });
});
