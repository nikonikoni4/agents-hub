import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./client', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  mockableRequest: vi.fn((_real, mock) => Promise.resolve(mock)),
}));

import apiClient from './client';
import {
  createRole,
  getRoleInfo,
  listRoles,
  updateRole,
  deleteRole,
  getRoleSkills,
  addSkillToRole,
  removeSkillFromRole,
  listAvatars,
} from './roleApi';

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('roleApi', () => {
  it('listRoles 返回角色列表', async () => {
    const result = await listRoles();
    expect(result).toHaveLength(4);
    expect(result[0]!.name).toBe('Leader');
  });

  it('getRoleInfo 返回指定角色', async () => {
    const result = await getRoleInfo('Leader');
    expect(result.name).toBe('Leader');
  });

  it('createRole 返回新角色', async () => {
    const result = await createRole({ name: 'Test', platform: 'claude' });
    expect(result.name).toBe('New Role');
  });

  it('updateRole 返回更新后的角色', async () => {
    const result = await updateRole('Leader', { description: 'updated' });
    expect(result).toBeDefined();
    expect(result.name).toBeDefined();
  });

  it('deleteRole 返回删除确认', async () => {
    const result = await deleteRole('Leader');
    expect(result.message).toBe('Successfully deleted');
  });

  it('getRoleSkills 返回角色关联的 skills', async () => {
    const result = await getRoleSkills('Leader');
    expect(result).toHaveLength(1);
    expect(result[0]!.name).toBe('architecture');
  });

  it('getRoleSkills 对未知角色返回空数组', async () => {
    const result = await getRoleSkills('Unknown');
    expect(result).toEqual([]);
  });

  it('addSkillToRole 返回添加的 skill', async () => {
    const result = await addSkillToRole('Leader', 'skill-123');
    expect(result.name).toBe('skill-123');
  });

  it('removeSkillFromRole 返回删除确认', async () => {
    const result = await removeSkillFromRole('Leader', 'skill-123');
    expect(result.message).toBe('Successfully deleted');
  });

  it('listAvatars 返回头像列表', async () => {
    const result = await listAvatars();
    expect(result).toHaveLength(5);
    expect(result[0]).toBe('circle-blue.svg');
  });

  describe('真实 API 调用路径（通过 client）', () => {
    it('listRoles 调用 GET /roles', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.get.mockResolvedValue([]);

      await listRoles();
      expect(mockedClient.get).toHaveBeenCalledWith('/roles');
    });

    it('createRole 调用 POST /roles', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.post.mockResolvedValue({});

      await createRole({ name: 'Test', platform: 'claude' });
      expect(mockedClient.post).toHaveBeenCalledWith('/roles', {
        name: 'Test',
        platform: 'claude',
      });
    });

    it('deleteRole 调用 DELETE /roles/:name', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.delete.mockResolvedValue({});

      await deleteRole('Leader');
      expect(mockedClient.delete).toHaveBeenCalledWith('/roles/Leader');
    });

    it('addSkillToRole 发送正确的请求体', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.post.mockResolvedValue({});

      await addSkillToRole('Leader', 'skill-123');
      expect(mockedClient.post).toHaveBeenCalledWith('/roles/Leader/skills', {
        skill_id: 'skill-123',
      });
    });
  });
});
