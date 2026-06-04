/**
 * 技能列表 Hook
 */

import { useState, useEffect, useCallback } from 'react';
import { listSkills } from '@/core/api/skillApi';
import type { SkillDisplayItem, SkillColor } from '../types';
import type { SkillApiItem } from '@/shared/types';

// 预定义颜色列表
const COLORS: SkillColor[] = [
  'blue',
  'indigo',
  'green',
  'purple',
  'teal',
  'amber',
  'pink',
  'rose',
  'orange',
];

/**
 * 将 API 数据转换为展示数据
 */
function adaptSkillForDisplay(skill: SkillApiItem, index: number): SkillDisplayItem {
  return {
    ...skill,
    type: 'local',
    color: COLORS[index % COLORS.length]!,
  };
}

/**
 * 获取技能列表
 */
export function useSkillList() {
  const [skills, setSkills] = useState<SkillDisplayItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSkills();
      setSkills(data.map(adaptSkillForDisplay));
    } catch (err) {
      console.error('加载技能列表失败:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  return { skills, loading, refreshSkills: fetchSkills };
}
