import { ModifiedFileInfo } from '@/shared/types/api-schemas';
import styles from './FileChangesCard.module.css';

function FilePlusIcon() {
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
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" />
      <path d="M9 15h6" />
      <path d="M12 18v-6" />
    </svg>
  );
}

function FileMinusIcon() {
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
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" />
      <path d="M9 15h6" />
    </svg>
  );
}

function FileIcon() {
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
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" />
    </svg>
  );
}

export interface FileItemProps {
  file: ModifiedFileInfo;
  onPreview: () => void;
  onDiff: () => void;
}

export function FileItem({ file, onPreview, onDiff }: FileItemProps) {
  const getIcon = () => {
    if (file.status === 'added') return <FilePlusIcon />;
    if (file.status === 'deleted') return <FileMinusIcon />;
    return <FileIcon />;
  };

  return (
    <div className={styles.fileItem}>
      <div className={styles.fileInfo}>
        <span className={styles.fileIcon}>{getIcon()}</span>
        <span className={styles.filePath}>{file.path}</span>
        <span className={styles.stats}>
          <span className={styles.additions}>+{file.additions}</span>
          <span className={styles.deletions}>-{file.deletions}</span>
        </span>
      </div>
      <div className={styles.actions}>
        <button className={styles.actionBtn} onClick={onPreview} type="button">
          预览
        </button>
        {file.diff_available && (
          <button className={styles.actionBtn} onClick={onDiff} type="button">
            Diff
          </button>
        )}
      </div>
    </div>
  );
}
