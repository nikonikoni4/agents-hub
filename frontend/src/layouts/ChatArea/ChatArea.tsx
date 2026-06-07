import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  MoreVerticalIcon,
  RightPanelIcon,
  AvatarImage,
  MarkdownRenderer,
} from '@/shared/components';
import { FileChangesCard } from '@/shared/components/FileChangesCard';
import { useChatMessages } from '@/features/chat/hooks/useChatMessages';
import { useMembers } from '@/features/chat/hooks/useMembers';
import { usePinnedMessages } from '@/features/chat/hooks/usePinnedMessages';
import { ManageMembersDialog } from '@/features/chat/components/ManageMembersDialog';
import {
  sendMessage,
  getMembers,
  getFileSnapshotContent,
  getFileSnapshotDiff,
} from '@/core/api/groupChatApi';
import type { MessageApiItem } from '@/shared/types';
import { RightSidebarContent } from '@/shared/types/layout';
import { ChatInput } from './ChatInput';
import styles from './ChatArea.module.css';

export interface ChatAreaProps {
  onToggleRightSidebar?: () => void;
  onContentChange?: (content: RightSidebarContent | null) => void;
}

const MessageBubble = React.memo(
  ({
    msg,
    avatar,
    pinned,
    onPin,
    onUnpin,
    onQuote,
    onPreview,
    onDiff,
  }: {
    msg: MessageApiItem;
    avatar?: string | null;
    pinned: boolean;
    onPin: () => void;
    onUnpin: () => void;
    onQuote: () => void;
    onPreview: (snapshotId: string, filePath: string) => void;
    onDiff: (snapshotId: string, filePath: string) => void;
  }) => {
    const isUser = msg.speaker === 'user';

    return (
      <div className={`${styles.message} ${isUser ? styles.messageUser : styles.messageAgent}`}>
        {!isUser && (
          <div className={styles.messageHeader}>
            {avatar && (
              <div className={styles.messageAvatar}>
                <AvatarImage avatar={avatar} fallback={msg.speaker} />
              </div>
            )}
            <span className={styles.speakerName}>{msg.speaker}</span>
          </div>
        )}
        <div
          className={`${styles.messageBubble} ${isUser ? styles.bubbleUser : styles.bubbleAgent}`}
        >
          <MarkdownRenderer content={msg.content} />
        </div>
        <div className={`${styles.messageActions} ${isUser ? styles.actionsRight : ''}`}>
          <button
            className={`${styles.pinButton} ${pinned ? styles.pinButtonActive : ''}`}
            onClick={pinned ? onUnpin : onPin}
            title={pinned ? '取消置顶' : '置顶消息'}
          >
            📌
          </button>
          <button className={styles.quoteButton} onClick={onQuote} title="引用消息">
            💬
          </button>
        </div>
        {msg.modified_files && msg.modified_files.length > 0 && (
          <FileChangesCard
            modifiedFiles={msg.modified_files}
            onPreview={onPreview}
            onDiff={onDiff}
          />
        )}
      </div>
    );
  }
);

