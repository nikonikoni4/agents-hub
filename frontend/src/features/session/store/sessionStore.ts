/**
 * Session Store
 *
 * 职责：
 * - 存储项目分组的 sessions（仅群聊）
 * - 管理当前活跃的群聊 session
 * - 提供更新 session 的操作
 * - 支持按项目懒加载和分页
 *
 * 架构约束：
 * - 不包含副作用（API 调用在 hooks 中）
 * - 纯状态管理
 * - 不管理单聊状态（由 singleChatStore 管理）
 */

import { create } from 'zustand';
import { SessionItem, ProjectGroup } from '@/shared/adapters/sessionAdapter';

interface SessionState {
  /** 按项目分组的 sessions（支持分页） */
  projectGroups: ProjectGroup[];
  /** 当前活跃的 session ID */
  activeSessionId: string | null;
  /** 最近一次选择 session 的时间戳 */
  lastSelectedAt: number;
  /** 刷新触发时间戳（用于 refreshGroupChats） */
  lastRefreshTrigger: number;

  // Actions
  /** 设置项目分组 */
  setProjectGroups: (groups: ProjectGroup[]) => void;
  /** 向指定项目追加 sessions */
  appendSessionsToProject: (projectPath: string, sessions: SessionItem[], hasMore: boolean) => void;
  /** 设置项目加载状态 */
  setProjectLoading: (projectPath: string, isLoading: boolean) => void;
  /** 选择群聊 session */
  selectGroupChat: (id: string) => void;
  /** 更新某个 session 的数据 */
  updateSession: (id: string, updates: Partial<SessionItem>) => void;
  /** 清除活跃 session */
  clearActive: () => void;
  /** 触发群聊列表刷新（供删除/创建后使用） */
  refreshGroupChats: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  projectGroups: [],
  activeSessionId: null,
  lastSelectedAt: 0,
  lastRefreshTrigger: 0,

  setProjectGroups: (groups) => set({ projectGroups: groups }),

  appendSessionsToProject: (projectPath, sessions, hasMore) =>
    set((state) => ({
      projectGroups: state.projectGroups.map((group) =>
        group.projectPath === projectPath
          ? {
              ...group,
              loadedSessions: [...(group.loadedSessions || []), ...sessions],
              loadedCount: (group.loadedSessions?.length || 0) + sessions.length,
              hasMore,
              isLoading: false,
            }
          : group
      ),
    })),

  setProjectLoading: (projectPath, isLoading) =>
    set((state) => ({
      projectGroups: state.projectGroups.map((group) =>
        group.projectPath === projectPath ? { ...group, isLoading } : group
      ),
    })),

  selectGroupChat: (id) => set({ activeSessionId: id, lastSelectedAt: Date.now() }),

  updateSession: (id, updates) =>
    set((state) => ({
      projectGroups: state.projectGroups.map((group) => ({
        ...group,
        sessions: group.sessions.map((s) => (s.id === id ? { ...s, ...updates } : s)),
        loadedSessions: group.loadedSessions?.map((s) => (s.id === id ? { ...s, ...updates } : s)),
      })),
    })),

  clearActive: () => set({ activeSessionId: null }),

  refreshGroupChats: () => set({ lastRefreshTrigger: Date.now() }),
}));
