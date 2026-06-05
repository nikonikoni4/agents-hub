/**
 * 技能选择弹窗组件
 *
 * 职责：
 * - 展示所有可用技能
 * - 支持搜索过滤
 * - 支持选择技能
 */

import { useState, useMemo, useEffect } from 'react';
import { listSkills } from '@/core/api';
import { SearchIcon } from '@/shared/components';
import type { SkillApiItem } from '@/shared/types';
import styles from './SkillSelectorModal.module.css';

export interface SkillSelectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (skill: SkillApiItem) => void;
  /** 已选技能的名称列表，用于标记已选状态 */
  excludeNames?: string[];
}

export function SkillSelectorModal({
  isOpen,
  onClose,
  onSelect,
  excludeNames = [],
}: SkillSelectorModalProps) {
  const [skills, setSkills] = useState<SkillApiItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (!isOpen) return;

    const fetchSkills = async () => {
      setLoading(true);
      try {
        const data = await listSkills();
        setSkills(data);
      } catch (err) {
        console.error('Failed to fetch skills:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSkills();
  }, [isOpen]);

  const filteredSkills = useMemo(() => {
    return skills.filter(
      (skill) =>
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [skills, searchQuery]);

  const handleSelect = (skill: SkillApiItem) => {
    onSelect(skill);
  };

  const handleClose = () => {
    setSearchQuery('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>选择技能</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <div className={styles.searchBox}>
          <SearchIcon />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="搜索技能..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className={styles.content}>
          {loading ? (
            <div className={styles.loading}>加载中...</div>
          ) : filteredSkills.length === 0 ? (
            <div className={styles.emptyState}>
              <p>未找到匹配的技能</p>
            </div>
          ) : (
            <div className={styles.skillsGrid}>
              {filteredSkills.map((skill) => {
                const isSelected = excludeNames.includes(skill.name);
                return (
                  <button
                    key={skill.name}
                    type="button"
                    className={`${styles.skillCard} ${isSelected ? styles.selected : ''}`}
                    onClick={() => !isSelected && handleSelect(skill)}
                    disabled={isSelected}
                  >
                    <div className={styles.skillName}>{skill.name}</div>
                    <div className={styles.skillDesc}>{skill.description}</div>
                    {isSelected && <span className={styles.selectedBadge}>已选</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
