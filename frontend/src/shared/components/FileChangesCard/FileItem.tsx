import { ModifiedFileInfo } from '@/shared/types/api-schemas';
import styles from './FileChangesCard.module.css';

export interface FileItemProps {
  file: ModifiedFileInfo;
  onPreview: () => void;
  onDiff: () => void;
}

export function FileItem({ file, onPreview, onDiff }: FileItemProps) {
  // 根据文件状态选择图标
  const getIcon = () => {
    if (file.status === 'added') return '➕';
    if (file.status === 'deleted') return '➖';
    return '📄';
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
