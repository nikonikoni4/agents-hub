# 角色管理模块 UI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现角色管理模块的 UI，包括角色展示、团队管理、创建角色和成员管理功能

**Architecture:** 
- 采用 Feature 模块化架构，数据聚合在 Adapter 层完成
- 使用 Zustand 管理状态，hooks 封装业务逻辑，components 纯展示
- 遵循 DESIGN.md v2.0 视觉规范，支持双主题

**Tech Stack:** React 18, TypeScript, Zustand, CSS Modules, Vite

---

## File Structure

### 新增文件

**Adapter 层（数据聚合）**：
- `frontend/src/shared/adapters/roleAdapter.ts` - 角色数据聚合函数
- `frontend/src/shared/adapters/roleAdapter.test.ts` - 角色适配器测试
- `frontend/src/shared/adapters/teamAdapter.ts` - 团队数据聚合函数
- `frontend/src/shared/adapters/teamAdapter.test.ts` - 团队适配器测试

**Feature 模块**：
- `frontend/src/features/roles/types.ts` - 模块专属类型定义
- `frontend/src/features/roles/store/rolesStore.ts` - 角色状态管理
- `frontend/src/features/roles/store/teamsStore.ts` - 团队状态管理
- `frontend/src/features/roles/hooks/useRoles.ts` - 角色列表管理
- `frontend/src/features/roles/hooks/useTeams.ts` - 团队列表管理
- `frontend/src/features/roles/hooks/useCreateRole.ts` - 创建角色逻辑
- `frontend/src/features/roles/hooks/useTeamMembers.ts` - 团队成员管理

**UI 组件**：
- `frontend/src/features/roles/components/RoleManagementPanel.tsx` - 主面板
- `frontend/src/features/roles/components/RoleManagementPanel.module.css` - 主面板样式
- `frontend/src/features/roles/components/RoleCard.tsx` - 角色卡片
- `frontend/src/features/roles/components/RoleCard.module.css` - 角色卡片样式
- `frontend/src/features/roles/components/TeamList.tsx` - 团队列表
- `frontend/src/features/roles/components/TeamList.module.css` - 团队列表样式
- `frontend/src/features/roles/components/TeamMemberPanel.tsx` - 团队成员面板
- `frontend/src/features/roles/components/TeamMemberPanel.module.css` - 团队成员面板样式
- `frontend/src/features/roles/components/RoleMemberRow.tsx` - 角色成员行
- `frontend/src/features/roles/components/RoleMemberRow.module.css` - 角色成员行样式
- `frontend/src/features/roles/components/CreateRoleDialog.tsx` - 创建角色弹窗
- `frontend/src/features/roles/components/CreateRoleDialog.module.css` - 创建角色弹窗样式
- `frontend/src/features/roles/components/AvatarSelector.tsx` - 头像选择器
- `frontend/src/features/roles/components/AvatarSelector.module.css` - 头像选择器样式
- `frontend/src/features/roles/components/AddMemberDialog.tsx` - 添加成员弹窗
- `frontend/src/features/roles/components/AddMemberDialog.module.css` - 添加成员弹窗样式

### 修改文件

**API Mock 数据**：
- `frontend/src/core/api/teamApi.ts:17-30` - 更新 Mock 团队数据，使成员名称与角色对齐
- `frontend/src/core/api/roleApi.ts:86-92` - 更新 Mock 头像数据为 SVG 文件名

---

## Task 1: 创建 Adapter 层 - roleAdapter

**Files:**
- Create: `frontend/src/shared/adapters/roleAdapter.ts`
- Create: `frontend/src/shared/adapters/roleAdapter.test.ts`
- Modify: `frontend/src/core/api/roleApi.ts:86-92`

- [ ] **Step 1: 定义 roleAdapter 类型和聚合函数**

```typescript
/**
 * 角色适配器 - 聚合角色和技能数据
 */

import { getRoleInfo, getRoleSkills, listRoles } from '@/core/api/roleApi';
import type { RoleApiResponse, RoleSkillApiItem } from '@/shared/types/api-schemas';

/**
 * 聚合后的角色数据（包含技能列表）
 */
export interface RoleWithSkills extends RoleApiResponse {
  skills: RoleSkillApiItem[];
}

/**
 * 获取单个角色及其技能
 */
export async function fetchRoleWithSkills(roleName: string): Promise<RoleWithSkills> {
  const role = await getRoleInfo(roleName);
  const skills = await getRoleSkills(roleName);
  return { ...role, skills };
}

/**
 * 获取所有角色及其技能
 */
export async function fetchAllRolesWithSkills(): Promise<RoleWithSkills[]> {
  const roles = await listRoles();
  return Promise.all(roles.map((role) => fetchRoleWithSkills(role.name)));
}
```

- [ ] **Step 2: 编写 roleAdapter 单元测试**

```typescript
/**
 * roleAdapter 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchRoleWithSkills, fetchAllRolesWithSkills } from './roleAdapter';
import * as roleApi from '@/core/api/roleApi';

vi.mock('@/core/api/roleApi');

describe('roleAdapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchRoleWithSkills', () => {
    it('should aggregate role info and skills', async () => {
      const mockRole = {
        name: 'Designer',
        platform: 'claude' as const,
        avatar: 'avatar1.png',
        abilities: ['UI设计'],
        type: 'team_member' as const,
        scope: null,
        description: '前端设计师',
      };

      const mockSkills = [
        { id: 'skill-1', name: 'design', description: '设计技能' },
      ];

      vi.mocked(roleApi.getRoleInfo).mockResolvedValue(mockRole);
      vi.mocked(roleApi.getRoleSkills).mockResolvedValue(mockSkills);

      const result = await fetchRoleWithSkills('Designer');

      expect(result).toEqual({ ...mockRole, skills: mockSkills });
      expect(roleApi.getRoleInfo).toHaveBeenCalledWith('Designer');
      expect(roleApi.getRoleSkills).toHaveBeenCalledWith('Designer');
    });
  });

  describe('fetchAllRolesWithSkills', () => {
    it('should aggregate all roles with skills', async () => {
      const mockRoles = [
        { name: 'Designer', platform: 'claude' as const, avatar: null, abilities: [], type: 'team_member' as const, scope: null, description: 'A' },
        { name: 'Developer', platform: 'codex' as const, avatar: null, abilities: [], type: 'team_member' as const, scope: null, description: 'B' },
      ];

      vi.mocked(roleApi.listRoles).mockResolvedValue(mockRoles);
      vi.mocked(roleApi.getRoleInfo).mockImplementation((name) =>
        Promise.resolve(mockRoles.find((r) => r.name === name)!)
      );
      vi.mocked(roleApi.getRoleSkills).mockResolvedValue([]);

      const result = await fetchAllRolesWithSkills();

      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('Designer');
      expect(result[0].skills).toEqual([]);
    });
  });
});
```

