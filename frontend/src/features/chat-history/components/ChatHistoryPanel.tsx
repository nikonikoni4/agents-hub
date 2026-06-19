import { useRef, useEffect } from 'react';
import { MarkdownRenderer, ToolCallCard } from '@/shared/components';
import { useChatHistory } from '../hooks/useChatHistory';
import styles from './ChatHistoryPanel.module.css';

interface ChatHistoryPanelProps {
  chatId: string;
  agentName: string;
  onClose: () => void;
}

function formatTime(timestamp: string): string {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return timestamp;
  }
}

export function ChatHistoryPanel({ chatId, agentName, onClose }: ChatHistoryPanelProps) {
  const { messages, loading, refresh } = useChatHistory(chatId, agentName);
  const listRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div>
          <div className={styles.headerTitle}>{agentName} 历史记录</div>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.refreshBtn} onClick={refresh} disabled={loading} title="刷新">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 2v6h-6" />
              <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
              <path d="M3 22v-6h6" />
              <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
            </svg>
          </button>
          <button className={styles.closeBtn} onClick={onClose} title="关闭">
            ×
          </button>
        </div>
      </div>

      {loading ? (
        <div className={styles.loading}>加载中...</div>
      ) : messages.length === 0 ? (
        <div className={styles.empty}>暂无历史记录</div>
      ) : (
        <div className={styles.messageList} ref={listRef}>
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`${styles.message} ${msg.role === 'user' ? styles.messageUser : styles.messageAssistant}`}
            >
              <div className={styles.messageRole}>{msg.role === 'user' ? 'User' : 'Assistant'}</div>
              <div className={styles.messageBubble}>
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className={styles.toolCalls}>
                    {msg.tool_calls.map((tc) => (
                      <ToolCallCard key={tc.id} toolCall={tc} />
                    ))}
                  </div>
                )}
                {msg.role === 'assistant' ? (
                  <MarkdownRenderer content={msg.content} />
                ) : (
                  msg.content
                )}
              </div>
              {msg.timestamp && (
                <div className={styles.messageTimestamp}>{formatTime(msg.timestamp)}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
