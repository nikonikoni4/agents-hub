/**
 * Skill 相关 API 接口
 *
 * 提供全局 skill 库的查询、删除和添加操作
 */

import apiClient, { mockableRequest } from './client';
import type { Skill, CreateSkillRequest } from '@/shared/types';

// ==================== Mock 数据 ====================

const MOCK_SKILLS: Skill[] = [
  {
    name: 'code-review',
    description: '代码审查工具，帮助检查代码质量和潜在问题',
  },
  {
    name: 'test-generator',
    description: '自动生成单元测试代码',
  },
  {
    name: 'refactor-assistant',
    description: '重构建议和代码优化助手',
  },
  {
    name: 'documentation-writer',
    description: '自动生成代码文档和注释',
  },
];

const MOCK_SKILL: Skill = {
  name: 'code-review',
  description: '代码审查工具，帮助检查代码质量和潜在问题',
};

// ==================== API 接口 ====================

/**
 * 列出所有 skills
 *
 * GET /api/v1/skills
 *
 * @returns 所有 skill 列表
 *
 * @example
 * const skills = await listSkills();
 * console.log(skills); // [{ name: 'code-review', description: '...' }]
 */
export async function listSkills(): Promise<Skill[]> {
  return mockableRequest(
    () => apiClient.get<Skill[]>('/skills'),
    MOCK_SKILLS
  );
}

/**
 * 获取单个 skill 详情
 *
 * GET /api/v1/skills/{skillName}
 *
 * @param skillName - skill 名称
 * @returns skill 详情
 *
 * @throws {ApiError} 404 - skill 不存在
 *
 * @example
 * const skill = await getSkill('code-review');
 * console.log(skill); // { name: 'code-review', description: '...' }
 */
export async function getSkill(skillName: string): Promise<Skill> {
  return mockableRequest(
    () => apiClient.get<Skill>(`/skills/${skillName}`),
    MOCK_SKILL
  );
}

/**
 * 删除 skill
 *
 * DELETE /api/v1/skills/{skillName}
 *
 * @param skillName - skill 名称
 * @returns 删除成功的消息
 *
 * @throws {ApiError} 404 - skill 不存在
 *
 * @example
 * const result = await deleteSkill('code-review');
 * console.log(result); // { message: "Skill 'code-review' 删除成功" }
 */
export async function deleteSkill(skillName: string): Promise<{ message: string }> {
  return mockableRequest(
    () => apiClient.delete<{ message: string }>(`/skills/${skillName}`),
    { message: `Skill '${skillName}' 删除成功` }
  );
}

/**
 * 从网络添加 skill（预留接口）
 *
 * POST /api/v1/skills
 *
 * @param data - 包含 skill URL 的请求数据
 * @returns 新添加的 skill 信息
 *
 * @throws {ApiError} 500 - 网络获取功能暂未实现
 *
 * @example
 * const skill = await addSkill({ url: 'https://example.com/skill.zip' });
 * console.log(skill); // { name: 'new-skill', description: '...' }
 */
export async function addSkill(data: CreateSkillRequest): Promise<Skill> {
  return mockableRequest(
    () => apiClient.post<Skill>('/skills', data),
    {
      name: 'new-skill',
      description: '新添加的 skill（Mock 数据）',
    }
  );
}