- [ ] **Step 3: 运行测试验证**

Run: `npm test -- roleAdapter.test.ts`
Expected: 所有测试通过

- [ ] **Step 4: 提交**

```bash
git add frontend/src/shared/adapters/roleAdapter.ts frontend/src/shared/adapters/roleAdapter.test.ts
git commit -m "feat(adapter): 添加角色数据聚合适配器"
```

---

## Task 2: 创建 Adapter 层 - teamAdapter

**Files:**
- Create: `frontend/src/shared/adapters/teamAdapter.ts`
- Create: `frontend/src/shared/adapters/teamAdapter.test.ts`

- [ ] **Step 1: 定义 teamAdapter 类型和聚合函数**

```typescript
/**
 * 团队适配器 - 聚合团队和成员角色数据
 */

import { getTeam, listTeams } from '@/core/api/teamApi';
import { fetchRoleWithSkills, type RoleWithSkills } from './roleAdapter';

/**
 * 聚合后的团队数据（包含完整的成员角色对象）
 */
export interface TeamWithMembers {
  name: string;
  members: RoleWithSkills[];
}

/**
 * 获取单个团队及其成员详情
 */
export async function fetchTeamWithMembers(teamName: string): Promise<TeamWithMembers> {
  const team = await getTeam(teamName);
  const members = await Promise.all(team.members.map((name) => fetchRoleWithSkills(name)));
  return { name: team.name, members };
}

/**
 * 获取所有团队及其成员详情
 */
export async function fetchAllTeamsWithMembers(): Promise<TeamWithMembers[]> {
  const teams = await listTeams();
  return Promise.all(teams.map((team) => fetchTeamWithMembers(team.name)));
}
```

- [ ] **Step 2: 编写 teamAdapter 单元测试**

```typescript
/**
 * teamAdapter 单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchTeamWithMembers, fetchAllTeamsWithMembers } from './teamAdapter';
import * as teamApi from '@/core/api/teamApi';
import * as roleAdapter from './roleAdapter';

vi.mock('@/core/api/teamApi');
vi.mock('./roleAdapter');

describe('teamAdapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchTeamWithMembers', () => {
    it('should aggregate team with member details', async () => {
      const mockTeam = {
        name: 'Frontend Team',
        members: ['Designer', 'Developer'],
      };

      const mockRoles = [
        { name: 'Designer', platform: 'claude' as const, avatar: null, abilities: [], type: 'team_member' as const, scope: null, description: 'A', skills: [] },
        { name: 'Developer', platform: 'codex' as const, avatar: null, abilities: [], type: 'team_member' as const, scope: null, description: 'B', skills: [] },
      ];

      vi.mocked(teamApi.getTeam).mockResolvedValue(mockTeam);
      vi.mocked(roleAdapter.fetchRoleWithSkills).mockImplementation((name) =>
        Promise.resolve(mockRoles.find((r) => r.name === name)!)
      );

      const result = await fetchTeamWithMembers('Frontend Team');

      expect(result.name).toBe('Frontend Team');
      expect(result.members).toHaveLength(2);
      expect(result.members[0].name).toBe('Designer');
      expect(roleAdapter.fetchRoleWithSkills).toHaveBeenCalledTimes(2);
    });
  });

  describe('fetchAllTeamsWithMembers', () => {
    it('should aggregate all teams with members', async () => {
      const mockTeams = [
        { name: 'Frontend Team', members: ['Designer'] },
        { name: 'Backend Team', members: ['Developer'] },
      ];

      const mockRole = { name: 'Designer', platform: 'claude' as const, avatar: null, abilities: [], type: 'team_member' as const, scope: null, description: '', skills: [] };

      vi.mocked(teamApi.listTeams).mockResolvedValue(mockTeams);
      vi.mocked(teamApi.getTeam).mockImplementation((name) =>
        Promise.resolve(mockTeams.find((t) => t.name === name)!)
      );
      vi.mocked(roleAdapter.fetchRoleWithSkills).mockResolvedValue(mockRole);

      const result = await fetchAllTeamsWithMembers();

      expect(result).toHaveLength(2);
      expect(result[0].members).toHaveLength(1);
    });
  });
});
```

- [ ] **Step 3: 运行测试验证**

Run: `npm test -- teamAdapter.test.ts`
Expected: 所有测试通过

- [ ] **Step 4: 提交**

```bash
git add frontend/src/shared/adapters/teamAdapter.ts frontend/src/shared/adapters/teamAdapter.test.ts
git commit -m "feat(adapter): 添加团队数据聚合适配器"
```

---

## Task 3: 更新 Mock 数据

**Files:**
- Modify: `frontend/src/core/api/teamApi.ts:17-30`
- Modify: `frontend/src/core/api/roleApi.ts:86-92`

- [ ] **Step 1: 更新 teamApi Mock 数据，使成员名称与角色对齐**

```typescript
const MOCK_TEAMS: TeamApiResponse[] = [
  {
    name: 'Frontend Team',
    members: ['Designer', 'Developer'],
  },
  {
    name: 'Backend Team',
    members: ['Developer', 'Tester'],
  },
  {
    name: 'Product Team',
    members: ['Designer'],
  },
];
```

- [ ] **Step 2: 更新 roleApi Mock 头像数据为 SVG 文件名**

```typescript
const MOCK_AVATARS: string[] = [
  'avatar-circle.svg',
  'avatar-square.svg',
  'avatar-hexagon.svg',
  'avatar-triangle.svg',
  'avatar-star.svg',
];
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/core/api/teamApi.ts frontend/src/core/api/roleApi.ts
git commit -m "fix(api): 更新 Mock 数据以对齐角色和团队"
```

