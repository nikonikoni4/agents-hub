import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./client', () => ({
  default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
  mockableRequest: vi.fn((_real, mock) => Promise.resolve(mock)),
}));

import apiClient from './client';
import { listSkills, getSkill, deleteSkill, addSkill } from './skillApi';

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('skillApi', () => {
  it('listSkills 返回 skill 列表', async () => {
    const result = await listSkills();
    expect(result).toHaveLength(4);
    expect(result[0]!.name).toBe('code-review');
    expect(result[0]!.description).toBeDefined();
  });

  it('getSkill 返回指定 skill', async () => {
    const result = await getSkill('code-review');
    expect(result.name).toBe('code-review');
  });

  it('deleteSkill 返回删除确认', async () => {
    const result = await deleteSkill('code-review');
    expect(result.message).toContain('code-review');
    expect(result.message).toContain('删除成功');
  });

  it('addSkill 返回新 skill', async () => {
    const result = await addSkill({ url: 'https://example.com/skill.zip' });
    expect(result.name).toBe('new-skill');
  });

  describe('真实 API 调用路径', () => {
    it('listSkills 调用 GET /skills', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.get.mockResolvedValue([]);

      await listSkills();
      expect(mockedClient.get).toHaveBeenCalledWith('/skills');
    });

    it('getSkill 调用 GET /skills/:name', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.get.mockResolvedValue({});

      await getSkill('code-review');
      expect(mockedClient.get).toHaveBeenCalledWith('/skills/code-review');
    });

    it('deleteSkill 调用 DELETE /skills/:name', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.delete.mockResolvedValue({});

      await deleteSkill('code-review');
      expect(mockedClient.delete).toHaveBeenCalledWith('/skills/code-review');
    });

    it('addSkill 调用 POST /skills', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.post.mockResolvedValue({});

      await addSkill({ url: 'https://example.com/skill.zip' });
      expect(mockedClient.post).toHaveBeenCalledWith('/skills', {
        url: 'https://example.com/skill.zip',
      });
    });
  });
});
