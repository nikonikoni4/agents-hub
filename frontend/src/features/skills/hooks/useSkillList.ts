/**
 * 技能列表 Hook
 */

import { useState, useEffect } from 'react';
import type { SkillDisplayItem } from '../types';

// Mock 数据
const MOCK_SKILLS: SkillDisplayItem[] = [
  {
    name: '代码审查',
    description: '自动化代码质量检查和最佳实践建议',
    type: 'local',
    color: 'blue',
  },
  {
    name: '文档生成',
    description: '根据代码自动生成技术文档和API说明',
    type: 'local',
    color: 'indigo',
  },
  {
    name: '测试编写',
    description: '智能生成单元测试和集成测试用例',
    type: 'local',
    color: 'green',
  },
  {
    name: '架构设计',
    description: '系统架构分析和设计方案推荐',
    type: 'local',
    color: 'purple',
  },
  {
    name: '代码翻译',
    description: '多语言代码转换和迁移工具',
    type: 'local',
    color: 'teal',
  },
  {
    name: '性能优化',
    description: '代码性能分析和优化建议',
    type: 'local',
    color: 'amber',
  },
  {
    name: 'UI 设计',
    description: '界面设计建议和组件生成',
    type: 'local',
    color: 'pink',
  },
  {
    name: '安全扫描',
    description: '代码安全漏洞检测和修复方案',
    type: 'local',
    color: 'rose',
  },
  {
    name: '数据库优化',
    description: 'SQL查询优化和数据库架构建议',
    type: 'local',
    color: 'orange',
  },
];

/**
 * 获取技能列表
 */
export function useSkillList() {
  const [skills, setSkills] = useState<SkillDisplayItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 模拟 API 调用
    const fetchSkills = async () => {
      setLoading(true);
      await new Promise((resolve) => setTimeout(resolve, 300));
      setSkills(MOCK_SKILLS);
      setLoading(false);
    };

    fetchSkills();
  }, []);

  const refreshSkills = () => {
    setLoading(true);
    setTimeout(() => {
      setSkills(MOCK_SKILLS);
      setLoading(false);
    }, 300);
  };

  return { skills, loading, refreshSkills };
}
