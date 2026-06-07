/**
 * API 模块统一导出
 */

// API Client
export { default as apiClient, ApiError, USE_MOCK, mockableRequest } from './client';

// 群聊 API
export {
  createGroupChat,
  getGroupChatInfo,
  listGroupChats,
  listGroupChatInfos,
  getMessages,
  getMembers,
  sendMessage,
  updateMemberDockerMode,
  deleteGroupChat,
  getAgentCalls,
  getActiveTasks,
} from './groupChatApi';

// 角色管理 API
export {
  createRole,
  getRoleInfo,
  listRoles,
  updateRole,
  deleteRole,
  addSkillToRole,
  removeSkillFromRole,
  listAvatars,
} from './roleApi';

// Skill 管理 API
export { listSkills, getSkill, deleteSkill, addSkill } from './skillApi';

// 团队管理 API
export { listTeams, getTeam, createTeam, updateTeam, deleteTeam } from './teamApi';
