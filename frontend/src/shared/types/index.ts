/**
 * 统一导出所有类型定义
 */

// 核心数据模型
export type {
  AgentPlatform,
  RoleType,
  GroupChatType,
  SessionType,
  MessageType,
  CallStatus,
  TaskStatus,
  Message,
  AgentMessage,
  Role,
  Agent,
  Skill,
  GroupChat,
  GroupChatSummary,
  GroupChatMember,
  AgentContextState,
  AgentSessionInfo,
  SystemConfig,
} from './models';

// API 请求/响应类型
export type {
  CreateGroupChatRequest,
  SendMessageRequest,
  UpdateDockerModeRequest,
  CreateRoleRequest,
  UpdateRoleRequest,
  AddSkillRequest,
  CreateSkillRequest,
  UpdateConfigRequest,
  SuccessResponse,
  ErrorResponse,
} from './api';

// WebSocket 相关类型
export type {
  RefreshSignal,
  WebSocketEventType,
  WebSocketEventCallback,
  WebSocketMessage,
} from './websocket';

export { WebSocketState } from './websocket';
