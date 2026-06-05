/**
 * useChatMessages Hook
 *
 * 职责：
 * - 根据 activeSessionId 加载消息列表
 * - 提供会话标题
 * - 提供角色头像映射
 *
 * 架构约束：
 * - 管理副作用（API 调用）
 * - 通过 store 订阅 activeSessionId（不直接 import session feature）
 */

import { useState, useEffect } from 'react';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { getMessages } from '@/core/api/groupChatApi';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';
import type { MessageApiItem } from '@/shared/types';

export function useChatMessages() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const projectGroups = useSessionStore((s) => s.projectGroups);

  const [messages, setMessages] = useState<MessageApiItem[]>([]);
  const [roleAvatarMap, setRoleAvatarMap] = useState<Map<string, string | null>>(new Map());
  const [loading, setLoading] = useState(false);

  // 从 store 中查找当前 session 的标题
  const activeTitle =
    projectGroups.flatMap((g) => g.sessions).find((s) => s.id === activeSessionId)?.title ?? null;

  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      setRoleAvatarMap(new Map());
      return;
    }

    let cancelled = false;
    setLoading(true);

    Promise.all([getMessages(activeSessionId), buildRoleAvatarMap()])
      .then(([msgData, avatarMap]) => {
        if (!cancelled) {
          setMessages(msgData);
          setRoleAvatarMap(avatarMap);
        }
      })
      .catch((err) => {
        console.error('Failed to load messages:', err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeSessionId]);

  return { messages, loading, activeTitle, activeSessionId, roleAvatarMap };
}
