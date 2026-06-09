/**
 * Session 数据适配器
 *
 * 职责：
 * - 将后端扁平的 GroupChatInfo[] 聚合为按项目分组的数据结构
 * - 计算未读状态（基于 last_update_at 和 last_view_at）
 * - 提供时间格式化等辅助函数
 *
 * 架构约束：
 * - 纯函数，无副作用
 * - 不调用 API，不操作 storage
 * - 可独立测试
 */

import { GroupChatInfoApiResponse, SingleChatApiResponse } from '../types/api-schemas';

// ==================== 导出类型 ====================

/**
 * Session 项（前端数据模型）
 */
export interface SessionItem {
  /** 群聊 ID 或单聊 ID */
  id: string;
  /** 名称 */
  title: string;
  /** 预览文本 */
  preview: string;
  /** 最后更新时间 */
  lastUpdateAt: Date;
  /** 上次观看时间 */
  lastViewAt: Date | null;
  /** 是否未读 */
  isUnread: boolean;
  /** 成员数量 */
  memberCount: number;
  /** 项目路径 */
  projectPath: string;
  /** 成员头像列表（最多 4 个 SVG 字符串） */
  memberAvatars: (string | null)[];
  /** 会话类型 */
  type: 'group_chat' | 'single_chat';
  /** 单聊的 agent 名称（仅 single_chat 类型） */
  agentName?: string;
  /** 单聊的平台（仅 single_chat 类型） */
  platform?: string;
}

/**
 * 项目分组
 */
export interface ProjectGroup {
  /** 项目路径（完整） */
  projectPath: string;
  /** 项目名称（从路径提取） */
  projectName: string;
  /** 该项目下的 sessions（按 lastUpdateAt 降序） */
  sessions: SessionItem[];
}

// ==================== 核心聚合函数 ====================

/**
 * 按项目分组并聚合 sessions（群聊 + 单聊混合）
 *
 * @param chats - 后端返回的群聊列表
 * @param singleChats - 后端返回的单聊列表
 * @param lastViewRecords - 本地存储的 last_view_at 记录 { id: timestamp }
 * @returns 按项目分组的 sessions
 */
export function groupSessionsByProject(
  chats: GroupChatInfoApiResponse[],
  lastViewRecords: Record<string, string>,
  singleChats: SingleChatApiResponse[] = []
): ProjectGroup[] {
  // 1. 按 project_path 分组（群聊）
  const grouped = chats.reduce(
    (acc, chat) => {
      const projectName = extractProjectName(chat.project_path);

      if (!acc[projectName]) {
        acc[projectName] = {
          projectPath: chat.project_path,
          projectName,
          sessions: [],
        };
      }

      const lastViewTimestamp = lastViewRecords[chat.group_chat_id];
      const lastViewAt = lastViewTimestamp ? new Date(lastViewTimestamp) : null;

      const sessionItem: SessionItem = {
        id: chat.group_chat_id,
        title: chat.group_chat_name,
        preview: formatPreview(chat.last_speaker, chat.last_message),
        lastUpdateAt: chat.last_update_at
          ? new Date(chat.last_update_at)
          : new Date(chat.created_at),
        lastViewAt,
        isUnread: isUnread(
          chat.last_update_at || chat.created_at,
          lastViewRecords[chat.group_chat_id]
        ),
        memberCount: 0,
        projectPath: chat.project_path,
        memberAvatars: [],
        type: 'group_chat',
      };

      acc[projectName]!.sessions.push(sessionItem);
      return acc;
    },
    {} as Record<string, ProjectGroup>
  );

  // 2. 将单聊合并到对应项目分组
  for (const sc of singleChats) {
    const projectName = extractProjectName(sc.cwd);

    if (!grouped[projectName]) {
      grouped[projectName] = {
        projectPath: sc.cwd,
        projectName,
        sessions: [],
      };
    }

    const lastViewTimestamp = lastViewRecords[sc.single_chat_id];
    const lastViewAt = lastViewTimestamp ? new Date(lastViewTimestamp) : null;

    const sessionItem: SessionItem = {
      id: sc.single_chat_id,
      title: sc.single_chat_name,
      preview: `${sc.agent_name} · ${sc.platform}`,
      lastUpdateAt: new Date(sc.last_active_at),
      lastViewAt,
      isUnread: false,
      memberCount: 1,
      projectPath: sc.cwd,
      memberAvatars: [],
      type: 'single_chat',
      agentName: sc.agent_name,
      platform: sc.platform,
    };

    grouped[projectName]!.sessions.push(sessionItem);
  }

  // 3. 转为数组，组内按 lastUpdateAt 降序排序
  return Object.values(grouped).map((group) => ({
    ...group,
    sessions: group.sessions.sort((a, b) => b.lastUpdateAt.getTime() - a.lastUpdateAt.getTime()),
  }));
}

