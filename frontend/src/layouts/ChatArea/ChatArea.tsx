import { useState, useCallback, useRef, useEffect } from 'react';
import {
  MoreVerticalIcon,
  RightPanelIcon,
  PlusIcon,
  CheckCircleIcon,
  SendIcon,
  AvatarImage,
} from '@/shared/components';
import { useChatMessages } from '@/features/chat/hooks/useChatMessages';
import { sendMessage, getMembers } from '@/core/api/groupChatApi';
import type { MessageApiItem } from '@/shared/types';
import styles from './ChatArea.module.css';

export interface ChatAreaProps {
  onToggleRightSidebar?: () => void;
}

function MessageBubble({ msg, avatar }: { msg: MessageApiItem; avatar?: string | null }) {
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
      <div className={`${styles.messageBubble} ${isUser ? styles.bubbleUser : styles.bubbleAgent}`}>
        <p>{msg.content}</p>
      </div>
    </div>
  );
}

export function ChatArea({ onToggleRightSidebar }: ChatAreaProps) {
  const { messages, loading, activeTitle, activeSessionId, roleAvatarMap } = useChatMessages();
  const [inputValue, setInputValue] = useState('');
  const [localMessages, setLocalMessages] = useState<MessageApiItem[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 合并 API 消息和本地发送的消息
  const allMessages = [...messages, ...localMessages];

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [allMessages.length]);

  // 切换 session 时清空本地消息
  useEffect(() => {
    setLocalMessages([]);
  }, [activeSessionId]);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || !activeSessionId) return;

    // 乐观更新：立即显示用户消息
    const optimisticMsg: MessageApiItem = {
      speaker: 'user',
      content: text,
      timestamp: new Date().toISOString(),
      platform: 'user',
    };
    setLocalMessages((prev) => [...prev, optimisticMsg]);
    setInputValue('');

    try {
      const members = await getMembers(activeSessionId);
      const memberNames = members.map((m) => m.name);
      await sendMessage(activeSessionId, { content: text, members: memberNames });
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  }, [inputValue, activeSessionId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
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
      <div className={styles.chatMessages}>
        {loading && allMessages.length === 0 ? (
          <div className={styles.loadingText}>加载中...</div>
        ) : (
          allMessages.map((msg, i) => (
            <MessageBubble
              key={i}
              msg={msg}
              avatar={msg.speaker !== 'user' ? roleAvatarMap.get(msg.speaker) : undefined}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区 */}
      <div className={styles.chatInputContainer}>
        <div className={styles.chatInputWrapper}>
          <button className={styles.iconBtn} aria-label="添加附件">
            <PlusIcon />
          </button>
          <input
            type="text"
            className={styles.chatInput}
            placeholder="输入消息..."
            aria-label="输入消息"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button className={styles.iconBtn} aria-label="确认">
            <CheckCircleIcon />
          </button>
          <button className={styles.iconBtn} onClick={handleSend} aria-label="发送消息">
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
