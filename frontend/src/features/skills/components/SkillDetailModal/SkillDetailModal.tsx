/**
 * 技能详情弹窗
 */

import type { SkillDisplayItem } from '../../types';
import styles from './SkillDetailModal.module.css';

export interface SkillDetailModalProps {
  skill: SkillDisplayItem;
  onClose: () => void;
}

export function SkillDetailModal({ skill, onClose }: SkillDetailModalProps) {
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className={styles.overlay} onClick={handleOverlayClick}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <h2>{skill.name}</h2>
          <button className={styles.closeBtn} onClick={onClose} aria-label="关闭">
            <svg viewBox="0 0 24 24">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.section}>
            <h3>描述</h3>
            <p>{skill.description}</p>
          </div>

          <div className={styles.section}>
            <h3>类型</h3>
            <span className={`${styles.tag} ${styles[skill.type]}`}>
              <span className={styles.tagDot} />
              {skill.type === 'local' ? '本地技能' : '网络技能'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
