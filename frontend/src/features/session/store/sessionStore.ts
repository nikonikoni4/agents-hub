/**
 * Session Store
 *
 * 职责：
 * - 存储项目分组的 sessions（仅群聊）
 * - 管理当前活跃的群聊 session
 * - 提供更新 session 的操作
 *
 * 架构约束：
 * - 不包含副作用（API 调用在 hooks 中）
 * - 纯状态管理
 * - 不管理单聊状态（由 singleChatStore 管理）
 */

import { create } from 'zustand';
import { ProjectGroup, SessionItem } from '@/shared/adapters/sessionAdapter';

interface SessionState {
  /** 按项目分组的 sessions */
  projectGroups: ProjectGroup[];
  /** 当前活跃的 session ID */
  activeSessionId: string | null;
  /** 最近一次选择 session 的时间戳 */
  lastSelectedAt: number;

  // Actions
  /** 设置项目分组 */
  setProjectGroups: (groups: ProjectGroup[]) => void;
  /** 选择群聊 session */
  selectGroupChat: (id: string) => void;
  /** 更新某个 session 的数据 */
  updateSession: (id: string, updates: Partial<SessionItem>) => void;
  /** 清除活跃 session */
  clearActive: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  projectGroups: [],
  activeSessionId: null,
  lastSelectedAt: 0,

  setProjectGroups: (groups) => set({ projectGroups: groups }),

  selectGroupChat: (id) => set({ activeSessionId: id, lastSelectedAt: Date.now() }),

  updateSession: (id, updates) =>
    set((state) => ({
      projectGroups: state.projectGroups.map((group) => ({
        ...group,
        sessions: group.sessions.map((s) => (s.id === id ? { ...s, ...updates } : s)),
      })),
    })),

  clearActive: () => set({ activeSessionId: null }),
}));
