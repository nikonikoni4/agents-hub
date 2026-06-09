import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { PlusIcon, CheckCircleIcon, SendIcon, UploadPreview, ImagePreviewModal } from '@/shared/components';
import type { MessageApiItem, UploadedFileInfo } from '@/shared/types';
import styles from './ChatArea.module.css';

export interface ChatInputProps {
  activeSessionId: string | null;
  members: { name: string }[];
  onSend: (text: string, files?: UploadedFileInfo[]) => void;
  quotedMessage?: MessageApiItem | null;
  onClearQuote?: () => void;
}

export const ChatInput = React.memo(
  ({ activeSessionId, members, onSend, quotedMessage, onClearQuote }: ChatInputProps) => {
    const [inputValue, setInputValue] = useState('');
    const [showMention, setShowMention] = useState(false);
    const [mentionQuery, setMentionQuery] = useState('');
    const [mentionIndex, setMentionIndex] = useState(0);
    const [uploadedFiles, setUploadedFiles] = useState<UploadedFileInfo[]>([]);
    const [showImagePreview, setShowImagePreview] = useState(false);
    const [previewImageUrl, setPreviewImageUrl] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // 过滤匹配的成员（使用 useMemo 优化）
    const filteredMembers = useMemo(
      () =>
        mentionQuery
          ? members.filter((m) => m.name.toLowerCase().includes(mentionQuery.toLowerCase()))
          : members,
      [members, mentionQuery]
    );

    // 自动调整 textarea 高度
    const adjustTextareaHeight = useCallback(() => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }, []);

    // 选择成员后插入 @name
    const handleMentionSelect = useCallback(
      (name: string) => {
        const textarea = textareaRef.current;
        if (!textarea) return;
        const cursorPos = textarea.selectionStart;
        const before = inputValue.slice(0, cursorPos);
        const after = inputValue.slice(cursorPos);
        // 找到 @ 的位置
        const atIndex = before.lastIndexOf('@');
        const newValue = before.slice(0, atIndex) + `@${name} ` + after;
        setInputValue(newValue);
        setShowMention(false);
        // 重新聚焦并设置光标
        requestAnimationFrame(() => {
          textarea.focus();
          const newPos = atIndex + name.length + 2;
          textarea.setSelectionRange(newPos, newPos);
        });
      },
      [inputValue]
    );

    const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      setInputValue(value);

      // 检测 @ 触发
      const cursorPos = e.target.selectionStart;
      const textBeforeCursor = value.slice(0, cursorPos);
      const atIndex = textBeforeCursor.lastIndexOf('@');

      if (atIndex !== -1) {
        const charBeforeAt = atIndex > 0 ? textBeforeCursor[atIndex - 1] : ' ';
        // @ 前面必须是空格或行首
        if (charBeforeAt === ' ' || charBeforeAt === '\n' || atIndex === 0) {
          const query = textBeforeCursor.slice(atIndex + 1);
          // 查询中不能有空格（否则说明已经离开了 @ 上下文）
          if (!query.includes(' ') && !query.includes('\n')) {
            setMentionQuery(query);
            setMentionIndex(0);
            setShowMention(true);
            return;
          }
        }
      }
      setShowMention(false);
    }, []);

    const handleSendClick = useCallback(() => {
      const text = inputValue.trim();
      if (!text || !activeSessionId) return;

      onSend(text, uploadedFiles);
      setInputValue('');
      setUploadedFiles([]);
      setShowMention(false);
    }, [inputValue, activeSessionId, onSend, uploadedFiles]);

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent) => {
        // @成员选择导航
        if (showMention && filteredMembers.length > 0) {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            setMentionIndex((prev) => (prev + 1) % filteredMembers.length);
            return;
          }
          if (e.key === 'ArrowUp') {
            e.preventDefault();
            setMentionIndex((prev) => (prev - 1 + filteredMembers.length) % filteredMembers.length);
            return;
          }
          if (e.key === 'Enter' || e.key === 'Tab') {
            e.preventDefault();
            const selected = filteredMembers[mentionIndex];
            if (selected) handleMentionSelect(selected.name);
            return;
          }
          if (e.key === 'Escape') {
            e.preventDefault();
            setShowMention(false);
            return;
          }
        }

        // Enter 发送，Shift+Enter 换行
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSendClick();
        }
      },
      [handleSendClick, showMention, filteredMembers, mentionIndex, handleMentionSelect]
    );

    // 点击外部关闭 mention 下拉框
    useEffect(() => {
      if (!showMention) return;
      const handleClickOutside = () => setShowMention(false);
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }, [showMention]);

    const handleRemoveFile = useCallback((index: number) => {
      setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
    }, []);

    const handleImageClick = useCallback(
      (filePath: string) => {
        setPreviewImageUrl(
          `/api/v1/group-chats/${activeSessionId}/files/${encodeURIComponent(filePath)}`
        );
        setShowImagePreview(true);
      },
      [activeSessionId]
    );

    return (
      <div className={styles.chatInputContainer}>
        {/* 引用消息框 */}
        {quotedMessage && (
          <div className={styles.quoteBox}>
            <div className={styles.quoteContent}>
              <div className={styles.quoteHeader}>
                <span className={styles.quoteSpeaker}>{quotedMessage.speaker}</span>
                <button
                  className={styles.quoteCloseBtn}
                  onClick={onClearQuote}
                  aria-label="取消引用"
                >
                  ✕
                </button>
              </div>
              <div className={styles.quoteText}>
                {quotedMessage.content.length > 100
                  ? `${quotedMessage.content.slice(0, 100)}...`
                  : quotedMessage.content}
              </div>
            </div>
          </div>
        )}
        <div className={styles.chatInputWrapper} style={{ position: 'relative' }}>
          {/* @成员选择下拉框 */}
          {showMention && filteredMembers.length > 0 && (
            <div className={styles.mentionDropdown} onClick={(e) => e.stopPropagation()}>
              {filteredMembers.map((member, i) => (
                <div
                  key={member.name}
                  className={styles.mentionItem}
                  style={i === mentionIndex ? { background: 'var(--bg-hover)' } : undefined}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleMentionSelect(member.name);
                  }}
                  onMouseEnter={() => setMentionIndex(i)}
                >
                  <span>{member.name}</span>
                </div>
              ))}
            </div>
          )}
          <button className={styles.iconBtn} aria-label="添加附件">
            <PlusIcon />
          </button>
          <textarea
            ref={textareaRef}
            rows={2}
            className={styles.chatInput}
            placeholder="输入消息... (输入 @ 提及成员)"
            aria-label="输入消息"
            value={inputValue}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            onInput={adjustTextareaHeight}
          />
          <button className={styles.iconBtn} aria-label="确认">
            <CheckCircleIcon />
          </button>
          <button className={styles.iconBtn} onClick={handleSendClick} aria-label="发送消息">
            <SendIcon />
          </button>
        </div>

        {/* 文件上传预览区域 */}
        {uploadedFiles.length > 0 && (
          <UploadPreview
            files={uploadedFiles}
            onRemove={handleRemoveFile}
            onImageClick={handleImageClick}
            groupChatId={activeSessionId || ''}
          />
        )}

        {/* 图片预览模态框 */}
        <ImagePreviewModal
          isOpen={showImagePreview}
          imageUrl={previewImageUrl}
          onClose={() => setShowImagePreview(false)}
        />
      </div>
    );
  }
);
