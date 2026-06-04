import { describe, it, expect } from 'vitest';
import { adaptRole, adaptRoleList, aggregateRoleWithSkills } from './roleAdapter';
import type { RoleApiResponse } from '@/shared/types/api-schemas';

const mockRole: RoleApiResponse = {
  name: 'Leader',
  platform: 'claude',
  avatar: 'avatar1.png',
  abilities: ['任务分派'],
  type: 'leader',
  scope: null,
  description: '团队领导者',
};

describe('roleAdapter', () => {
  describe('adaptRole', () => {
    it('转换单个角色', () => {
      const result = adaptRole(mockRole);
      expect(result.name).toBe('Leader');
      expect(result.platform).toBe('claude');
    });
  });

  describe('adaptRoleList', () => {
    it('转换角色列表', () => {
      const roles = [mockRole, { ...mockRole, name: 'Developer' }];
      const result = adaptRoleList(roles);
      expect(result).toHaveLength(2);
      expect(result[0]!.name).toBe('Leader');
      expect(result[1]!.name).toBe('Developer');
    });

    it('空列表返回空数组', () => {
      expect(adaptRoleList([])).toEqual([]);
    });
  });

  describe('aggregateRoleWithSkills', () => {
    it('未实现时抛出错误', async () => {
      await expect(aggregateRoleWithSkills('Leader')).rejects.toThrow('not implemented');
    });
  });
});
