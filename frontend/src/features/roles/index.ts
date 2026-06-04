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
