/**
 * 单聊消息 hook
 *
 * 职责：
 * - 订阅 activeSingleChatId，获取消息历史
 * - 通过 core/api/sseClient 发送流式消息
 * - 管理消息列表状态
 * - draft 模式：首次消息时自动创建单聊
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getSingleChatMessages } from '@/core/api/singleChatApi';
import { getMemberHistory } from '@/core/api/groupChatApi';
import { streamSSE } from '@/core/api/sseClient';
import { useSingleChatStore } from '../store/singleChatStore';
import type { SingleChatMessageApiItem, ToolCall } from '@/shared/types';

export function useSingleChatMessages(onAssistantReply?: () => void) {
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const draftChat = useSingleChatStore((s) => s.draftChat);
  const promoteDraftToReal = useSingleChatStore((s) => s.promoteDraftToReal);
  const [messages, setMessages] = useState<SingleChatMessageApiItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const abortRef = useRef<AbortController | null>(null);

  // 获取消息历史（支持真实单聊和 draft 模式）
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    // 真实单聊：通过 single_chat_id 获取历史
    if (activeSingleChatId) {
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
    }
    // Draft 模式：通过 group_chat_id 和 agent_name 获取历史
    else if (draftChat?.type === 'continue_group_chat' && draftChat.group_chat_id) {
      getMemberHistory(draftChat.group_chat_id, draftChat.agent_name)
        .then((res) => {
          if (!cancelled) {
            setMessages(res.messages);
            setLoading(false);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setLoading(false);
          }
        });
    } else {
      setMessages([]);
      setLoading(false);
    }

    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [activeSingleChatId, draftChat]);

  // 发送消息（SSE 流式）
  const sendMessage = useCallback(
    async (content: string) => {
      if (streaming) return;
      // 需要有 activeSingleChatId 或 draftChat
      if (!activeSingleChatId && !draftChat) return;

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
      let realChatId: string | null = null;

      // 构造请求体
      const body: Record<string, unknown> = { content };
      if (activeSingleChatId) {
        body.single_chat_id = activeSingleChatId;
      } else if (draftChat) {
        body.agent_name = draftChat.agent_name;
        body.single_chat_name = draftChat.single_chat_name;
        body.type = draftChat.type;
        if (draftChat.group_chat_id) {
          body.group_chat_id = draftChat.group_chat_id;
        }
      }

      try {
        await streamSSE(
          '/single-chats/messages/stream',
          body,
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
          controller.signal,
          (headers) => {
            realChatId = headers.get('X-Single-Chat-Id');
          }
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
          // agent 回复完成，调用回调
          onAssistantReply?.();
        }

        // draft → real：更新 store
        if (draftChat && realChatId && realChatId !== activeSingleChatId) {
          promoteDraftToReal(realChatId, {
            single_chat_id: realChatId,
            single_chat_name: draftChat.single_chat_name,
            type: draftChat.type,
            agent_name: draftChat.agent_name,
            platform: 'claude',
            session_id: null,
            group_chat_id: draftChat.group_chat_id ?? null,
            cwd: '',
            created_at: new Date().toISOString(),
            last_active_at: new Date().toISOString(),
          });
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
    [activeSingleChatId, draftChat, streaming, promoteDraftToReal]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, loading, streaming, streamingText, sendMessage, cancelStream };
}
