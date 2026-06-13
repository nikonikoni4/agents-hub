/**
 * 技能卡片组件
 */

import { XIcon, Tooltip } from '@/shared/components';
import type { SkillDisplayItem } from '../../types';
import styles from './SkillCard.module.css';

export interface SkillCardProps {
  skill: SkillDisplayItem;
  onClick: () => void;
  onDelete: (name: string) => void;
}

export function SkillCard({ skill, onClick, onDelete }: SkillCardProps) {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(skill.name);
  };

  const IconComponent = skill.icon;

  return (
    <div className={styles.skillCard} onClick={onClick}>
      <button
        className={styles.deleteBtn}
        onClick={handleDelete}
        aria-label={`删除 ${skill.name}`}
        type="button"
      >
        <XIcon />
      </button>

      <div className={styles.skillHeader}>
        <IconComponent className={styles.skillIcon} />
        <div className={`${styles.skillAvatar} ${styles[skill.color]}`}>{skill.name}</div>
      </div>

      <Tooltip content={skill.description} placement="bottom">
        <div className={styles.skillDesc}>
          {skill.description}
        </div>
      </Tooltip>

      <span className={`${styles.skillTag} ${styles[skill.type]}`}>
        <span className={styles.skillTagDot} />
        {skill.type === 'local' ? '本地' : '网络'}
      </span>
    </div>
  );
}
