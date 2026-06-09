import React, { useRef, useCallback } from 'react';
import type { UploadedFileInfo } from '@/shared/types';
import styles from './UploadArea.module.css';

export interface UploadAreaProps {
  chatId: string;
  onUploadComplete: (fileInfo: UploadedFileInfo) => void;
  onUploadError: (error: string) => void;
  disabled?: boolean;
}

const ALLOWED_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/svg+xml',
  'application/pdf',
  'text/plain',
  'text/markdown',
  'application/json',
  'text/csv',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-powerpoint',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'text/javascript',
  'text/typescript',
  'text/x-python',
  'text/x-java',
  'text/x-c++src',
  'text/x-csrc',
  'text/x-chdr',
  'text/css',
  'text/html',
  'text/xml',
  'application/x-yaml',
  'text/yaml',
  'application/toml',
  'application/zip',
  'application/x-rar-compressed',
  'application/x-7z-compressed',
  'application/x-tar',
  'application/gzip',
];

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export const UploadArea = React.memo(
  ({ chatId, onUploadComplete, onUploadError, disabled }: UploadAreaProps) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [isDragOver, setIsDragOver] = React.useState(false);

    const validateFile = useCallback((file: File): string | null => {
      if (!ALLOWED_TYPES.includes(file.type)) {
        return `不支持的文件类型: ${file.type}`;
      }
      if (file.size > MAX_FILE_SIZE) {
        return `文件大小超过限制: ${(file.size / 1024 / 1024).toFixed(1)}MB > 50MB`;
      }
      return null;
    }, []);

    const handleUpload = useCallback(
      async (file: File) => {
        const error = validateFile(file);
        if (error) {
          onUploadError(error);
          return;
        }

        try {
          const { uploadFile } = await import('@/core/api/groupChatApi');
          const fileInfo = await uploadFile(chatId, file);
          onUploadComplete(fileInfo);
        } catch (err) {
          onUploadError(err instanceof Error ? err.message : '上传失败');
        }
      },
      [chatId, onUploadComplete, onUploadError, validateFile]
    );

    const handleFileSelect = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files) return;

        Array.from(files).forEach(handleUpload);
        e.target.value = '';
      },
      [handleUpload]
    );

    const handleDragOver = useCallback((e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
    }, []);

    const handleDrop = useCallback(
      (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragOver(false);

        const files = e.dataTransfer.files;
        if (!files) return;

        Array.from(files).forEach(handleUpload);
      },
      [handleUpload]
    );

    const handleClick = useCallback(() => {
      if (!disabled) {
        fileInputRef.current?.click();
      }
    }, [disabled]);

    return (
      <div
        className={`${styles.uploadArea} ${isDragOver ? styles.dragOver : ''} ${disabled ? styles.disabled : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
          }
        }}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-label="上传文件"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ALLOWED_TYPES.join(',')}
          onChange={handleFileSelect}
          className={styles.fileInput}
        />
        <div className={styles.content}>
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>拖拽文件到此处或点击上传</span>
        </div>
      </div>
    );
  }
);

UploadArea.displayName = 'UploadArea';
