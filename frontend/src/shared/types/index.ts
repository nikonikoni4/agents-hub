/**
 * 统一导出所有类型定义
 */

// API Schemas 类型（后端契约）
export type {
  AgentPlatform,
  RoleType,
  GroupChatType,
  SessionType,
  MessageType,
  CallStatus,
  TaskStatus,
  MessageApiItem,
  AgentMessageApiItem,
  RoleApiResponse,
  SkillApiItem,
  RoleSkillApiItem,
  GroupChatApiResponse,
  GroupChatSummaryApiItem,
  GroupChatMemberApiItem,
  AgentContextStateApiResponse,
  AgentSessionInfoApiResponse,
  SystemConfigApiResponse,
} from './api-schemas';

// API 请求类型
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
} from './api-requests';

// WebSocket 相关类型
export type {
  RefreshSignal,
  WebSocketEventType,
  WebSocketEventCallback,
  WebSocketMessage,
} from './websocket';

export { WebSocketState } from './websocket';