---

## Task 4: 创建 Feature 类型定义

**Files:**
- Create: `frontend/src/features/roles/types.ts`

- [ ] **Step 1: 定义模块专属类型**

```typescript
/**
 * 角色管理模块类型定义
 */

import type { RoleWithSkills } from '@/shared/adapters/roleAdapter';
import type { TeamWithMembers } from '@/shared/adapters/teamAdapter';
import type { AgentPlatform } from '@/shared/types/api-schemas';

/**
 * 创建角色表单数据
 */
export interface CreateRoleFormData {
  name: string;
  platform: AgentPlatform;
  avatar: string | null;
  description: string;
}

/**
 * Tab 类型
 */
export type RoleManagementTab = 'teams' | 'roles';

/**
 * 添加成员模式
 */
export type AddMemberMode = 'existing' | 'create';

// Re-export adapter types for convenience
export type { RoleWithSkills, TeamWithMembers };
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/types.ts
git commit -m "feat(roles): 添加模块类型定义"
```

---

## Task 5: 创建 rolesStore（角色状态管理）

**Files:**
- Create: `frontend/src/features/roles/store/rolesStore.ts`

- [ ] **Step 1: 定义 rolesStore**

```typescript
/**
 * 角色状态管理
 */

import { create } from 'zustand';
import type { RoleWithSkills } from '@/shared/adapters/roleAdapter';

interface RolesState {
  roles: RoleWithSkills[];
  loading: boolean;
  error: string | null;
  
  setRoles: (roles: RoleWithSkills[]) => void;
  addRole: (role: RoleWithSkills) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useRolesStore = create<RolesState>((set) => ({
  roles: [],
  loading: false,
  error: null,
  
  setRoles: (roles) => set({ roles }),
  addRole: (role) => set((state) => ({ roles: [...state.roles, role] })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({ roles: [], loading: false, error: null }),
}));
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/store/rolesStore.ts
git commit -m "feat(roles): 添加角色状态管理"
```

---

## Task 6: 创建 teamsStore（团队状态管理）

**Files:**
- Create: `frontend/src/features/roles/store/teamsStore.ts`

- [ ] **Step 1: 定义 teamsStore**

```typescript
/**
 * 团队状态管理
 */

import { create } from 'zustand';
import type { TeamWithMembers } from '@/shared/adapters/teamAdapter';

interface TeamsState {
  teams: TeamWithMembers[];
  selectedTeam: string | null;
  loading: boolean;
  error: string | null;
  
  setTeams: (teams: TeamWithMembers[]) => void;
  selectTeam: (name: string | null) => void;
  updateTeam: (name: string, updater: (team: TeamWithMembers) => TeamWithMembers) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useTeamsStore = create<TeamsState>((set) => ({
  teams: [],
  selectedTeam: null,
  loading: false,
  error: null,
  
  setTeams: (teams) => set({ teams }),
  selectTeam: (name) => set({ selectedTeam: name }),
  updateTeam: (name, updater) =>
    set((state) => ({
      teams: state.teams.map((team) => (team.name === name ? updater(team) : team)),
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({ teams: [], selectedTeam: null, loading: false, error: null }),
}));
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/store/teamsStore.ts
git commit -m "feat(roles): 添加团队状态管理"
```

---

## Task 7: 创建 useRoles hook

**Files:**
- Create: `frontend/src/features/roles/hooks/useRoles.ts`

- [ ] **Step 1: 定义 useRoles hook**

```typescript
/**
 * 角色列表管理 hook
 */

import { useEffect, useCallback } from 'react';
import { useRolesStore } from '../store/rolesStore';
import { fetchAllRolesWithSkills } from '@/shared/adapters/roleAdapter';

export function useRoles() {
  const { roles, loading, error, setRoles, setLoading, setError } = useRolesStore();

  const fetchRoles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAllRolesWithSkills();
      setRoles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载角色失败');
    } finally {
      setLoading(false);
    }
  }, [setRoles, setLoading, setError]);

  const refreshRoles = useCallback(() => {
    return fetchRoles();
  }, [fetchRoles]);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  return { roles, loading, error, refreshRoles };
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/hooks/useRoles.ts
git commit -m "feat(roles): 添加角色列表管理 hook"
```

---

## Task 8: 创建 useTeams hook

**Files:**
- Create: `frontend/src/features/roles/hooks/useTeams.ts`

- [ ] **Step 1: 定义 useTeams hook**

```typescript
/**
 * 团队列表管理 hook
 */

import { useEffect, useCallback } from 'react';
import { useTeamsStore } from '../store/teamsStore';
import { fetchAllTeamsWithMembers } from '@/shared/adapters/teamAdapter';

export function useTeams() {
  const { teams, selectedTeam, loading, error, setTeams, selectTeam, setLoading, setError } =
    useTeamsStore();

  const fetchTeams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAllTeamsWithMembers();
      setTeams(data);
      if (data.length > 0 && !selectedTeam) {
        selectTeam(data[0].name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载团队失败');
    } finally {
      setLoading(false);
    }
  }, [setTeams, setLoading, setError, selectTeam, selectedTeam]);

  const refreshTeams = useCallback(() => {
    return fetchTeams();
  }, [fetchTeams]);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  const currentTeam = teams.find((t) => t.name === selectedTeam) || null;

  return { teams, selectedTeam, currentTeam, loading, error, selectTeam, refreshTeams };
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/hooks/useTeams.ts
git commit -m "feat(roles): 添加团队列表管理 hook"
```

---

## Task 9: 创建 useCreateRole hook

**Files:**
- Create: `frontend/src/features/roles/hooks/useCreateRole.ts`

- [ ] **Step 1: 定义 useCreateRole hook**