export function ChatArea({ onToggleRightSidebar, onContentChange }: ChatAreaProps) {
  const {
    messages,
    loading,
    activeTitle,
    activeSessionId,
    roleAvatarMap,
    hasMore,
    loadingMore,
    isRestoringScroll,
    loadMoreWithRestore,
  } = useChatMessages();
  const { members } = useMembers();
  const { pin, unpin, isPinned } = usePinnedMessages(activeSessionId);
  const [localMessages, setLocalMessages] = useState<MessageApiItem[]>([]);
  const [showManageMembers, setShowManageMembers] = useState(false);
  const [quotedMessage, setQuotedMessage] = useState<MessageApiItem | null>(null);
  const [rightSidebarContent, setRightSidebarContent] = useState<RightSidebarContent | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // 合并 API 消息和本地发送的消息（使用 useMemo 优化）
  const allMessages = useMemo(() => [...messages, ...localMessages], [messages, localMessages]);

  // 自动滚动到底部（loadMore 恢复滚动位置期间跳过）
  useEffect(() => {
    if (loadingMore || isRestoringScroll) return;
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [allMessages.length, loadingMore, isRestoringScroll]);

  // 滚动到顶部时加载更多
  const handleScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container || loadingMore || !hasMore) return;
    if (container.scrollTop < 50) {
      loadMoreWithRestore(container);
    }
  }, [loadingMore, hasMore, loadMoreWithRestore]);

  // 切换 session 时清空本地消息
  useEffect(() => {
    setLocalMessages([]);
    setQuotedMessage(null);
  }, [activeSessionId]);

  // 通知 MainLayout 右侧栏内容变化
  useEffect(() => {
    onContentChange?.(rightSidebarContent);
  }, [rightSidebarContent, onContentChange]);

  const handleSend = useCallback(
    async (text: string) => {
      if (!activeSessionId) return;

      // 如果有引用消息，用 MD 引用语法包裹
      let finalText = text;
      if (quotedMessage) {
        const quotedContent = quotedMessage.content
          .split('\n')
          .map((line) => `> ${line}`)
          .join('\n');
        finalText = `${quotedContent}\n\n${text}`;
      }

      // 乐观更新：立即显示用户消息
      const optimisticMsg: MessageApiItem = {
        id: 0, // 临时 id，实际 id 由后端分配
        speaker: 'user',
        content: finalText,
        timestamp: new Date().toISOString(),
        platform: 'user',
      };
      setLocalMessages((prev) => [...prev, optimisticMsg]);

      try {
        const members = await getMembers(activeSessionId);
        const memberNames = members.map((m) => m.name);
        await sendMessage(activeSessionId, { content: finalText, members: memberNames });
        // 发送成功后才清空引用状态
        setQuotedMessage(null);
      } catch (err) {
        console.error('Failed to send message:', err);
        // 发送失败时保留引用状态，用户可重试
      }
    },
    [activeSessionId, quotedMessage]
  );

  const handleQuote = useCallback((msg: MessageApiItem) => {
    setQuotedMessage(msg);
  }, []);

  const handlePreview = useCallback(
    async (snapshotId: string, filePath: string) => {
      if (!activeSessionId) return;
      try {
        const content = await getFileSnapshotContent(activeSessionId, snapshotId);
        setRightSidebarContent({ type: 'preview', content, filePath });
      } catch (error) {
        console.error('Failed to load preview:', error);
      }
    },
    [activeSessionId]
  );

  const handleDiff = useCallback(
    async (snapshotId: string, filePath: string) => {
      if (!activeSessionId) return;
      try {
        const diff = await getFileSnapshotDiff(activeSessionId, snapshotId);
        setRightSidebarContent({ type: 'diff', content: diff, filePath });
      } catch (error) {
        console.error('Failed to load diff:', error);
      }
    },
    [activeSessionId]
  );

  // 未选择会话时的空态
  if (!activeSessionId) {
    return (
      <div className={styles.chatArea}>
        <div className={styles.emptyState}>
          <p className={styles.emptyText}>选择一个会话开始对话</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.chatArea}>
      {/* 对话头部 */}
      <div className={styles.chatHeader}>
        <div className={styles.chatTitle}>{activeTitle ?? '会话'}</div>
        <div className={styles.chatActions}>
          <button
            className={styles.iconBtn}
            onClick={() => setShowManageMembers(true)}
            aria-label="管理群成员"
          >
            <MoreVerticalIcon />
          </button>
          <button className={styles.iconBtn} onClick={onToggleRightSidebar} aria-label="切换右侧栏">
            <RightPanelIcon />
          </button>
        </div>
      </div>

      {/* 管理群成员弹窗 */}
      <ManageMembersDialog
        isOpen={showManageMembers}
        chatId={activeSessionId}
        onClose={() => setShowManageMembers(false)}
      />

      {/* 消息区域 */}
      <div className={styles.chatMessages} ref={messagesContainerRef} onScroll={handleScroll}>
        {loadingMore && <div className={styles.loadingText}>加载更多消息...</div>}
        {loading && allMessages.length === 0 ? (
          <div className={styles.loadingText}>加载中...</div>
        ) : (
          allMessages.map((msg) => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              avatar={roleAvatarMap.get(msg.speaker)}
              pinned={isPinned(msg.id)}
              onPin={() => pin(msg.id)}
              onUnpin={() => unpin(msg.id)}
              onQuote={() => handleQuote(msg)}
              onPreview={handlePreview}
              onDiff={handleDiff}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区 */}
      <ChatInput
        activeSessionId={activeSessionId}
        members={members}
        onSend={handleSend}
        quotedMessage={quotedMessage}
        onClearQuote={() => setQuotedMessage(null)}
      />
    </div>
  );
}
