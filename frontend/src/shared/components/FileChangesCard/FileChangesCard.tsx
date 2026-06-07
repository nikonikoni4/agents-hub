import { useState } from 'react';
import { ModifiedFileInfo } from '@/shared/types/api-schemas';
import { FileItem } from './FileItem';
import styles from './FileChangesCard.module.css';

function PencilIcon() {
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
      <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
      <path d="m15 5 4 4" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function ChevronUpIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m18 15-6-6-6 6" />
    </svg>
  );
}

export interface FileChangesCardProps {
  modifiedFiles: ModifiedFileInfo[];
  onPreview: (snapshotId: string, filePath: string) => void;
  onDiff: (snapshotId: string, filePath: string) => void;
}

export function FileChangesCard({ modifiedFiles, onPreview, onDiff }: FileChangesCardProps) {
  const [collapsed, setCollapsed] = useState(true);

  const totalAdditions = modifiedFiles.reduce((sum, file) => sum + file.additions, 0);
  const totalDeletions = modifiedFiles.reduce((sum, file) => sum + file.deletions, 0);

  return (
    <div className={styles.card}>
      <div className={styles.header} onClick={() => setCollapsed(!collapsed)}>
        <div className={styles.summary}>
          <span className={styles.icon}>
            <PencilIcon />
          </span>
          <span>已编辑 {modifiedFiles.length} 个文件</span>
          <span className={styles.stats}>
            <span className={styles.additions}>+{totalAdditions}</span>
            <span className={styles.deletions}>-{totalDeletions}</span>
          </span>
        </div>
        <button className={styles.toggleBtn} type="button">
          {collapsed ? (
            <>
              <span>展开</span> <ChevronDownIcon />
            </>
          ) : (
            <>
              <span>收起</span> <ChevronUpIcon />
            </>
          )}
        </button>
      </div>

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
