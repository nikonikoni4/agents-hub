import { describe, it, expect } from 'vitest';
import {
  adaptSkill,
  adaptSkillList,
  adaptRoleSkill,
  adaptRoleSkillList,
  aggregateSkillWithUsers,
} from './skillAdapter';
import type { SkillApiItem, RoleSkillApiItem } from '@/shared/types/api-schemas';

const mockSkill: SkillApiItem = {
  name: 'code-review',
  description: '代码审查工具',
};

const mockRoleSkill: RoleSkillApiItem = {
  id: 'skill-001',
  name: 'code-review',
  description: '代码审查工具',
};

describe('skillAdapter', () => {
  describe('adaptSkill', () => {
    it('转换单个 skill', () => {
      const result = adaptSkill(mockSkill);
      expect(result.name).toBe('code-review');
      expect(result.description).toBe('代码审查工具');
    });
  });

  describe('adaptSkillList', () => {
    it('转换 skill 列表', () => {
      const result = adaptSkillList([mockSkill, { ...mockSkill, name: 'tdd' }]);
      expect(result).toHaveLength(2);
    });

    it('空列表返回空数组', () => {
      expect(adaptSkillList([])).toEqual([]);
    });
  });

  describe('adaptRoleSkill', () => {
    it('转换角色关联的 skill', () => {
      const result = adaptRoleSkill(mockRoleSkill);
      expect(result.id).toBe('skill-001');
      expect(result.name).toBe('code-review');
    });
  });

  describe('adaptRoleSkillList', () => {
    it('转换角色 skill 列表', () => {
      const result = adaptRoleSkillList([mockRoleSkill]);
      expect(result).toHaveLength(1);
    });
  });

  describe('aggregateSkillWithUsers', () => {
    it('未实现时抛出错误', async () => {
      await expect(aggregateSkillWithUsers('code-review')).rejects.toThrow('not implemented');
    });
  });
});
