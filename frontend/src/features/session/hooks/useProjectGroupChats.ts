import { useCallback, useRef } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { listGroupChatsWithPagination, getMembers } from '@/core/api';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';
import type { SessionItem } from '@/shared/adapters/sessionAdapter';

/**
 * 管理单个项目的群聊加载
 *
 * @param projectPath - 项目路径
 */
export function useProjectGroupChats(projectPath: string) {
  const { appendSessionsToProject, setProjectLoading } = useSessionStore();
  const project = useSessionStore((s) =>
    s.projectGroups.find((g) => g.projectPath === projectPath)
  );

  const loadingRef = useRef(false);

  const loadMore = useCallback(async () => {
    if (loadingRef.current || !project || !project.hasMore) return;

    loadingRef.current = true;
    setProjectLoading(projectPath, true);

    try {
      const response = await listGroupChatsWithPagination({
        projectPath,
        limit: 10,
        offset: project.loadedCount,
      });

      // 加载成员头像
      const roleAvatarMap = await buildRoleAvatarMap();
      const sessionsWithAvatars: SessionItem[] = [];

      for (const chat of response.items) {
        const members = await getMembers(chat.group_chat_id).catch(() => []);

        sessionsWithAvatars.push({
          id: chat.group_chat_id,
          title: chat.group_chat_name || 'Untitled',
          preview: chat.last_message || '',
          lastUpdateAt: new Date(chat.last_update_at || chat.created_at),
          lastViewAt: null,
          isUnread: false,
          memberCount: members.length,
          projectPath: chat.project_path,
          memberAvatars: members.slice(0, 4).map((m) => roleAvatarMap.get(m.name) ?? null),
          type: 'group_chat',
        });
      }

      appendSessionsToProject(projectPath, sessionsWithAvatars, response.has_more);
    } catch (error) {
      console.error('Failed to load group chats:', error);
      setProjectLoading(projectPath, false);
    } finally {
      loadingRef.current = false;
    }
  }, [project, projectPath, appendSessionsToProject, setProjectLoading]);

  return {
    sessions: project?.loadedSessions ?? [],
    hasMore: project?.hasMore ?? false,
    isLoading: project?.isLoading ?? false,
    totalCount: project?.totalCount ?? 0,
    loadMore,
  };
}
