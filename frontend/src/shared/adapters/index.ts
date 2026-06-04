/**
 * Adapters 统一导出
 *
 * 提供 API 响应类型到 Domain 类型的转换和数据聚合功能
 */

// 角色相关 Adapter
export * from './roleAdapter';

// 群聊相关 Adapter
export * from './chatAdapter';

// Skill 相关 Adapter
export * from './skillAdapter';

// 消息相关 Adapter
export * from './messageAdapter';

// 团队相关 Adapter
export * from './teamAdapter';

// Session 相关 Adapter
export * from './sessionAdapter';

// 转发导出 API Schemas（作为统一入口）
export type {
  // 枚举类型
  AgentPlatform,
  RoleType,
  GroupChatType,
  SessionType,
  MessageType,
  CallStatus,
  TaskStatus,
  // 消息相关
  MessageApiItem,
  AgentMessageApiItem,
  // 角色相关
  RoleApiResponse,
  SkillApiItem,
  RoleSkillApiItem,
  // 群聊相关
  GroupChatApiResponse,
  GroupChatMemberApiItem,
  // Session 相关
  GroupChatInfoApiResponse,
  LastViewRecord,
  // 配置相关
  SystemConfigApiResponse,
} from '@/shared/types/api-schemas';
