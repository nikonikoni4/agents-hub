import React from 'react';
import type { UploadedFileInfo } from '@/shared/types';
import styles from './FilePreviewCard.module.css';

export interface FilePreviewCardProps {
  groupChatId: string;
  files: UploadedFileInfo[];
  onImageClick?: (filePath: string) => void;
  onDocumentClick?: (filePath: string) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function FileIcon({ fileType }: { fileType: string }) {
  if (fileType.startsWith('image/')) {
    return (
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
    );
  }

  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  );
}

export const FilePreviewCard = React.memo(
  ({ groupChatId, files, onImageClick, onDocumentClick }: FilePreviewCardProps) => {
    if (files.length === 0) return null;

    return (
      <div className={styles.container}>
        {files.map((file, index) => (
          <div key={index} className={styles.item}>
            {file.file_type.startsWith('image/') ? (
              <div
                className={styles.imagePreview}
                onClick={() => onImageClick?.(file.file_path)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onImageClick?.(file.file_path);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-label={`查看图片 ${file.file_name}`}
              >
                <img
                  src={`/api/v1/group-chats/${groupChatId}/files/${encodeURIComponent(file.file_path)}`}
                  alt={file.file_name}
                  className={styles.thumbnail}
                />
              </div>
            ) : (
              <div
                className={styles.fileInfo}
                onClick={() => onDocumentClick?.(file.file_path)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onDocumentClick?.(file.file_path);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-label={`下载文件 ${file.file_name}`}
              >
                <span className={styles.fileIcon}>
                  <FileIcon fileType={file.file_type} />
                </span>
                <span className={styles.fileName}>{file.file_name}</span>
                <span className={styles.fileSize}>{formatFileSize(file.file_size)}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }
);

FilePreviewCard.displayName = 'FilePreviewCard';
