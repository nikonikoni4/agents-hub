/**
 * 私聊 Hook
 *
 * 封装私聊相关的业务逻辑：
 * - API 调用（start/stop）
 * - 3 分钟超时计时器管理
 * - 状态一致性保证
 *
 * 组件通过此 hook 调用私聊功能，不直接操作 API 或 store。
 */

import { useCallback, useEffect, useRef } from 'react';
import { stopPrivateChat as stopPrivateChatApi } from '@/core/api';
import { useToast } from '@/shared/components/Toast/useToast';
import { usePrivateChatStore } from '../store/privateChatStore';

const PRIVATE_CHAT_TIMEOUT = 3 * 60 * 1000; // 3 分钟

export function usePrivateChat() {
  const toast = useToast();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const activeGroupChatId = usePrivateChatStore((s) => s.activeGroupChatId);
  const activeAgentName = usePrivateChatStore((s) => s.activeAgentName);
  const startPrivateChatStore = usePrivateChatStore((s) => s.startPrivateChat);
  const stopPrivateChatStore = usePrivateChatStore((s) => s.stopPrivateChat);

  const isPrivateChat = !!activeGroupChatId && !!activeAgentName;

  // 清除计时器
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // 启动计时器
  const startTimer = useCallback(
    (onTimeout: () => void) => {
      clearTimer();
      timerRef.current = setTimeout(onTimeout, PRIVATE_CHAT_TIMEOUT);
    },
    [clearTimer]
  );

  // 重置计时器（重新开始计时）
  const resetTimer = useCallback(
    (onTimeout: () => void) => {
      startTimer(onTimeout);
    },
    [startTimer]
  );

  // 超时处理（API 成功后才清除前端状态）
  const handleTimeout = useCallback(async () => {
    if (!activeGroupChatId || !activeAgentName) return;

    try {
      await stopPrivateChatApi(activeGroupChatId, activeAgentName);
      // API 成功后才清除前端状态
      stopPrivateChatStore();
      toast.info('单聊已自动退出（3 分钟无活动）');
    } catch (error) {
      console.error('Failed to auto stop private chat:', error);
      // API 失败时不清除前端状态，保持一致性
    }
  }, [activeGroupChatId, activeAgentName, stopPrivateChatStore, toast]);

  // 退出单聊
  const stopPrivateChat = useCallback(async () => {
    if (!activeGroupChatId || !activeAgentName) return false;

    try {
      await stopPrivateChatApi(activeGroupChatId, activeAgentName);
      // API 成功后才清除前端状态
      clearTimer();
      stopPrivateChatStore();
      toast.success('已退出单聊');
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : '退出单聊失败';
      toast.error(message);
      return false;
    }
  }, [activeGroupChatId, activeAgentName, clearTimer, stopPrivateChatStore, toast]);

  // 组件卸载时清除计时器
  useEffect(() => {
    return () => {
      clearTimer();
    };
  }, [clearTimer]);

  return {
    isPrivateChat,
    activeGroupChatId,
    activeAgentName,
    startPrivateChat: startPrivateChatStore,
    stopPrivateChat,
    startTimer,
    resetTimer,
    clearTimer,
    handleTimeout,
  };
}
