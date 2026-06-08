/**
 * 导航标记解析工具
 *
 * 解析系统助手回复中的特殊标记，用于渲染可点击的导航卡片。
 * 标记格式：<!-- navigation:type -->\n{json}\n[text](#)
 */

export type NavigationType = 'group_chat' | 'create_single_chat';

export interface GroupChatNavigationData {
  group_chat_id: string;
  name: string;
  members: string[];
  project_path: string;
}

export interface CreateSingleChatNavigationData {
  agent_name: string;
  platform: string;
  description: string;
}

export interface NavigationMark {
  type: NavigationType;
  data: GroupChatNavigationData | CreateSingleChatNavigationData;
  linkText: string;
}

/**
 * 从消息内容中解析导航标记
 *
 * @param content 消息文本内容
 * @returns 解析后的导航标记，无标记返回 null
 */
export function parseNavigationMark(content: string): NavigationMark | null {
  const regex = /<!-- navigation:(\w+) -->\s*\n(\{.*?\})\s*\n\[([^\]]+)\]\(#\)/s;
  const match = content.match(regex);
  if (!match) return null;

  const type = match[1];
  const jsonStr = match[2];
  const linkText = match[3];

  if (!type || !jsonStr || !linkText) return null;
  if (type !== 'group_chat' && type !== 'create_single_chat') {
    return null;
  }

  try {
    const data = JSON.parse(jsonStr);
    return { type, data, linkText };
  } catch {
    return null;
  }
}
