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

import { GroupChatInfoApiResponse } from '../types/api-schemas';

// ==================== 导出类型 ====================

/**
 * Session 项（前端数据模型）
 */
export interface SessionItem {
  /** 群聊 ID */
  id: string;
  /** 群聊名称 */
  title: string;
  /** 预览文本（last_speaker: last_message） */
  preview: string;
  /** 最后更新时间 */
  lastUpdateAt: Date;
  /** 是否未读 */
  isUnread: boolean;
  /** 成员数量 */
  memberCount: number;
  /** 项目路径 */
  projectPath: string;
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
 * 按项目分组并聚合 sessions
 *
 * @param chats - 后端返回的群聊列表
 * @param lastViewRecords - 本地存储的 last_view_at 记录 { group_chat_id: timestamp }
 * @returns 按项目分组的 sessions
 */
export function groupSessionsByProject(
  chats: GroupChatInfoApiResponse[],
  lastViewRecords: Record<string, string>
): ProjectGroup[] {
  // 1. 按 project_path 分组
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

      // 2. 转换为 SessionItem
      const sessionItem: SessionItem = {
        id: chat.group_chat_id,
        title: chat.group_chat_name,
        preview: formatPreview(chat.last_speaker, chat.last_message),
        lastUpdateAt: chat.last_update_at
          ? new Date(chat.last_update_at)
          : new Date(chat.created_at),
        isUnread: isUnread(
          chat.last_update_at || chat.created_at,
          lastViewRecords[chat.group_chat_id]
        ),
        memberCount: 0, // 后端暂未提供，先设为 0
        projectPath: chat.project_path,
      };

      acc[projectName]!.sessions.push(sessionItem);
      return acc;
    },
    {} as Record<string, ProjectGroup>
  );

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
