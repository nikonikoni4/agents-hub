import styles from './WebPreviewCard.module.css';

function GlobeIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  );
}

export interface WebPreviewCardProps {
  url: string;
  title?: string;
  isActive: boolean;
  onClick: () => void;
}

function extractDomain(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function WebPreviewCard({ url, title, isActive, onClick }: WebPreviewCardProps) {
  return (
    <button
      className={`${styles.card} ${isActive ? styles.active : ''}`}
      onClick={onClick}
      type="button"
    >
      <div className={styles.iconWrapper}>
        <GlobeIcon />
      </div>
      <div className={styles.info}>
        <div className={styles.title}>{title || '网页预览'}</div>
        <div className={styles.url}>{extractDomain(url)}</div>
      </div>
      <div className={styles.arrow}>
        <ExternalLinkIcon />
      </div>
    </button>
  );
}
