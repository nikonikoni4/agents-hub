/**
 * 消息相关 Adapter
 *
 * 提供 Message API 响应到 Domain 类型的转换和聚合功能
 */

import type { MessageApiItem, AgentMessageApiItem } from '@/shared/types/api-schemas';

// TODO: 需要时在 types/domain.ts 中定义 Domain 类型
// import type { ChatMessage, MessageSender } from '@/shared/types/domain';

// ==================== 基础转换函数 ====================

/**
 * 将 API 消息响应转换为前端业务模型
 *
 * @param apiMessage - API 响应的消息数据
 * @returns 前端业务模型
 *
 * @example
 * const apiMessages = await getMessages('chat-001');
 * const messages = apiMessages.map(adaptMessage);
 */
export function adaptMessage(apiMessage: MessageApiItem) {
  // TODO: 实现转换逻辑
  // 示例：
  // return {
  //   id: `${apiMessage.timestamp}-${apiMessage.speaker}`,
  //   sender: parseSender(apiMessage.speaker, apiMessage.platform),
  //   content: apiMessage.content,
  //   timestamp: new Date(apiMessage.timestamp),
  //   platform: apiMessage.platform,
  // };
  return apiMessage;
}

/**
 * 批量转换消息列表
 *
 * @param apiMessages - API 响应的消息列表
 * @returns 前端业务模型列表
 */
export function adaptMessageList(apiMessages: MessageApiItem[]) {
  return apiMessages.map(adaptMessage);
}

/**
 * 将 API Agent 消息响应转换为前端业务模型
 *
 * @param apiAgentMessage - API 响应的 Agent 消息数据
 * @returns 前端业务模型
 */
export function adaptAgentMessage(apiAgentMessage: AgentMessageApiItem) {
  // TODO: 实现转换逻辑
  return apiAgentMessage;
}

/**
 * 批量转换 Agent 消息列表
 *
 * @param apiAgentMessages - API 响应的 Agent 消息列表
 * @returns 前端业务模型列表
 */
export function adaptAgentMessageList(apiAgentMessages: AgentMessageApiItem[]) {
  return apiAgentMessages.map(adaptAgentMessage);
}

// ==================== 辅助函数 ====================

/**
 * 解析发送者信息
 *
 * @param speaker - 发送者名称
 * @param platform - 平台信息
 * @returns 解析后的发送者信息
 *
 * @example
 * const sender = parseSender('user', 'user');
 * console.log(sender); // { type: 'user', name: 'You' }
 *
 * const agentSender = parseSender('Agent1', 'claude');
 * console.log(agentSender); // { type: 'agent', name: 'Agent1' }
 */
export function parseSender(speaker: string, platform: string) {
  // TODO: 实现解析逻辑
  // 示例：
  // if (speaker === 'user') {
  //   return { type: 'user', name: 'You' };
  // }
  // return {
  //   type: 'agent',
  //   name: speaker,
  //   // avatarUrl 可以从其他地方获取
  // };
  return { speaker, platform };
}

// ==================== 聚合函数 ====================

/**
 * 聚合：获取消息及其发送者详情
 *
 * @param chatId - 群聊 ID
 * @returns 消息及其发送者详情的聚合数据
 *
 * @example
 * const messagesWithSenders = await aggregateMessagesWithSenders('chat-001');
 * console.log(messagesWithSenders);
 */
export async function aggregateMessagesWithSenders(_chatId: string) {
  // TODO: 实现聚合逻辑
  // 示例：
  // const [messagesData, membersData] = await Promise.all([
  //   getMessages(chatId),
  //   getMembers(chatId),
  // ]);
  //
  // // 将成员信息映射到消息中
  // return messagesData.map(msg => {
  //   const member = membersData.find(m => m.name === msg.speaker);
  //   return {
  //     ...adaptMessage(msg),
  //     senderDetail: member ? adaptGroupChatMember(member) : null,
  //   };
  // });

  throw new Error('aggregateMessagesWithSenders not implemented');
}
