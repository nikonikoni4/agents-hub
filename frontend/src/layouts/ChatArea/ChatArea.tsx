import { useState, useCallback, useRef, useEffect } from 'react';
import {
  MoreVerticalIcon,
  RightPanelIcon,
  PlusIcon,
  CheckCircleIcon,
  SendIcon,
  AvatarImage,
  MarkdownRenderer,
} from '@/shared/components';
import { useChatMessages } from '@/features/chat/hooks/useChatMessages';
import { useMembers } from '@/features/chat/hooks/useMembers';
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
        <MarkdownRenderer content={msg.content} />
      </div>
    </div>
  );
}

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
  const [inputValue, setInputValue] = useState('');
  const [localMessages, setLocalMessages] = useState<MessageApiItem[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // @成员选择状态
  const [showMention, setShowMention] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionIndex, setMentionIndex] = useState(0);

  // 过滤匹配的成员
  const filteredMembers = mentionQuery
    ? members.filter((m) => m.name.toLowerCase().includes(mentionQuery.toLowerCase()))
    : members;

  // 合并 API 消息和本地发送的消息
  const allMessages = [...messages, ...localMessages];

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

  // 自动调整 textarea 高度
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, []);

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
    setShowMention(false);

    try {
      const members = await getMembers(activeSessionId);
      const memberNames = members.map((m) => m.name);
      await sendMessage(activeSessionId, { content: text, members: memberNames });
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  }, [inputValue, activeSessionId]);

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
        handleSend();
      }
    },
    [handleSend, showMention, filteredMembers, mentionIndex, handleMentionSelect]
  );

  // 点击外部关闭 mention 下拉框
  useEffect(() => {
    if (!showMention) return;
    const handleClickOutside = () => setShowMention(false);
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showMention]);

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
          <button className={styles.iconBtn} onClick={handleSend} aria-label="发送消息">
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
