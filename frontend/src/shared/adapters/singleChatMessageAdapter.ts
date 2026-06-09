/**
 * 单聊消息适配器
 *
 * 职责：将 SingleChatMessageApiItem[] 转换为 MessageApiItem[] 格式
 */

import type { SingleChatMessageApiItem, MessageApiItem } from '@/shared/types';

/**
 * 将单聊消息转换为统一的消息格式
 */
export function adaptSingleChatMessages(
  singleChatMessages: SingleChatMessageApiItem[]
): MessageApiItem[] {
  return singleChatMessages.map((m) => ({
    id: parseInt(m.id, 10), // 转换字符串 id 为数字
    speaker: m.role === 'user' ? 'user' : m.role,
    content: m.content,
    timestamp: m.timestamp,
    platform: m.model || 'claude', // 使用 model 字段作为 platform
    modified_files: [],
    permission_request: undefined,
    tool_calls: m.tool_calls,
  }));
}
