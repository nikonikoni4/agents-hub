import { useEffect, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { getProjectsSummary } from '@/core/api';
import type { RefreshSignal } from '@/shared/types';
import type { ProjectGroup } from '@/shared/adapters/sessionAdapter';
import { extractProjectName } from '@/shared/adapters/sessionAdapter';

export function useGroupChatList() {
  const { projectGroups, setProjectGroups, lastRefreshTrigger, resetProjectSessions } =
    useSessionStore();
  const activeSessionId = useSessionStore((s) => s.activeSessionId);

  const refreshProjectsSummary = useCallback(async () => {
    try {
      const summaries = await getProjectsSummary();

      // 重置所有项目的已加载 sessions，触发重新加载
      const currentGroups = useSessionStore.getState().projectGroups;
      for (const group of currentGroups) {
        if (group.loadedSessions && group.loadedSessions.length > 0) {
          resetProjectSessions(group.projectPath);
        }
      }

      const groups: ProjectGroup[] = summaries.map(
        (summary: { project_path: string; group_chat_count: number }) => ({
          projectPath: summary.project_path,
          projectName: extractProjectName(summary.project_path),
          sessions: [],
          totalCount: summary.group_chat_count,
          loadedSessions: [],
          loadedCount: 0,
          hasMore: summary.group_chat_count > 0,
          isLoading: false,
        })
      );

      setProjectGroups(groups);
    } catch (error) {
      console.error('Failed to fetch projects summary:', error);
    }
  }, [setProjectGroups, resetProjectSessions]);

  // 初始加载
  useEffect(() => {
    refreshProjectsSummary();
  }, [refreshProjectsSummary]);

  // 监听刷新触发（供 refreshGroupChats 使用）
  useEffect(() => {
    if (lastRefreshTrigger > 0) {
      refreshProjectsSummary();
    }
  }, [lastRefreshTrigger, refreshProjectsSummary]);

  // WebSocket 刷新
  useEffect(() => {
    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      if (!signal?.group_chat_id || signal.group_chat_id === activeSessionId) {
        refreshProjectsSummary();
      }
    };
    wsManager.on('refresh', handleRefresh);
    return () => {
      wsManager.off('refresh', handleRefresh);
    };
  }, [refreshProjectsSummary, activeSessionId]);

  return {
    projectGroups,
    refreshGroupChats: useSessionStore.getState().refreshGroupChats,
  };
}
