import {
  Button,
  LeftPanelIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SearchIcon,
} from '@/shared/components';
import styles from './TopBar.module.css';

export interface TopBarProps {
  onToggleSidebar?: () => void;
}

export function TopBar({ onToggleSidebar }: TopBarProps) {
  return (
    <div className={styles.topBar}>
      <div className={styles.topBarLeft}>
        <Button variant="topBar" onClick={onToggleSidebar} aria-label="切换左侧栏">
          <LeftPanelIcon />
        </Button>
        <Button variant="topBar" aria-label="后退">
          <ChevronLeftIcon />
        </Button>
        <Button variant="topBar" aria-label="前进">
          <ChevronRightIcon />
        </Button>
        <Button variant="topBar" aria-label="搜索">
          <SearchIcon />
        </Button>
      </div>
    </div>
  );
}
