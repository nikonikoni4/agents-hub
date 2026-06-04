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
  getMessages,
  getMembers,
  sendMessage,
  updateMemberDockerMode,
  deleteGroupChat,
} from './groupChatApi';

// 角色管理 API
export {
  createRole,
  getRoleInfo,
  listRoles,
  updateRole,
  deleteRole,
  getRoleSkills,
  addSkillToRole,
  removeSkillFromRole,
  listAvatars,
} from './roleApi';

// Skill 管理 API
export { listSkills, getSkill, deleteSkill, addSkill } from './skillApi';
