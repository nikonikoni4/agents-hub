/**
 * 单聊消息适配器
 *
 * 职责：将 SingleChatMessageApiItem[] 转换为 MessageApiItem[] 格式
 *
 * 设计说明：
 * - SingleChatMessageApiItem 是单聊 API 响应格式（包含 role、model 等）
 * - MessageApiItem 是统一的消息格式（包含 speaker、platform 等）
 * - 适配器将单聊消息标准化为统一格式，便于复用消息渲染组件
 */

import type { SingleChatMessageApiItem, MessageApiItem } from '@/shared/types';

/**
 * 将单聊消息转换为统一的消息格式
 *
 * @param singleChatMessages - 单聊消息列表
 * @returns 统一消息格式列表
 *
 * @example
 * const messages = await getSingleChatMessages(singleChatId);
 * const adaptedMessages = adaptSingleChatMessages(messages);
 * // 现在可以用同一个组件渲染消息
 */
export function adaptSingleChatMessages(
  singleChatMessages: SingleChatMessageApiItem[]
): MessageApiItem[] {
  return singleChatMessages.map((message) => ({
    id: parseInt(message.id, 10),
    speaker: message.role === 'user' ? 'user' : message.role,
    content: message.content,
    timestamp: message.timestamp,
    platform: message.model || 'claude',
    cwd: undefined,
    modified_files: undefined,
    git_diff_range: undefined,
    permission_request: undefined,
  }));
}

/**
 * 批量转换单聊消息列表
 *
 * @param singleChatMessages - 单聊消息列表
 * @returns 统一消息格式列表
 *
 * @note 此函数为 adaptSingleChatMessages 的别名，保持命名一致性
 */
export function adaptSingleChatMessageList(
  singleChatMessages: SingleChatMessageApiItem[]
): MessageApiItem[] {
  return adaptSingleChatMessages(singleChatMessages);
}