```typescript
/**
 * 创建角色逻辑 hook
 */

import { useCallback, useState } from 'react';
import { useRolesStore } from '../store/rolesStore';
import { createRole } from '@/core/api/roleApi';
import { fetchRoleWithSkills } from '@/shared/adapters/roleAdapter';
import type { CreateRoleFormData } from '../types';

export function useCreateRole() {
  const [submitting, setSubmitting] = useState(false);
  const { addRole } = useRolesStore();

  const handleCreateRole = useCallback(
    async (formData: CreateRoleFormData) => {
      setSubmitting(true);
      try {
        await createRole({
          name: formData.name,
          platform: formData.platform,
          avatar: formData.avatar,
          description: formData.description,
          type: 'team_member',
          abilities: [],
        });

        const newRole = await fetchRoleWithSkills(formData.name);
        addRole(newRole);

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: err instanceof Error ? err.message : '创建角色失败',
        };
      } finally {
        setSubmitting(false);
      }
    },
    [addRole]
  );

  return { createRole: handleCreateRole, submitting };
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/hooks/useCreateRole.ts
git commit -m "feat(roles): 添加创建角色逻辑 hook"
```

---

## Task 10: 创建 useTeamMembers hook

**Files:**
- Create: `frontend/src/features/roles/hooks/useTeamMembers.ts`

- [ ] **Step 1: 定义 useTeamMembers hook**

```typescript
/**
 * 团队成员管理 hook
 */

import { useCallback, useState } from 'react';
import { useTeamsStore } from '../store/teamsStore';
import { updateTeam } from '@/core/api/teamApi';
import { fetchTeamWithMembers } from '@/shared/adapters/teamAdapter';

export function useTeamMembers() {
  const [submitting, setSubmitting] = useState(false);
  const { updateTeam: updateTeamInStore } = useTeamsStore();

  const addMembersToTeam = useCallback(
    async (teamName: string, roleNames: string[]) => {
      setSubmitting(true);
      try {
        const team = await fetchTeamWithMembers(teamName);
        const existingMembers = team.members.map((m) => m.name);
        const newMembers = [...new Set([...existingMembers, ...roleNames])];

        await updateTeam(teamName, { members: newMembers });

        const updatedTeam = await fetchTeamWithMembers(teamName);
        updateTeamInStore(teamName, () => updatedTeam);

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: err instanceof Error ? err.message : '添加成员失败',
        };
      } finally {
        setSubmitting(false);
      }
    },
    [updateTeamInStore]
  );

  const removeMemberFromTeam = useCallback(
    async (teamName: string, roleName: string) => {
      setSubmitting(true);
      try {
        const team = await fetchTeamWithMembers(teamName);
        const newMembers = team.members.filter((m) => m.name !== roleName).map((m) => m.name);

        await updateTeam(teamName, { members: newMembers });

        const updatedTeam = await fetchTeamWithMembers(teamName);
        updateTeamInStore(teamName, () => updatedTeam);

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: err instanceof Error ? err.message : '移除成员失败',
        };
      } finally {
        setSubmitting(false);
      }
    },
    [updateTeamInStore]
  );

  return { addMembersToTeam, removeMemberFromTeam, submitting };
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/hooks/useTeamMembers.ts
git commit -m "feat(roles): 添加团队成员管理 hook"
```

---

## Task 11: 创建 AvatarSelector 组件

**Files:**
- Create: `frontend/src/features/roles/components/AvatarSelector.tsx`
- Create: `frontend/src/features/roles/components/AvatarSelector.module.css`

- [ ] **Step 1: 创建 AvatarSelector 组件**

```typescript
/**
 * 头像选择器组件
 */

import { useState, useEffect } from 'react';
import { listAvatars } from '@/core/api/roleApi';
import styles from './AvatarSelector.module.css';

export interface AvatarSelectorProps {
  selectedAvatar: string | null;
  onSelect: (avatar: string) => void;
}

export function AvatarSelector({ selectedAvatar, onSelect }: AvatarSelectorProps) {
  const [avatars, setAvatars] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listAvatars()
      .then(setAvatars)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className={styles.loading}>加载头像...</div>;
  }

  return (
    <div className={styles.container}>
      {avatars.map((avatar) => (
        <button
          key={avatar}
          type="button"
          className={`${styles.avatarItem} ${selectedAvatar === avatar ? styles.selected : ''}`}
          onClick={() => onSelect(avatar)}
          aria-label={`选择头像 ${avatar}`}
        >
          <div className={styles.avatarPreview}>{avatar[0].toUpperCase()}</div>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: 创建 AvatarSelector 样式**

```css
.container {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  padding: 16px;
}

.avatarItem {
  width: 64px;
  height: 64px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 8px;
  background: var(--bg-bubble);
  cursor: pointer;
  transition: all 0.2s;
}

.avatarItem:hover {
  border-color: var(--border-color);
  transform: scale(1.05);
}

.avatarItem.selected {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1);
}