// ==================== 辅助函数 ====================

/**
 * 从项目路径提取最后一个文件夹名
 *
 * @example
 * extractProjectName("D:\\projects\\agents-hub") // => "agents-hub"
 * extractProjectName("/home/user/agents-hub") // => "agents-hub"
 */
export function extractProjectName(projectPath: string): string {
  // 处理 Windows 和 Unix 路径
  const parts = projectPath.split(/[/\\]/);
  const lastName = parts[parts.length - 1];
  return lastName || 'Unknown Project';
}

/**
 * 判断是否未读
 *
 * @param lastUpdateAt - 最后更新时间（ISO 8601）
 * @param lastViewAt - 最后查看时间（ISO 8601，可选）
 * @returns true 表示未读
 */
export function isUnread(lastUpdateAt: string, lastViewAt?: string): boolean {
  if (!lastViewAt) return true; // 从未查看过，算未读

  const updateTime = new Date(lastUpdateAt).getTime();
  const viewTime = new Date(lastViewAt).getTime();

  return updateTime > viewTime;
}

/**
 * 格式化预览文本
 *
 * @param speaker - 发言者（可能为 null）
 * @param message - 消息内容（可能为 null）
 * @returns 格式化后的预览文本
 */
export function formatPreview(speaker: string | null, message: string | null): string {
  if (!speaker || !message) return '暂无消息';

  // 截断过长的消息
  const truncatedMessage = message.length > 50 ? message.slice(0, 50) + '...' : message;
  return `${speaker}: ${truncatedMessage}`;
}

/**
 * 格式化相对时间
 *
 * @param date - 时间对象
 * @returns 相对时间字符串（如 "1小时前"、"昨天"）
 */
export function formatRelativeTime(date: Date): string {
  const now = Date.now();
  const past = date.getTime();
  const diffMs = now - past;

  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;

  const days = Math.floor(hours / 24);
  if (days === 1) return '昨天';
  if (days < 30) return `${days}天前`;

  // 超过 30 天，显示日期
  return date.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' });
}

/**
 * 将单聊列表按 cwd 分组为 ProjectGroup 格式
 */
export function groupSingleChatsByProject(
  singleChats: SingleChatApiResponse[]
): ProjectGroup[] {
  const grouped: Record<string, ProjectGroup> = {};
  for (const sc of singleChats) {
    const projectName = extractProjectName(sc.cwd);
    if (!grouped[projectName]) {
      grouped[projectName] = {
        projectPath: sc.cwd,
        projectName,
        sessions: [],
      };
    }
    grouped[projectName]!.sessions.push({
      id: sc.single_chat_id,
      title: sc.single_chat_name,
      preview: `${sc.agent_name} · ${sc.platform}`,
      lastUpdateAt: new Date(sc.last_active_at),
      lastViewAt: null,
      isUnread: false,
      memberCount: 1,
      projectPath: sc.cwd,
      memberAvatars: [],
      type: 'single_chat',
      agentName: sc.agent_name,
      platform: sc.platform,
    });
  }
  return Object.values(grouped).map((group) => ({
    ...group,
    sessions: group.sessions.sort(
      (a, b) => b.lastUpdateAt.getTime() - a.lastUpdateAt.getTime()
    ),
  }));
}
