/**
 * useSessionActions Hook
 *
 * 职责：
 * - 处理 session 切换操作
 * - 标记已读（更新本地存储）
 * - 更新 UI 状态
 *
 * 架构约束：
 * - 管理副作用（Storage 写入）
 * - 不包含 UI 逻辑
 */

import { useSessionStore } from '../store/sessionStore';
import { storage } from '@/core/storage';

export function useSessionActions() {
  const { selectSession, updateSession } = useSessionStore();

  const handleSelectSession = async (sessionId: string) => {
    try {
      // 1. 切换 session
      selectSession(sessionId);

      // 2. 标记为已读
      const now = new Date().toISOString();
      await storage.setLastView(sessionId, now);

      // 3. 更新本地状态（取消未读标记）
      updateSession(sessionId, { isUnread: false });
    } catch (error) {
      console.error('Failed to select session:', error);
    }
  };

  return { handleSelectSession };
}
