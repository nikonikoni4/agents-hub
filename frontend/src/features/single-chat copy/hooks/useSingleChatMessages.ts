/**
 * 单聊消息 hook
 *
 * 职责：
 * - 订阅 activeSingleChatId，获取消息历史
 * - 通过 core/api/sseClient 发送流式消息
 * - 管理消息列表状态
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getSingleChatMessages } from '@/core/api/singleChatApi';
import { streamSSE } from '@/core/api/sseClient';
import { useSingleChatStore } from '../store/singleChatStore';
import type { SingleChatMessageApiItem, ToolCall } from '@/shared/types';

export function useSingleChatMessages() {
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const [messages, setMessages] = useState<SingleChatMessageApiItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  // 获取消息历史
  useEffect(() => {
    if (!activeSingleChatId) {
      setMessages([]);
      return;
    }

    let cancelled = false;
    setLoading(true);

    getSingleChatMessages(activeSingleChatId)
      .then((msgs) => {
        if (!cancelled) {
          setMessages(msgs);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [activeSingleChatId]);

  // 发送消息（SSE 流式）
  const sendMessage = useCallback(
    async (content: string) => {
      if (!activeSingleChatId || streaming) return;

      const userMsg: SingleChatMessageApiItem = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        model: null,
      };
      setMessages((prev) => [...prev, userMsg]);

      setStreaming(true);
      setStreamingText('');

      const controller = new AbortController();
      abortRef.current = controller;

      let fullText = '';
      const toolCalls: ToolCall[] = [];

      try {
        await streamSSE(
          `/single-chats/${activeSingleChatId}/messages/stream`,
          { content },
          (event) => {
            if (event.type === 'text_delta' && event.content?.text) {
              fullText += event.content.text as string;
              setStreamingText(fullText);
            }
            if (event.type === 'tool_use') {
              toolCalls.push({
                id: event.content.tool_id as string,
                name: event.content.tool_name as string,
                input: event.content.input as Record<string, unknown>,
              });
            }
          },
          controller.signal
        );

        if (fullText || toolCalls.length > 0) {
          const assistantMsg: SingleChatMessageApiItem = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: fullText,
            timestamp: new Date().toISOString(),
            model: null,
            tool_calls: toolCalls.length > 0 ? toolCalls : undefined,
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          console.error('SSE stream error:', err);
        }
      } finally {
        setStreaming(false);
        setStreamingText('');
        abortRef.current = null;
      }
    },
    [activeSingleChatId, streaming]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, loading, streaming, streamingText, sendMessage, cancelStream };
}
