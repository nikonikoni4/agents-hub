/**
 * Skills 模块类型定义
 */

import type { SkillApiItem } from '@/shared/types';

/**
 * 技能类型
 */
export type SkillType = 'local' | 'remote';

/**
 * 技能图标颜色
 */
export type SkillColor =
  | 'blue'
  | 'green'
  | 'purple'
  | 'orange'
  | 'pink'
  | 'teal'
  | 'amber'
  | 'rose'
  | 'indigo';

/**
 * 技能展示项（扩展 API 类型）
 */
export interface SkillDisplayItem extends SkillApiItem {
  /** 技能类型 */
  type: SkillType;
  /** 图标颜色 */
  color: SkillColor;
}

/**
 * 筛选类型
 */
export type FilterType = 'all' | 'local' | 'remote';
