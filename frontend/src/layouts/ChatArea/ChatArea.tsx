import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  MoreVerticalIcon,
  RightPanelIcon,
  AvatarImage,
  MarkdownRenderer,
  PermissionRequest,
} from '@/shared/components';
import { FileChangesCard } from '@/shared/components/FileChangesCard';
import { useChatMessages } from '@/features/chat/hooks/useChatMessages';
import { useMembers } from '@/features/chat/hooks/useMembers';
import { usePinnedMessages } from '@/features/chat/hooks/usePinnedMessages';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { ManageMembersDialog } from '@/features/chat/components/ManageMembersDialog';
import { wsManager } from '@/core/websocket/WebSocketManager';
import {
  sendMessage,
  getMembers,
  getFileSnapshotContent,
  getFileSnapshotDiff,
  updatePermissionStatus,
} from '@/core/api/groupChatApi';
import type { MessageApiItem } from '@/shared/types';
import { RightSidebarContent } from '@/shared/types/layout';
import { extractProjectName } from '@/shared/adapters/sessionAdapter';
import { ChatInput } from './ChatInput';
import styles from './ChatArea.module.css';

export interface ChatAreaProps {
  onToggleRightSidebar?: () => void;
  onContentChange?: (content: RightSidebarContent | null) => void;
}

