/**
 * 技能广场主容器
 */

import { useState, useMemo } from 'react';
import { SearchIcon } from '@/shared/components';
import { useSkillList } from '../../hooks/useSkillList';
import { useSkillDelete } from '../../hooks/useSkillDelete';
import { SkillCard } from './SkillCard';
import { SkillDetailModal } from '../SkillDetailModal';
import type { SkillDisplayItem, FilterType } from '../../types';
import styles from './SkillSquare.module.css';

export function SkillSquare() {
  const { skills, loading, refreshSkills } = useSkillList();
  const { handleDelete } = useSkillDelete();
  const [searchQuery, setSearchQuery] = useState('');
  const [currentFilter, setCurrentFilter] = useState<FilterType>('all');
  const [selectedSkill, setSelectedSkill] = useState<SkillDisplayItem | null>(null);

  // 过滤技能
  const filteredSkills = useMemo(() => {
    return skills.filter((skill) => {
      const matchFilter = currentFilter === 'all' || skill.type === currentFilter;
      const matchSearch =
        skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchQuery.toLowerCase());
      return matchFilter && matchSearch;
    });
  }, [skills, currentFilter, searchQuery]);

  const handleSkillClick = (skill: SkillDisplayItem) => {
    setSelectedSkill(skill);
  };

  const handleSkillDelete = (name: string) => {
    handleDelete(name, refreshSkills);
  };

  const handleCloseModal = () => {
    setSelectedSkill(null);
  };

  return (
    <div className={styles.container}>
      {/* 头部 */}
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.headerTop}>
            <h1>技能广场</h1>
            <p>发现和管理你的技能</p>
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
        </div>
      </div>

      {/* 筛选按钮 */}
      <div className={styles.filters}>
        <button
          className={`${styles.filterBtn} ${currentFilter === 'all' ? styles.active : ''}`}
          onClick={() => setCurrentFilter('all')}
        >
          <svg className={styles.filterIcon} viewBox="0 0 24 24">
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
          全部
        </button>
        <button
          className={`${styles.filterBtn} ${currentFilter === 'local' ? styles.active : ''}`}
          onClick={() => setCurrentFilter('local')}
        >
          <svg className={styles.filterIcon} viewBox="0 0 24 24">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
            <line x1="6" y1="6" x2="6.01" y2="6" />
            <line x1="6" y1="18" x2="6.01" y2="18" />
          </svg>
          本地
        </button>
        <button
          className={`${styles.filterBtn} ${currentFilter === 'remote' ? styles.active : ''}`}
          onClick={() => setCurrentFilter('remote')}
        >
          <svg className={styles.filterIcon} viewBox="0 0 24 24">
            <path d="M5 12.55a11 11 0 0 1 14.08 0" />
            <path d="M1.42 9a16 16 0 0 1 21.16 0" />
            <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
            <line x1="12" y1="20" x2="12.01" y2="20" />
          </svg>
          网络
        </button>
      </div>

      {/* 技能卡片网格 */}
      {loading ? (
        <div className={styles.loading}>加载中...</div>
      ) : filteredSkills.length === 0 ? (
        <div className={styles.emptyState}>
          <svg viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
          <p>未找到匹配的技能</p>
        </div>
      ) : (
        <div className={styles.skillsGrid}>
          {filteredSkills.map((skill) => (
            <SkillCard
              key={skill.name}
              skill={skill}
              onClick={() => handleSkillClick(skill)}
              onDelete={handleSkillDelete}
            />
          ))}
        </div>
      )}

      {/* 详情弹窗 */}
      {selectedSkill && <SkillDetailModal skill={selectedSkill} onClose={handleCloseModal} />}
    </div>
  );
}
