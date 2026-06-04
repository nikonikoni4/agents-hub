/**
 * 技能相关 API 接口
 */

import apiClient, { mockableRequest } from './client';
import type { SkillApiItem } from '@/shared/types';
import type { CreateSkillRequest } from '@/shared/types/api-requests';

// ==================== Mock 数据 ====================

const MOCK_SKILLS: SkillApiItem[] = [
  { name: 'code-review', description: '自动化代码质量检查和最佳实践建议' },
  { name: 'doc-generation', description: '根据代码自动生成技术文档和API说明' },
  { name: 'test-writing', description: '智能生成单元测试和集成测试用例' },
  { name: 'architecture', description: '系统架构分析和设计方案推荐' },
];

const MOCK_SKILL: SkillApiItem = {
  name: 'new-skill',
  description: 'A newly created skill',
};

// ==================== API 接口 ====================

/**
 * 获取所有技能
 */
export async function listSkills(): Promise<SkillApiItem[]> {
  return mockableRequest(() => apiClient.get<SkillApiItem[]>('/skills'), MOCK_SKILLS);
}

/**
 * 获取单个技能信息
 */
export async function getSkill(name: string): Promise<SkillApiItem> {
  const mockSkill = MOCK_SKILLS.find((s) => s.name === name) ?? MOCK_SKILLS[0]!;
  return mockableRequest(() => apiClient.get<SkillApiItem>(`/skills/${name}`), mockSkill);
}

/**
 * 添加技能
 */
export async function addSkill(data: CreateSkillRequest): Promise<SkillApiItem> {
  return mockableRequest(() => apiClient.post<SkillApiItem>('/skills', data), MOCK_SKILL);
}

/**
 * 删除技能
 */
export async function deleteSkill(name: string): Promise<{ message: string }> {
  return mockableRequest(() => apiClient.delete<{ message: string }>(`/skills/${name}`), {
    message: `Skill '${name}' 删除成功`,
  });
}
