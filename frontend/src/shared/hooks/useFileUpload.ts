import { useState, useCallback } from 'react';
import { uploadFile } from '@/core/api/groupChatApi';
import type { UploadedFileInfo } from '@/shared/types';

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

export interface UseFileUploadOptions {
  chatId: string;
  onUploadComplete?: (fileInfo: UploadedFileInfo) => void;
  onUploadError?: (error: string) => void;
}

export interface UseFileUploadReturn {
  uploadedFiles: UploadedFileInfo[];
  isUploading: boolean;
  uploadFiles: (files: FileList | File[]) => Promise<void>;
  removeFile: (index: number) => void;
  clearFiles: () => void;
  validateFile: (file: File) => string | null;
}

export function useFileUpload({
  chatId,
  onUploadComplete,
  onUploadError,
}: UseFileUploadOptions): UseFileUploadReturn {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileInfo[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const validateFile = useCallback((file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `不支持的文件类型: ${file.type}`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `文件大小超过限制: ${(file.size / 1024 / 1024).toFixed(1)}MB > 50MB`;
    }
    return null;
  }, []);

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      setIsUploading(true);
      const fileArray = Array.from(files);

      for (const file of fileArray) {
        const error = validateFile(file);
        if (error) {
          onUploadError?.(error);
          continue;
        }

        try {
          const fileInfo = await uploadFile(chatId, file);
          setUploadedFiles((prev) => [...prev, fileInfo]);
          onUploadComplete?.(fileInfo);
        } catch (err) {
          onUploadError?.(err instanceof Error ? err.message : '上传失败');
        }
      }

      setIsUploading(false);
    },
    [chatId, validateFile, onUploadComplete, onUploadError]
  );

  const removeFile = useCallback((index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearFiles = useCallback(() => {
    setUploadedFiles([]);
  }, []);

  return {
    uploadedFiles,
    isUploading,
    uploadFiles,
    removeFile,
    clearFiles,
    validateFile,
  };
}
