/**
 * Agents Hub 助手弹窗组件
 *
 * 复用现有单聊组件，提供独立的弹窗界面。
 * 遵循项目统一的 modal 模式：overlay + dialog，isOpen prop 控制显隐。
 *
 * 功能：
 * - 消息列表（支持普通消息、Markdown 渲染、工具调用卡片、导航卡片）
 * - 输入框（支持 Enter 发送、Shift+Enter 换行）
 * - 流式输出
 * - ESC 键关闭、点击 overlay 关闭
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { AvatarImage, MarkdownRenderer } from '@/shared/components';
import { NavigationCard } from '@/shared/components/NavigationCard/NavigationCard';
import { parseNavigationMark } from '@/shared/utils/navigationParser';
import { useSingleChatStore } from '../store/singleChatStore';
import { useSingleChatMessages } from '../hooks/useSingleChatMessages';
import { useSingleChatMembers } from '../hooks/useSingleChatMembers';
import { useNavigationHandler } from '../hooks/useNavigationHandler';
import { useAutoResizeTextarea } from '../hooks/useAutoResizeTextarea';
import { ToolCallCard } from '@/shared/components';
import type { SingleChatMessageApiItem } from '@/shared/types';
import { AssistantSkillCards } from './AssistantSkillCards';
import { useAssistantChat } from '../hooks/useAssistantChat';
import styles from './AgentsHubAssistantModal.module.css';

interface AgentsHubAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * 消息气泡组件
 * 复用自 SingleChatPanel，处理普通消息和导航标记消息
 */
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

export function AgentsHubAssistantModal({ isOpen, onClose }: AgentsHubAssistantModalProps) {
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const singleChats = useSingleChatStore((s) => s.singleChats);
  const draftChat = useSingleChatStore((s) => s.draftChat);

  const { initAssistantChat, startNewChat } = useAssistantChat();
  const { messages, loading, streaming, streamingText, sendMessage } = useSingleChatMessages();
  const { handleNavigation } = useNavigationHandler();
  const { textareaRef, adjustHeight } = useAutoResizeTextarea();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 从已有列表中查找，或用 draft 构造临时对象
  const activeChat = activeSingleChatId
    ? singleChats.find((c) => c.single_chat_id === activeSingleChatId)
    : null;

  const displayChat =
    activeChat ??
    (draftChat
      ? {
          single_chat_id: 'draft',
          single_chat_name: draftChat.single_chat_name,
          type: draftChat.type,
          agent_name: draftChat.agent_name,
          platform: 'claude' as const,
          session_id: null,
          group_chat_id: draftChat.group_chat_id ?? null,
          cwd: '',
          created_at: '',
          last_active_at: '',
        }
      : null);

  // 获取 Agent 头像（通过群聊成员信息）
  const { members } = useSingleChatMembers(displayChat?.group_chat_id ?? null);
  const agentMember = members.find((m) => m.name === displayChat?.agent_name);
  const agentAvatar = agentMember?.role?.avatar ?? null;

  // ESC 键关闭
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // 打开弹窗时查找最近的助手会话
  useEffect(() => {
    if (!isOpen) return;
    initAssistantChat();
  }, [isOpen, initAssistantChat]);

  // 自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current?.scrollIntoView) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingText]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || streaming) return;
    setInput('');
    // 重置 textarea 高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    await sendMessage(trimmed);
  }, [input, streaming, sendMessage, textareaRef]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleSkillSelect = useCallback(
    (prompt: string) => {
      setInput(prompt);
      // 聚焦输入框，让用户可以修改后再发送
      setTimeout(() => {
        textareaRef.current?.focus();
        adjustHeight();
      }, 0);
    },
    [textareaRef, adjustHeight]
  );

  const handleNewChat = useCallback(() => {
    startNewChat();
  }, [startNewChat]);

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.dialog}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="agents-hub-assistant-modal-title"
      >
        {/* 头部 */}
        <div className={styles.header}>
          <div className={styles.avatar}>
            <AvatarImage avatar={agentAvatar} fallback="Agents Hub 助手" />
          </div>
          <h2 id="agents-hub-assistant-modal-title" className={styles.title}>
            Agents Hub 助手
          </h2>
          <button type="button" className={styles.newChatBtn} onClick={handleNewChat}>
            开始新对话
          </button>
          <button type="button" className={styles.closeBtn} onClick={onClose} title="关闭">
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

        {/* 技能卡片 */}
        <div className={styles.skillCardsArea}>
          <AssistantSkillCards onSkillSelect={handleSkillSelect} />
        </div>

        {/* 输入框 */}
        <div className={styles.inputArea}>
          <textarea
            ref={textareaRef}
            className={styles.input}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              adjustHeight();
            }}
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
    </div>
  );
}
