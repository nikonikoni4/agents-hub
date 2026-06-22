/**
 * 查找最近活跃的 Agents Hub 助手单聊
 *
 * 筛选逻辑：
 * 1. 按 agent_name === 'Agents-Hub-Assistant' 筛选
 * 2. 按 last_active_at 降序排序
 * 3. 返回第一个（最近活跃的）
 */

import type { SingleChatApiResponse } from '@/shared/types';

const ASSISTANT_AGENT_NAME = 'Agents-Hub-Assistant';

export function findLatestAssistantChat(
  singleChats: SingleChatApiResponse[]
): SingleChatApiResponse | null {
  const assistantChats = singleChats.filter((chat) => chat.agent_name === ASSISTANT_AGENT_NAME);

  if (assistantChats.length === 0) {
    return null;
  }

  // 按 last_active_at 降序排序
  assistantChats.sort(
    (a, b) => new Date(b.last_active_at).getTime() - new Date(a.last_active_at).getTime()
  );

  return assistantChats[0] ?? null;
}
