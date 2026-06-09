/**
 * 单聊面板组件
 *
 * 展示在 RightSidebar 的"单聊"tab 中，包含：
 * - Agent 信息头部
 * - 消息列表
 * - 输入框
 */

import { useState, useRef, useEffect } from 'react';
import { AvatarImage, MarkdownRenderer } from '@/shared/components';
import { NavigationCard } from '@/shared/components/NavigationCard/NavigationCard';
import { parseNavigationMark } from '@/shared/utils/navigationParser';
import { useSingleChatStore } from '../store/singleChatStore';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { useSingleChatMessages } from '../hooks/useSingleChatMessages';
import { useSingleChatMembers } from '../hooks/useSingleChatMembers';
import { useNavigationHandler } from '../hooks/useNavigationHandler';
import { ToolCallCard } from './ToolCallCard';
import type { SingleChatMessageApiItem } from '@/shared/types';
import styles from './SingleChatPanel.module.css';

const CHAT_TYPE_LABELS: Record<string, string> = {
  new: '全新',
  fork: 'Fork',
  continue_group_chat: 'Continue',
};

function MessageBubble({
  msg,
  onNavigation,
}: {
  msg: SingleChatMessageApiItem;
  onNavigation?: (navigation: import('@/shared/utils/navigationParser').NavigationMark) => void;
}) {
  const isUser = msg.role === 'user';

  // 检测导航标记
  if (!isUser) {
    const navigation = parseNavigationMark(msg.content);
    if (navigation) {
      return (
        <div className={`${styles.messageRow} ${styles.assistantRow}`}>
          <NavigationCard
            type={navigation.type}
            data={navigation.data}
            linkText={navigation.linkText}
            onNavigate={() => onNavigation?.(navigation)}
          />
        </div>
      );
    }
  }

  return (
    <div className={`${styles.messageRow} ${isUser ? styles.userRow : styles.assistantRow}`}>
      <div className={`${styles.bubble} ${isUser ? styles.userBubble : styles.assistantBubble}`}>
        {/* 工具调用卡片 */}
        {msg.tool_calls && msg.tool_calls.length > 0 && (
          <div className={styles.toolCalls}>
            {msg.tool_calls.map((toolCall) => (
              <ToolCallCard key={toolCall.id} toolCall={toolCall} />
            ))}
          </div>
        )}
        {/* 消息内容 */}
        {isUser ? <span>{msg.content}</span> : <MarkdownRenderer content={msg.content} />}
      </div>
    </div>
  );
}

export function SingleChatPanel() {
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const singleChats = useSingleChatStore((s) => s.singleChats);
  const closeSingleChat = useSingleChatStore((s) => s.closeSingleChat);
  const toggleLocation = useSingleChatStore((s) => s.toggleLocation);
  const selectSession = useSessionStore((s) => s.selectSession);

  const { messages, loading, streaming, streamingText, sendMessage } = useSingleChatMessages();
  const { handleNavigation } = useNavigationHandler();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeChat = singleChats.find((c) => c.single_chat_id === activeSingleChatId);

  // 点击移到主界面时，同时激活单聊 session
  const handleToggleLocation = () => {
    if (activeSingleChatId) {
      selectSession(activeSingleChatId, 'single_chat');
    }
    toggleLocation();
  };

  // 获取 Agent 头像（通过群聊成员信息）
  const { members } = useSingleChatMembers(activeChat?.group_chat_id ?? null);
  const agentMember = members.find((m) => m.name === activeChat?.agent_name);
  const agentAvatar = agentMember?.role?.avatar ?? null;

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || streaming) return;
    setInput('');
    await sendMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!activeChat) {
    return (
      <div className={styles.emptyState}>
        <p>创建一个单聊开始对话</p>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      {/* Agent 信息头部 */}
      <div className={styles.agentHeader}>
        <div className={styles.agentAvatar}>
          <AvatarImage avatar={agentAvatar} fallback={activeChat.agent_name} />
        </div>
        <div className={styles.agentInfo}>
          <span className={styles.agentName}>{activeChat.agent_name}</span>
          <span className={styles.chatType}>
            {CHAT_TYPE_LABELS[activeChat.type] ?? activeChat.type}
          </span>
        </div>
        <button
          type="button"
          className={styles.toggleLocationBtn}
          onClick={handleToggleLocation}
          title="移到主界面"
        >
          📍
        </button>
        <button
          type="button"
          className={styles.closeBtn}
          onClick={closeSingleChat}
          title="关闭单聊"
        >
          ×
        </button>
      </div>

      {/* 消息列表 */}
      <div className={styles.messages}>
        {loading ? (
          <div className={styles.emptyState}>加载中...</div>
        ) : messages.length === 0 && !streaming ? (
          <div className={styles.emptyState}>发送消息开始对话</div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} onNavigation={handleNavigation} />
            ))}
            {streaming && streamingText && (
              <div className={`${styles.messageRow} ${styles.assistantRow}`}>
                <div className={`${styles.bubble} ${styles.assistantBubble}`}>
                  <MarkdownRenderer content={streamingText} />
                  <span className={styles.cursor} />
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className={styles.inputArea}>
        <textarea
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息..."
          rows={1}
        />
        <button
          type="button"
          className={styles.sendBtn}
          onClick={handleSend}
          disabled={!input.trim() || streaming}
        >
          发送
        </button>
      </div>
    </div>
  );
}
