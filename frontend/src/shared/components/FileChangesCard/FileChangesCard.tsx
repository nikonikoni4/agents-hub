import { useState } from 'react';
import { ModifiedFileInfo } from '@/shared/types/api-schemas';
import { FileItem } from './FileItem';
import styles from './FileChangesCard.module.css';

export interface FileChangesCardProps {
  modifiedFiles: ModifiedFileInfo[];
  onPreview: (snapshotId: string, filePath: string) => void;
  onDiff: (snapshotId: string, filePath: string) => void;
}

export function FileChangesCard({ modifiedFiles, onPreview, onDiff }: FileChangesCardProps) {
  const [collapsed, setCollapsed] = useState(true);

  // 计算总的 additions 和 deletions
  const totalAdditions = modifiedFiles.reduce((sum, file) => sum + file.additions, 0);
  const totalDeletions = modifiedFiles.reduce((sum, file) => sum + file.deletions, 0);

  return (
    <div className={styles.card}>
      {/* 折叠头部 */}
      <div className={styles.header} onClick={() => setCollapsed(!collapsed)}>
        <div className={styles.summary}>
          <span className={styles.icon}>📝</span>
          <span>已编辑 {modifiedFiles.length} 个文件</span>
          <span className={styles.stats}>
            <span className={styles.additions}>+{totalAdditions}</span>
            <span className={styles.deletions}>-{totalDeletions}</span>
          </span>
        </div>
        <button className={styles.toggleBtn} type="button">
          {collapsed ? '展开 ▼' : '收起 ▲'}
        </button>
      </div>

      {/* 文件列表（展开时显示） */}
      {!collapsed && (
        <div className={styles.fileList}>
          {modifiedFiles.map((file) => (
            <FileItem
              key={file.snapshot_id}
              file={file}
              onPreview={() => onPreview(file.snapshot_id, file.path)}
              onDiff={() => onDiff(file.snapshot_id, file.path)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