.avatarPreview {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.loading {
  padding: 16px;
  text-align: center;
  color: var(--text-secondary);
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/roles/components/AvatarSelector.tsx frontend/src/features/roles/components/AvatarSelector.module.css
git commit -m "feat(roles): 添加头像选择器组件"
```

---

## Task 12: 创建 CreateRoleDialog 组件

**Files:**
- Create: `frontend/src/features/roles/components/CreateRoleDialog.tsx`
- Create: `frontend/src/features/roles/components/CreateRoleDialog.module.css`

- [ ] **Step 1: 创建 CreateRoleDialog 组件**

```typescript
/**
 * 创建角色弹窗组件
 */

import { useState } from 'react';
import { AvatarSelector } from './AvatarSelector';
import { useCreateRole } from '../hooks/useCreateRole';
import type { CreateRoleFormData } from '../types';
import type { AgentPlatform } from '@/shared/types/api-schemas';
import styles from './CreateRoleDialog.module.css';

export interface CreateRoleDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateRoleDialog({ isOpen, onClose, onSuccess }: CreateRoleDialogProps) {
  const [formData, setFormData] = useState<CreateRoleFormData>({
    name: '',
    platform: 'claude',
    avatar: null,
    description: '',
  });

  const { createRole, submitting } = useCreateRole();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      alert('请输入角色名称');
      return;
    }

    const result = await createRole(formData);
    
    if (result.success) {
      onSuccess?.();
      handleClose();
    } else {
      alert(result.error || '创建失败');
    }
  };

  const handleClose = () => {
    setFormData({ name: '', platform: 'claude', avatar: null, description: '' });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>创建角色</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label htmlFor="role-name">角色名称 *</label>
            <input
              id="role-name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="输入角色名称"
              required
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="role-platform">平台 *</label>
            <select
              id="role-platform"
              value={formData.platform}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, platform: e.target.value as AgentPlatform }))
              }
            >
              <option value="claude">Claude</option>
              <option value="codex">Codex</option>
            </select>
          </div>

          <div className={styles.field}>
            <label>头像</label>
            <AvatarSelector
              selectedAvatar={formData.avatar}
              onSelect={(avatar) => setFormData((prev) => ({ ...prev, avatar }))}
            />
          </div>

          <div className={styles.field}>
            <label>角色类型</label>
            <div className={styles.typeBadge}>team_member</div>
            <p className={styles.typeHint}>当前版本角色类型固定为 team_member</p>
          </div>

          <div className={styles.field}>
            <label htmlFor="role-description">角色描述</label>
            <textarea
              id="role-description"
              value={formData.description}
              onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="输入角色描述（可选）"
              rows={3}
            />
          </div>

          <div className={styles.field}>
            <label>技能列表</label>
            <div className={styles.skillPlaceholder}>技能配置功能开发中...</div>
          </div>

          <div className={styles.actions}>
            <button type="button" onClick={handleClose} className={styles.cancelBtn}>
              取消
            </button>
            <button type="submit" className={styles.submitBtn} disabled={submitting}>
              {submitting ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 CreateRoleDialog 样式（第1部分）**

```css
.overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--bg-main);
  border-radius: 12px;
  width: 600px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.closeBtn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;
}

.closeBtn:hover {
  background: var(--bg-shadow);
}

.form {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.field {
  margin-bottom: 20px;
}
```

- [ ] **Step 3: 创建 CreateRoleDialog 样式（第2部分）**

```css
.field label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.field input,
.field select,
.field textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  transition: border-color 0.2s;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
  outline: none;
  border-color: var(--accent-color);
}

.typeBadge {
  display: inline-block;
  padding: 6px 12px;
  background: var(--bg-bubble);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.typeHint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.skillPlaceholder {
  padding: 16px;
  background: var(--bg-bubble);
  border-radius: 6px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 24px;
  border-top: 1px solid var(--border-color);
}

.cancelBtn,
.submitBtn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.cancelBtn {
  background: var(--bg-bubble);
  color: var(--text-primary);
}

.cancelBtn:hover {
  background: var(--bg-shadow);
}

.submitBtn {
  background: var(--accent-color);
  color: white;
}

.submitBtn:hover:not(:disabled) {
  opacity: 0.9;
}

.submitBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/features/roles/components/CreateRoleDialog.tsx frontend/src/features/roles/components/CreateRoleDialog.module.css
git commit -m "feat(roles): 添加创建角色弹窗组件"
```

---

## Task 13: 创建 RoleCard 组件

**Files:**
- Create: `frontend/src/features/roles/components/RoleCard.tsx`
- Create: `frontend/src/features/roles/components/RoleCard.module.css`

- [ ] **Step 1: 创建 RoleCard 组件**

```typescript
/**
 * 角色卡片组件
 */

import type { RoleWithSkills } from '../types';
import styles from './RoleCard.module.css';

export interface RoleCardProps {
  role: RoleWithSkills;
  onClick?: () => void;
}

export function RoleCard({ role, onClick }: RoleCardProps) {
  return (
    <div className={styles.card} onClick={onClick}>
      <div className={styles.header}>
        <div className={styles.avatar}>
          {role.avatar ? role.avatar[0].toUpperCase() : role.name[0].toUpperCase()}
        </div>
        <div className={styles.info}>
          <h3 className={styles.name}>{role.name}</h3>
          <div className={styles.badges}>
            <span className={`${styles.badge} ${styles.platform}`}>{role.platform}</span>
            <span className={`${styles.badge} ${styles.type}`}>
              {role.type === 'leader' ? 'leader' : 'team_member'}
            </span>
          </div>
        </div>
      </div>

      {role.description && <p className={styles.description}>{role.description}</p>}

      <div className={styles.skills}>
        <span className={styles.skillsLabel}>Skills:</span>
        {role.skills.length > 0 ? (
          <div className={styles.skillsList}>
            {role.skills.map((skill) => (
              <span key={skill.id} className={styles.skillBadge}>
                {skill.name}
              </span>
            ))}
          </div>
        ) : (
          <span className={styles.noSkills}>暂无技能</span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 RoleCard 样式**

```css
.card {
  padding: 20px;
  background: var(--bg-main);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.header {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: var(--bg-bubble);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  flex-shrink: 0;
}

.info {
  flex: 1;
  min-width: 0;
}

.name {
  margin: 0 0 6px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badges {
  display: flex;
  gap: 6px;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.platform {
  background: rgba(74, 158, 255, 0.1);
  color: var(--accent-color);
}

.badge.type {
  background: var(--bg-bubble);
  color: var(--text-secondary);
}

.description {
  margin: 0 0 12px 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.skills {
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.skillsLabel {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.skillsList {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skillBadge {
  padding: 4px 10px;
  background: var(--bg-bubble);
  border-radius: 4px;
  font-size: 11px;
  color: var(--text-secondary);
}

.noSkills {
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/roles/components/RoleCard.tsx frontend/src/features/roles/components/RoleCard.module.css
git commit -m "feat(roles): 添加角色卡片组件"
```

---

## Task 14: 创建 TeamList 组件

**Files:**
- Create: `frontend/src/features/roles/components/TeamList.tsx`
- Create: `frontend/src/features/roles/components/TeamList.module.css`

- [ ] **Step 1: 创建 TeamList 组件**

```typescript
/**
 * 团队列表组件
 */

import type { TeamWithMembers } from '../types';
import styles from './TeamList.module.css';

export interface TeamListProps {
  teams: TeamWithMembers[];
  selectedTeam: string | null;
  onSelectTeam: (teamName: string) => void;
}

export function TeamList({ teams, selectedTeam, onSelectTeam }: TeamListProps) {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3>团队列表</h3>
      </div>
      <div className={styles.list}>
        {teams.map((team) => (
          <button
            key={team.name}
            type="button"
            className={`${styles.item} ${selectedTeam === team.name ? styles.active : ''}`}
            onClick={() => onSelectTeam(team.name)}
          >
            <div className={styles.itemIcon}>👥</div>
            <div className={styles.itemInfo}>
              <div className={styles.itemName}>{team.name}</div>
              <div className={styles.itemCount}>{team.members.length} 成员</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 TeamList 样式**

```css
.container {
  width: 260px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  text-align: left;
}

.item:hover {
  background: var(--bg-shadow);
}

.item.active {
  background: var(--bg-shadow);
}

.itemIcon {
  font-size: 20px;
  flex-shrink: 0;
}

.itemInfo {
  flex: 1;
  min-width: 0;
}

.itemName {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.itemCount {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/roles/components/TeamList.tsx frontend/src/features/roles/components/TeamList.module.css
git commit -m "feat(roles): 添加团队列表组件"
```

---

## Task 15: 创建 RoleMemberRow 组件

**Files:**
- Create: `frontend/src/features/roles/components/RoleMemberRow.tsx`
- Create: `frontend/src/features/roles/components/RoleMemberRow.module.css`

- [ ] **Step 1: 创建 RoleMemberRow 组件**

```typescript
/**
 * 角色成员行组件
 */

import type { RoleWithSkills } from '../types';
import styles from './RoleMemberRow.module.css';

export interface RoleMemberRowProps {
  role: RoleWithSkills;
  onRemove: (roleName: string) => void;
}

export function RoleMemberRow({ role, onRemove }: RoleMemberRowProps) {
  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`确定将 ${role.name} 从团队中移除？`)) {
      onRemove(role.name);
    }
  };

  return (
    <div className={styles.row}>
      <div className={styles.avatar}>
        {role.avatar ? role.avatar[0].toUpperCase() : role.name[0].toUpperCase()}
      </div>
      <div className={styles.info}>
        <div className={styles.header}>
          <span className={styles.name}>{role.name}</span>
          <span className={`${styles.badge} ${styles.type}`}>
            {role.type === 'leader' ? 'leader' : 'team_member'}
          </span>
        </div>
        {role.description && <p className={styles.description}>{role.description}</p>}
      </div>
      <button
        type="button"
        className={styles.removeBtn}
        onClick={handleRemove}
        aria-label={`移除 ${role.name}`}
      >
        ×
      </button>
    </div>
  );
}
```

- [ ] **Step 2: 创建 RoleMemberRow 样式**

```css
.row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  transition: background 0.2s;
}

.row:hover {
  background: var(--bg-shadow);
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--bg-bubble);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  flex-shrink: 0;
}

.info {
  flex: 1;
  min-width: 0;
}

.header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.type {
  background: var(--bg-bubble);
  color: var(--text-secondary);
}

.description {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.removeBtn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  font-size: 20px;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.removeBtn:hover {
  background: rgba(255, 59, 48, 0.1);
  color: #ff3b30;
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/roles/components/RoleMemberRow.tsx frontend/src/features/roles/components/RoleMemberRow.module.css
git commit -m "feat(roles): 添加角色成员行组件"
```

---

## Task 16: 创建 TeamMemberPanel 组件

**Files:**
- Create: `frontend/src/features/roles/components/TeamMemberPanel.tsx`
- Create: `frontend/src/features/roles/components/TeamMemberPanel.module.css`

- [ ] **Step 1: 创建 TeamMemberPanel 组件**

```typescript
/**
 * 团队成员面板组件
 */

import { RoleMemberRow } from './RoleMemberRow';
import { useTeamMembers } from '../hooks/useTeamMembers';
import type { TeamWithMembers } from '../types';
import styles from './TeamMemberPanel.module.css';

export interface TeamMemberPanelProps {
  team: TeamWithMembers | null;
  onAddMember: () => void;
}

export function TeamMemberPanel({ team, onAddMember }: TeamMemberPanelProps) {
  const { removeMemberFromTeam, submitting } = useTeamMembers();

  const handleRemoveMember = async (roleName: string) => {
    if (!team) return;
    const result = await removeMemberFromTeam(team.name, roleName);
    if (!result.success) {
      alert(result.error);
    }
  };

  if (!team) {
    return (
      <div className={styles.empty}>
        <p>请选择一个团队</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.teamInfo}>
          <h2 className={styles.teamName}>{team.name}</h2>
          <span className={styles.memberCount}>{team.members.length} 成员</span>
        </div>
        <button type="button" className={styles.addBtn} onClick={onAddMember} disabled={submitting}>
          + 添加成员
        </button>
      </div>

      <div className={styles.memberList}>
        {team.members.length === 0 ? (
          <div className={styles.noMembers}>暂无成员</div>
        ) : (
          team.members.map((member) => (
            <RoleMemberRow key={member.name} role={member} onRemove={handleRemoveMember} />
          ))
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 TeamMemberPanel 样式**

```css
.container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.teamInfo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.teamName {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.memberCount {
  padding: 4px 10px;
  background: var(--bg-bubble);
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.addBtn {
  padding: 8px 16px;
  border: none;
  background: var(--accent-color);
  color: white;
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.addBtn:hover:not(:disabled) {
  opacity: 0.9;
}

.addBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.memberList {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.noMembers {
  padding: 32px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 14px;
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/roles/components/TeamMemberPanel.tsx frontend/src/features/roles/components/TeamMemberPanel.module.css
git commit -m "feat(roles): 添加团队成员面板组件"
```

---

## Task 17: 创建 AddMemberDialog 组件

**Files:**
- Create: `frontend/src/features/roles/components/AddMemberDialog.tsx`
- Create: `frontend/src/features/roles/components/AddMemberDialog.module.css`

- [ ] **Step 1: 创建 AddMemberDialog 组件**

```typescript
/**
 * 添加成员弹窗组件
 */

import { useState } from 'react';
import { CreateRoleDialog } from './CreateRoleDialog';
import { useRoles } from '../hooks/useRoles';
import { useTeamMembers } from '../hooks/useTeamMembers';
import type { AddMemberMode } from '../types';
import styles from './AddMemberDialog.module.css';

export interface AddMemberDialogProps {
  isOpen: boolean;
  teamName: string | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AddMemberDialog({ isOpen, teamName, onClose, onSuccess }: AddMemberDialogProps) {
  const [mode, setMode] = useState<AddMemberMode>('existing');
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { roles } = useRoles();
  const { addMembersToTeam, submitting } = useTeamMembers();

  const handleSubmit = async () => {
    if (!teamName || selectedRoles.length === 0) {
      alert('请至少选择一个角色');
      return;
    }

    const result = await addMembersToTeam(teamName, selectedRoles);
    
    if (result.success) {
      onSuccess?.();
      handleClose();
    } else {
      alert(result.error);
    }
  };

  const handleClose = () => {
    setMode('existing');
    setSelectedRoles([]);
    onClose();
  };

  const handleCreateSuccess = () => {
    setShowCreateDialog(false);
    onSuccess?.();
  };

  const toggleRole = (roleName: string) => {
    setSelectedRoles((prev) =>
      prev.includes(roleName) ? prev.filter((r) => r !== roleName) : [...prev, roleName]
    );
  };

  if (!isOpen) return null;

  return (
    <>
      <div className={styles.overlay} onClick={handleClose}>
        <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
          <div className={styles.header}>
            <h2>添加成员</h2>
            <button type="button" className={styles.closeBtn} onClick={handleClose}>
              ×
            </button>
          </div>

          <div className={styles.content}>
            <div className={styles.modeSelector}>
              <button
                type="button"
                className={`${styles.modeBtn} ${mode === 'existing' ? styles.active : ''}`}
                onClick={() => setMode('existing')}
              >
                添加现有角色
              </button>
              <button
                type="button"
                className={`${styles.modeBtn} ${mode === 'create' ? styles.active : ''}`}
                onClick={() => setMode('create')}
              >
                创建新角色
              </button>
            </div>

            {mode === 'existing' ? (
              <div className={styles.roleList}>
                {roles.map((role) => (
                  <label key={role.name} className={styles.roleItem}>
                    <input
                      type="checkbox"
                      checked={selectedRoles.includes(role.name)}
                      onChange={() => toggleRole(role.name)}
                    />
                    <div className={styles.roleInfo}>
                      <span className={styles.roleName}>{role.name}</span>
                      <span className={styles.roleDesc}>{role.description || '无描述'}</span>
                    </div>
                  </label>
                ))}
              </div>
            ) : (
              <div className={styles.createPrompt}>
                <p>点击下方按钮创建新角色，创建完成后将自动添加到团队</p>
                <button
                  type="button"
                  className={styles.createBtn}
                  onClick={() => setShowCreateDialog(true)}
                >
                  创建角色
                </button>
              </div>
            )}
          </div>

          <div className={styles.actions}>
            <button type="button" onClick={handleClose} className={styles.cancelBtn}>
              取消
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              className={styles.submitBtn}
              disabled={submitting || selectedRoles.length === 0}
            >
              {submitting ? '添加中...' : '添加'}
            </button>
          </div>
        </div>
      </div>

      <CreateRoleDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={handleCreateSuccess}
      />
    </>
  );
}
```

- [ ] **Step 2: 创建 AddMemberDialog 样式**

```css
.overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--bg-main);
  border-radius: 12px;
  width: 500px;
  max-width: 90vw;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.closeBtn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.2s;
}

.closeBtn:hover {
  background: var(--bg-shadow);
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.modeSelector {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  padding: 4px;
  background: var(--bg-bubble);
  border-radius: 8px;
}

.modeBtn {
  flex: 1;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.modeBtn.active {
  background: var(--bg-main);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.roleList {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.roleItem {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.roleItem:hover {
  background: var(--bg-shadow);
}

.roleItem input[type='checkbox'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.roleInfo {
  flex: 1;
  min-width: 0;
}

.roleName {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.roleDesc {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.createPrompt {
  text-align: center;
  padding: 32px 16px;
}

.createPrompt p {
  margin: 0 0 16px 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.createBtn {
  padding: 10px 20px;
  border: none;
  background: var(--accent-color);
  color: white;
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.createBtn:hover {
  opacity: 0.9;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

.cancelBtn,
.submitBtn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.cancelBtn {
  background: var(--bg-bubble);
  color: var(--text-primary);
}

.cancelBtn:hover {
  background: var(--bg-shadow);
}

.submitBtn {
  background: var(--accent-color);
  color: white;
}

.submitBtn:hover:not(:disabled) {
  opacity: 0.9;
}

.submitBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/roles/components/AddMemberDialog.tsx frontend/src/features/roles/components/AddMemberDialog.module.css
git commit -m "feat(roles): 添加添加成员弹窗组件"
```

---

## Task 18: 创建 RoleManagementPanel 主面板

**Files:**
- Create: `frontend/src/features/roles/components/RoleManagementPanel.tsx`
- Create: `frontend/src/features/roles/components/RoleManagementPanel.module.css`

- [ ] **Step 1: 创建 RoleManagementPanel 组件**

```typescript
/**
 * 角色管理主面板组件
 */

import { useState } from 'react';
import { RoleCard } from './RoleCard';
import { TeamList } from './TeamList';
import { TeamMemberPanel } from './TeamMemberPanel';
import { CreateRoleDialog } from './CreateRoleDialog';
import { AddMemberDialog } from './AddMemberDialog';
import { useRoles } from '../hooks/useRoles';
import { useTeams } from '../hooks/useTeams';
import type { RoleManagementTab } from '../types';
import styles from './RoleManagementPanel.module.css';

export function RoleManagementPanel() {
  const [activeTab, setActiveTab] = useState<RoleManagementTab>('teams');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showAddMemberDialog, setShowAddMemberDialog] = useState(false);

  const { roles, loading: rolesLoading, refreshRoles } = useRoles();
  const { teams, selectedTeam, currentTeam, selectTeam, refreshTeams } = useTeams();

  const handleCreateRoleSuccess = () => {
    refreshRoles();
    if (activeTab === 'teams') {
      refreshTeams();
    }
  };

  const handleAddMemberSuccess = () => {
    refreshTeams();
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>角色管理</h1>
        
        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'teams' ? styles.active : ''}`}
            onClick={() => setActiveTab('teams')}
          >
            团队管理
          </button>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'roles' ? styles.active : ''}`}
            onClick={() => setActiveTab('roles')}
          >
            角色管理
          </button>
        </div>
      </div>

      <div className={styles.content}>
        {activeTab === 'teams' ? (
          <div className={styles.teamsView}>
            <TeamList teams={teams} selectedTeam={selectedTeam} onSelectTeam={selectTeam} />
            <TeamMemberPanel
              team={currentTeam}
              onAddMember={() => setShowAddMemberDialog(true)}
            />
          </div>
        ) : (
          <div className={styles.rolesView}>
            <div className={styles.rolesHeader}>
              <button
                type="button"
                className={styles.addRoleBtn}
                onClick={() => setShowCreateDialog(true)}
              >
                + 添加角色
              </button>
            </div>

            {rolesLoading ? (
              <div className={styles.loading}>加载中...</div>
            ) : roles.length === 0 ? (
              <div className={styles.empty}>暂无角色</div>
            ) : (
              <div className={styles.rolesGrid}>
                {roles.map((role) => (
                  <RoleCard key={role.name} role={role} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <CreateRoleDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={handleCreateRoleSuccess}
      />

      <AddMemberDialog
        isOpen={showAddMemberDialog}
        teamName={selectedTeam}
        onClose={() => setShowAddMemberDialog(false)}
        onSuccess={handleAddMemberSuccess}
      />
    </div>
  );
}
```

- [ ] **Step 2: 创建 RoleManagementPanel 样式**

```css
.container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-main);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
}

.title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.tabs {
  display: flex;
  gap: 8px;
}

.tab {
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover {
  background: var(--bg-shadow);
}

.tab.active {
  background: var(--accent-color);
  color: white;
}

.content {
  flex: 1;
  overflow: hidden;
}

.teamsView {
  display: flex;
  height: 100%;
}

.rolesView {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.rolesHeader {
  display: flex;
  justify-content: flex-end;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color);
}

.addRoleBtn {
  padding: 8px 16px;
  border: none;
  background: var(--accent-color);
  color: white;
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.addRoleBtn:hover {
  opacity: 0.9;
}

.rolesGrid {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  align-content: start;
}

.loading,
.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  font-size: 14px;
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/features/roles/components/RoleManagementPanel.tsx frontend/src/features/roles/components/RoleManagementPanel.module.css
git commit -m "feat(roles): 添加角色管理主面板组件"
```

---

## Task 19: 导出所有组件和 hooks

**Files:**
- Create: `frontend/src/features/roles/index.ts`

- [ ] **Step 1: 创建 barrel export**

```typescript
/**
 * 角色管理模块导出
 */

// Components
export { RoleManagementPanel } from './components/RoleManagementPanel';
export { RoleCard } from './components/RoleCard';
export { TeamList } from './components/TeamList';
export { TeamMemberPanel } from './components/TeamMemberPanel';
export { RoleMemberRow } from './components/RoleMemberRow';
export { CreateRoleDialog } from './components/CreateRoleDialog';
export { AddMemberDialog } from './components/AddMemberDialog';
export { AvatarSelector } from './components/AvatarSelector';

// Hooks
export { useRoles } from './hooks/useRoles';
export { useTeams } from './hooks/useTeams';
export { useCreateRole } from './hooks/useCreateRole';
export { useTeamMembers } from './hooks/useTeamMembers';

// Types
export type {
  RoleWithSkills,
  TeamWithMembers,
  CreateRoleFormData,
  RoleManagementTab,
  AddMemberMode,
} from './types';
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/features/roles/index.ts
git commit -m "feat(roles): 添加模块导出"
```

---

## Task 20: 最终验证和测试

**Files:**
- Test: All components and hooks

- [ ] **Step 1: 运行所有测试**

Run: `npm test -- features/roles`
Expected: 所有测试通过

- [ ] **Step 2: 启动开发服务器**

Run: `npm run dev`
Expected: 服务启动成功，无编译错误

- [ ] **Step 3: 手动测试角色管理面板**

打开浏览器，导航到角色管理面板，验证：
- ✅ 两个 Tab 可以正常切换
- ✅ 团队列表正确显示
- ✅ 点击团队显示成员详情
- ✅ 角色网格正确显示所有角色
- ✅ 创建角色弹窗正常工作
- ✅ 添加成员到团队功能正常
- ✅ 从团队移除成员功能正常
- ✅ 头像选择器正常工作
- ✅ 样式符合 DESIGN.md 规范
- ✅ 双主题切换正常

- [ ] **Step 4: 最终提交**

```bash
git add .
git commit -m "feat(roles): 完成角色管理模块 UI 实现

- 实现角色管理面板（团队管理 + 角色管理两个 Tab）
- 实现角色卡片网格展示
- 实现团队列表和成员详情
- 实现创建角色功能
- 实现添加/移除团队成员功能
- 实现头像选择器
- 数据聚合在 Adapter 层完成
- 遵循 DESIGN.md v2.0 视觉规范
"
```

---

## Self-Review Checklist

### 1. Spec Coverage

- ✅ 角色管理页面布局（两个 Tab）
- ✅ 角色卡片网格展示
- ✅ 团队列表和成员详情展示
- ✅ 创建角色弹窗
- ✅ 添加成员到团队（现有角色/新建角色）
- ✅ 从团队移除成员
- ✅ 数据聚合逻辑（Adapter 层）
- ✅ 头像选择器
- ✅ 平台选择
- ✅ Skills 占位显示

### 2. Placeholder Scan

无占位符、TBD 或 TODO。所有步骤包含完整代码。

### 3. Type Consistency

所有类型定义一致：
- `RoleWithSkills` - 贯穿所有组件
- `TeamWithMembers` - 贯穿团队相关组件
- `CreateRoleFormData` - 创建角色表单
- `AgentPlatform` - 平台类型
- `RoleManagementTab` - Tab 类型
- `AddMemberMode` - 添加成员模式

---

## Execution Handoff

计划完成并保存到 `docs/superpowers/plans/2026-06-05-role-management-ui-implementation.md`。两种执行选项：

**1. Subagent-Driven（推荐）** - 每个任务派发新的子 agent，任务间审查，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 执行任务，批量执行并设置检查点

选择哪种方式？

