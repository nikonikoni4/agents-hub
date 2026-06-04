/**
 * Domain 类型定义
 *
 * 本文件包含前端业务领域模型的 TypeScript 类型定义。
 *
 * 命名规范：
 * - 使用前端业务语义的名称（如 TeamMember 而非 Role）
 * - 使用 camelCase 字段名
 * - 使用前端友好的数据类型（如 Date 而非 string）
 *
 * 创建时机：
 * - 当组件需要不同于 API 的数据结构时
 * - 当需要聚合多个 API 响应时
 * - 当需要派生/计算属性时
 *
 * 注意：
 * - Domain 类型按需创建，不要提前定义用不到的类型
 * - 每个 Domain 类型应该在对应的 Adapter 中有转换函数
 */

// ==================== 示例类型定义 ====================

/**
 * 示例：团队成员（前端业务模型）
 *
 * 对应 API 类型：RoleApiResponse
 * 转换函数：adaptRole() in roleAdapter.ts
 */
// export interface TeamMember {
//   id: string;                    // API 的 name 字段
//   displayName: string;            // API 的 name 字段
//   avatarUrl: string | null;       // API 的 avatar 字段
//   skills: string[];               // API 的 abilities 字段
//   isLeader: boolean;              // 从 type 字段派生
//   platform: AgentPlatform;
//   scope: string[] | null;
//   description: string | null;
// }

/**
 * 示例：会话（前端业务模型）
 *
 * 对应 API 类型：GroupChatApiResponse
 * 转换函数：adaptGroupChat() in chatAdapter.ts
 */
// export interface Conversation {
//   id: string;                     // API 的 group_chat_id
//   title: string;                  // API 的 group_chat_name
//   projectPath: string;
//   createdAt: Date;                // API 的 created_at (转换为 Date)
//   isActive: boolean;
//   type: ConversationType;         // API 的 group_type (转换为枚举)
// }

/**
 * 示例：聊天消息（前端业务模型）
 *
 * 对应 API 类型：MessageApiItem
 * 转换函数：adaptMessage() in messageAdapter.ts
 */
// export interface ChatMessage {
//   id: string;                     // 前端生成（timestamp + speaker）
//   sender: MessageSender;          // 解析后的发送者信息
//   content: string;
//   timestamp: Date;                // API 的 timestamp (转换为 Date)
//   platform: string;
// }

/**
 * 示例：消息发送者信息（前端派生）
 */
// export interface MessageSender {
//   type: 'user' | 'agent';
//   name: string;
//   avatarUrl?: string;
// }

// ==================== 枚举类型 ====================

/**
 * 示例：会话类型（前端枚举）
 *
 * 对应 API 类型：GroupChatType
 */
// export enum ConversationType {
//   Sequential = 'sequential',      // API 的 sequence_execute
//   Managed = 'managed',            // API 的 manager_orchestrate
// }

/**
 * 示例：Agent 平台（前端枚举）
 *
 * 对应 API 类型：AgentPlatform
 */
// export enum AgentPlatform {
//   Claude = 'claude',
//   Codex = 'codex',
// }

// ==================== 注意事项 ====================

/**
 * 1. 按需创建
 *    - 不要提前定义所有 Domain 类型
 *    - 只在实际需要时（页面设计时）才创建
 *
 * 2. 命名原则
 *    - 使用前端业务语义（TeamMember 而非 Role）
 *    - 避免与 API 类型名称冲突
 *
 * 3. 类型关系
 *    - 每个 Domain 类型应对应一个 API 类型
 *    - 在 JSDoc 中标注对应的 API 类型和转换函数
 *
 * 4. 数据类型选择
 *    - 日期使用 Date 对象而非 string
 *    - 枚举使用 enum 或 union type
 *    - ID 使用 string 而非 number
 */