// SVG 图标
function PinIcon({ active }: { active?: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill={active ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 17v5" />
      <path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 1 1 0 0 0 1-1V4a2 2 0 0 0-2-2H9a2 2 0 0 0-2 2v1a1 1 0 0 0 1 1 1 1 0 0 1 1 1z" />
    </svg>
  );
}

function QuoteIcon() {
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
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <path d="M8 10h.01" />
      <path d="M12 10h.01" />
      <path d="M16 10h.01" />
    </svg>
  );
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
    onPermissionAction,
  }: {
    msg: MessageApiItem;
    avatar?: string | null;
    pinned: boolean;
    onPin: () => void;
    onUnpin: () => void;
    onQuote: () => void;
    onPreview: (snapshotId: string, filePath: string) => void;
    onDiff: (snapshotId: string, filePath: string) => void;
    onPermissionAction: (messageId: number, action: 'approved' | 'rejected') => void;
  }) => {
    const isUser = msg.speaker === 'user';

    // 权限请求消息：渲染 PermissionRequest 卡片
    if (msg.permission_request) {
      const pr = msg.permission_request;
      return (
        <div className={`${styles.message} ${styles.messageAgent}`}>
          <div className={styles.messageHeader}>
            {avatar && (
              <div className={styles.messageAvatar}>
                <AvatarImage avatar={avatar} fallback={msg.speaker} />
              </div>
            )}
            <span className={styles.speakerName}>{msg.speaker}</span>
          </div>
          <PermissionRequest
            title={pr.title}
            content={pr.content}
            timestamp={msg.timestamp}
            status={pr.status}
            agentName={pr.requested_by}
            onApprove={() => onPermissionAction(msg.id, 'approved')}
            onReject={() => onPermissionAction(msg.id, 'rejected')}
          />
          <div className={`${styles.messageActions}`}>
            <button
              className={`${styles.pinButton} ${pinned ? styles.pinButtonActive : ''}`}
              onClick={pinned ? onUnpin : onPin}
              title={pinned ? '取消置顶' : '置顶消息'}
            >
              <PinIcon active={pinned} />
            </button>
            <button className={styles.quoteButton} onClick={onQuote} title="引用消息">
              <QuoteIcon />
            </button>
          </div>
        </div>
      );
    }

    // 普通消息：渲染 Markdown 气泡
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
        {msg.modified_files && msg.modified_files.length > 0 && (
          <FileChangesCard
            modifiedFiles={msg.modified_files}
            onPreview={onPreview}
            onDiff={onDiff}
          />
        )}
        <div className={`${styles.messageActions} ${isUser ? styles.actionsRight : ''}`}>
          <button
            className={`${styles.pinButton} ${pinned ? styles.pinButtonActive : ''}`}
            onClick={pinned ? onUnpin : onPin}
            title={pinned ? '取消置顶' : '置顶消息'}
          >
            <PinIcon active={pinned} />
          </button>
          <button className={styles.quoteButton} onClick={onQuote} title="引用消息">
            <QuoteIcon />
          </button>
        </div>
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
  const projectGroups = useSessionStore((s) => s.projectGroups);
  const activeSessionType = useSessionStore((s) => s.activeSessionType);
  const { singleChats, displayLocation, toggleLocation } = useSingleChatStore();
  const [localMessages, setLocalMessages] = useState<MessageApiItem[]>([]);
  const [showManageMembers, setShowManageMembers] = useState(false);
  const [quotedMessage, setQuotedMessage] = useState<MessageApiItem | null>(null);
  const [rightSidebarContent, setRightSidebarContent] = useState<RightSidebarContent | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const connectedSessionRef = useRef<string | null>(null);

  // 切换 session 时断开旧的 WebSocket 连接
  useEffect(() => {
    return () => {
      if (connectedSessionRef.current) {
        wsManager.disconnect();
        connectedSessionRef.current = null;
      }
    };
  }, [activeSessionId]);

  // 获取当前活跃会话的项目路径
  const activeProjectPath = useMemo(() => {
    if (!activeSessionId) return null;
    for (const group of projectGroups) {
      const session = group.sessions.find((s) => s.id === activeSessionId);
      if (session) {
        return session.projectPath;
      }
    }
    return null;
  }, [activeSessionId, projectGroups]);

  // 合并 API 消息和本地发送的消息（使用 useMemo 优化）
  const allMessages = useMemo(() => [...messages, ...localMessages], [messages, localMessages]);

  // 服务端消息刷新后，清空乐观消息（服务端已包含最新数据）
  useEffect(() => {
    if (messages.length > 0 && localMessages.length > 0) {
      setLocalMessages([]);
    }
  }, [messages]);

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

      // 发送第一条消息时才连接 WebSocket（已连接则跳过）
      if (connectedSessionRef.current !== activeSessionId) {
        wsManager.connect(activeSessionId);
        connectedSessionRef.current = activeSessionId;
      }

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

  // 权限请求操作（调用 API，刷新由 WebSocket refresh 自动处理）
  const handlePermissionAction = useCallback(
    async (messageId: number, action: 'approved' | 'rejected') => {
      if (!activeSessionId) return;
      try {
        await updatePermissionStatus(activeSessionId, messageId, action);
      } catch (err) {
        console.error('Failed to update permission status:', err);
      }
    },
    [activeSessionId]
  );

  // 判断是否显示单聊
  const showingSingleChat = activeSessionType === 'single_chat' && displayLocation === 'main';
  const activeSingleChat = useMemo(() => {
    if (!activeSessionId) return null;
    return singleChats.find((chat) => chat.single_chat_id === activeSessionId);
  }, [activeSessionId, singleChats]);

  // 未选择会话时的空态
  if (!activeSessionType) {
    return (
      <div className={styles.chatArea}>
        <div className={styles.emptyState}>
          <p className={styles.emptyText}>选择一个会话开始对话</p>
        </div>
      </div>
    );
  }

  // 单聊界面
  if (showingSingleChat) {
    return (
      <div className={styles.chatArea}>
        {/* 标题栏 */}
        <div className={styles.chatHeader}>
          <h2 className={styles.chatTitle}>{activeSingleChat?.single_chat_name ?? '单聊'}</h2>
          <div className={styles.chatActions}>
            <button className={styles.toggleLocationBtn} onClick={toggleLocation} title="返回右侧">
              返回右侧
            </button>
            <button className={styles.iconBtn} onClick={onToggleRightSidebar}>
              <RightPanelIcon />
            </button>
          </div>
        </div>

        {/* 消息列表 */}
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
                onPermissionAction={handlePermissionAction}
              />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
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

  // 群聊界面（原有逻辑）
  return (
    <div className={styles.chatArea}>
      {/* 对话头部 */}
      <div className={styles.chatHeader}>
        <div className={styles.chatHeaderInfo}>
          <div className={styles.chatTitle}>{activeTitle ?? '会话'}</div>
          {activeProjectPath && (
            <div className={styles.chatProjectPath} title={activeProjectPath}>
              📁 {extractProjectName(activeProjectPath)}
            </div>
          )}
        </div>
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
              onPermissionAction={handlePermissionAction}
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
