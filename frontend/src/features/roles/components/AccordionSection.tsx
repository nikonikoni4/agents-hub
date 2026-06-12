/**
 * 手风琴组件 - 可折叠的内容区域
 */

import { useState, type ReactNode } from 'react';
import styles from './CreateRoleDialog.module.css';

export interface AccordionSectionProps {
  title: string;
  badge?: string;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}

export function AccordionSection({ title, badge, isOpen, onToggle, children }: AccordionSectionProps) {
  return (
    <div className={styles.accordionSection}>
      <div className={styles.accordionHeader} onClick={onToggle}>
        <div className={styles.accordionTitle}>
          <span>{title}</span>
          {badge && <span className={styles.accordionBadge}>{badge}</span>}
        </div>
        <svg
          className={`${styles.accordionArrow} ${isOpen ? styles.open : ''}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>
      {isOpen && <div className={styles.accordionContent}>{children}</div>}
    </div>
  );
}
