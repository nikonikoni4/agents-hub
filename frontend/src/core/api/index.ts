/**
 * API 模块统一导出
 */

// API Client
export { default as apiClient, ApiError, USE_MOCK, mockableRequest } from './client';

// SSE 流式客户端
export { streamSSE, type SSEEvent, type SSEEventCallback } from './sseClient';

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
  getToolCatalog,
} from './roleApi';

// Skill 管理 API
export { listSkills, getSkill, deleteSkill, addSkill } from './skillApi';

// 团队管理 API
export { listTeams, getTeam, createTeam, updateTeam, deleteTeam } from './teamApi';

// 单聊 API
export { listSingleChats, getSingleChat, getSingleChatMessages } from './singleChatApi';
