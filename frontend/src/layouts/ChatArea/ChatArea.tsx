import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  MoreVerticalIcon,
  RightPanelIcon,
  AvatarImage,
  MarkdownRenderer,
} from '@/shared/components';
import { useChatMessages } from '@/features/chat/hooks/useChatMessages';
import { useMembers } from '@/features/chat/hooks/useMembers';
import { sendMessage, getMembers } from '@/core/api/groupChatApi';
import type { MessageApiItem } from '@/shared/types';
import { ChatInput } from './ChatInput';
import styles from './ChatArea.module.css';

export interface ChatAreaProps {
  onToggleRightSidebar?: () => void;
}

const MessageBubble = React.memo(
  ({ msg, avatar }: { msg: MessageApiItem; avatar?: string | null }) => {
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
      </div>
    );
  }
);

export function ChatArea({ onToggleRightSidebar }: ChatAreaProps) {
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
  const [localMessages, setLocalMessages] = useState<MessageApiItem[]>([]);
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
  }, [activeSessionId]);

  const handleSend = useCallback(
    async (text: string) => {
      if (!activeSessionId) return;

      // 乐观更新：立即显示用户消息
      const optimisticMsg: MessageApiItem = {
        speaker: 'user',
        content: text,
        timestamp: new Date().toISOString(),
        platform: 'user',
      };
      setLocalMessages((prev) => [...prev, optimisticMsg]);

      try {
        const members = await getMembers(activeSessionId);
        const memberNames = members.map((m) => m.name);
        await sendMessage(activeSessionId, { content: text, members: memberNames });
      } catch (err) {
        console.error('Failed to send message:', err);
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
          <button className={styles.iconBtn} aria-label="更多操作">
            <MoreVerticalIcon />
          </button>
          <button className={styles.iconBtn} onClick={onToggleRightSidebar} aria-label="切换右侧栏">
            <RightPanelIcon />
          </button>
        </div>
      </div>

      {/* 消息区域 */}
      <div className={styles.chatMessages} ref={messagesContainerRef} onScroll={handleScroll}>
        {loadingMore && <div className={styles.loadingText}>加载更多消息...</div>}
        {loading && allMessages.length === 0 ? (
          <div className={styles.loadingText}>加载中...</div>
        ) : (
          allMessages.map((msg) => (
            <MessageBubble
              key={msg.timestamp}
              msg={msg}
              avatar={msg.speaker !== 'user' ? roleAvatarMap.get(msg.speaker) : undefined}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区 */}
      <ChatInput activeSessionId={activeSessionId} members={members} onSend={handleSend} />
    </div>
  );
}
