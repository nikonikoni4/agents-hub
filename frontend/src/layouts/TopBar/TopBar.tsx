import { Button } from '@/shared/components';
import styles from './TopBar.module.css';

export interface TopBarProps {
  onToggleSidebar?: () => void;
}

// SVG 图标组件 - 左侧抽屉图标
function LeftPanelIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      stroke="currentColor"
      fill="none"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      stroke="currentColor"
      fill="none"
      strokeWidth="2"
    >
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      stroke="currentColor"
      fill="none"
      strokeWidth="2"
    >
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width="18"
      height="18"
      stroke="currentColor"
      fill="none"
      strokeWidth="2"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  );
}

export function TopBar({ onToggleSidebar }: TopBarProps) {
  return (
    <div className={styles.topBar}>
      <div className={styles.topBarLeft}>
        <Button variant="topBar" onClick={onToggleSidebar} title="切换左侧栏">
          <LeftPanelIcon />
        </Button>
        <Button variant="topBar" title="后退">
          <ChevronLeftIcon />
        </Button>
        <Button variant="topBar" title="前进">
          <ChevronRightIcon />
        </Button>
        <Button variant="topBar" title="搜索">
          <SearchIcon />
        </Button>
      </div>
    </div>
  );
}
