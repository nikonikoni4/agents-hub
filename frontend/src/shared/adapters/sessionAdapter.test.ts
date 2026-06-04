/**
 * sessionAdapter 单元测试
 */

import { describe, it, expect } from 'vitest';
import {
  groupSessionsByProject,
  extractProjectName,
  isUnread,
  formatPreview,
  formatRelativeTime,
} from './sessionAdapter';
import { GroupChatInfoApiResponse } from '../types/api-schemas';

describe('sessionAdapter', () => {
  describe('extractProjectName', () => {
    it('应该从 Windows 路径提取项目名', () => {
      expect(extractProjectName('D:\\projects\\agents-hub')).toBe('agents-hub');
      expect(extractProjectName('C:\\Users\\test\\my-project')).toBe('my-project');
    });

    it('应该从 Unix 路径提取项目名', () => {
      expect(extractProjectName('/home/user/agents-hub')).toBe('agents-hub');
      expect(extractProjectName('/var/www/my-app')).toBe('my-app');
    });

    it('应该处理混合路径分隔符', () => {
      expect(extractProjectName('D:/projects/agents-hub')).toBe('agents-hub');
    });

    it('应该处理空路径', () => {
      expect(extractProjectName('')).toBe('Unknown Project');
    });
  });

  describe('isUnread', () => {
    it('从未查看过应返回 true', () => {
      expect(isUnread('2026-06-05T10:00:00Z', undefined)).toBe(true);
      expect(isUnread('2026-06-05T10:00:00Z')).toBe(true);
    });

    it('last_update_at > last_view_at 应返回 true', () => {
      expect(isUnread('2026-06-05T10:00:00Z', '2026-06-05T09:00:00Z')).toBe(true);
    });

    it('last_update_at <= last_view_at 应返回 false', () => {
      expect(isUnread('2026-06-05T10:00:00Z', '2026-06-05T10:00:00Z')).toBe(false);
      expect(isUnread('2026-06-05T10:00:00Z', '2026-06-05T11:00:00Z')).toBe(false);
    });
  });

  describe('formatPreview', () => {
    it('应该格式化正常的预览文本', () => {
      expect(formatPreview('Manager', 'Hello world')).toBe('Manager: Hello world');
      expect(formatPreview('User', '测试消息')).toBe('User: 测试消息');
    });

    it('应该截断过长的消息', () => {
      const longMessage = 'a'.repeat(60);
      const result = formatPreview('Manager', longMessage);
      expect(result).toBe(`Manager: ${'a'.repeat(50)}...`);
      expect(result.length).toBeLessThan(longMessage.length + 10);
    });

    it('应该处理 null 值', () => {
      expect(formatPreview(null, 'message')).toBe('暂无消息');
      expect(formatPreview('speaker', null)).toBe('暂无消息');
      expect(formatPreview(null, null)).toBe('暂无消息');
    });
  });

  describe('formatRelativeTime', () => {
    it('应该显示"刚刚"（小于 1 分钟）', () => {
      const now = new Date();
      expect(formatRelativeTime(now)).toBe('刚刚');
      expect(formatRelativeTime(new Date(now.getTime() - 30000))).toBe('刚刚');
    });

    it('应该显示分钟数（1-59 分钟）', () => {
      const now = new Date();
      expect(formatRelativeTime(new Date(now.getTime() - 60000))).toBe('1分钟前');
      expect(formatRelativeTime(new Date(now.getTime() - 300000))).toBe('5分钟前');
    });

    it('应该显示小时数（1-23 小时）', () => {
      const now = new Date();
      expect(formatRelativeTime(new Date(now.getTime() - 3600000))).toBe('1小时前');
      expect(formatRelativeTime(new Date(now.getTime() - 7200000))).toBe('2小时前');
    });

    it('应该显示"昨天"（24 小时内）', () => {
      const now = new Date();
      expect(formatRelativeTime(new Date(now.getTime() - 86400000))).toBe('昨天');
    });

    it('应该显示天数（2-29 天）', () => {
      const now = new Date();
      expect(formatRelativeTime(new Date(now.getTime() - 172800000))).toBe('2天前');
      expect(formatRelativeTime(new Date(now.getTime() - 604800000))).toBe('7天前');
    });
  });

  describe('groupSessionsByProject', () => {
    const mockChats: GroupChatInfoApiResponse[] = [
      {
        group_chat_id: 'gc1',
        group_chat_name: '测试会话1',
        project_path: 'D:\\projects\\agents-hub',
        created_at: '2026-06-05T09:00:00Z',
        group_type: 'sequence_execute',
        is_active: true,
        last_speaker: 'Manager',
        last_message: '测试消息1',
        last_update_at: '2026-06-05T10:00:00Z',
      },
      {
        group_chat_id: 'gc2',
        group_chat_name: '测试会话2',
        project_path: 'D:\\projects\\agents-hub',
        created_at: '2026-06-05T08:00:00Z',
        group_type: 'manager_orchestrate',
        is_active: true,
        last_speaker: 'User',
        last_message: '测试消息2',
        last_update_at: '2026-06-05T11:00:00Z',
      },
      {
        group_chat_id: 'gc3',
        group_chat_name: '测试会话3',
        project_path: '/home/user/another-project',
        created_at: '2026-06-05T07:00:00Z',
        group_type: 'sequence_execute',
        is_active: false,
        last_speaker: 'Manager',
        last_message: '测试消息3',
        last_update_at: '2026-06-05T12:00:00Z',
      },
    ];

    it('应该按项目路径分组', () => {
      const result = groupSessionsByProject(mockChats, {});
      expect(result).toHaveLength(2);
      expect(result[0]?.projectName).toBe('agents-hub');
      expect(result[0]?.sessions).toHaveLength(2);
      expect(result[1]?.projectName).toBe('another-project');
      expect(result[1]?.sessions).toHaveLength(1);
    });

    it('应该按 lastUpdateAt 降序排序', () => {
      const result = groupSessionsByProject(mockChats, {});
      const agentsHubGroup = result.find((g) => g.projectName === 'agents-hub');

      expect(agentsHubGroup?.sessions[0]?.id).toBe('gc2'); // 11:00
      expect(agentsHubGroup?.sessions[1]?.id).toBe('gc1'); // 10:00
    });

    it('应该正确计算未读状态', () => {
      const lastViewRecords = {
        gc1: '2026-06-05T09:30:00Z', // 早于 last_update_at，应该未读
        gc2: '2026-06-05T12:00:00Z', // 晚于 last_update_at，应该已读
        // gc3 没有记录，应该未读
      };

      const result = groupSessionsByProject(mockChats, lastViewRecords);
      const allSessions = result.flatMap((g) => g.sessions);

      const gc1 = allSessions.find((s) => s.id === 'gc1');
      const gc2 = allSessions.find((s) => s.id === 'gc2');
      const gc3 = allSessions.find((s) => s.id === 'gc3');

      expect(gc1?.isUnread).toBe(true);
      expect(gc2?.isUnread).toBe(false);
      expect(gc3?.isUnread).toBe(true);
    });

    it('应该正确格式化预览文本', () => {
      const result = groupSessionsByProject(mockChats, {});
      const allSessions = result.flatMap((g) => g.sessions);

      const gc1 = allSessions.find((s) => s.id === 'gc1');
      const gc2 = allSessions.find((s) => s.id === 'gc2');

      expect(gc1?.preview).toBe('Manager: 测试消息1');
      expect(gc2?.preview).toBe('User: 测试消息2');
    });

    it('应该处理空列表', () => {
      const result = groupSessionsByProject([], {});
      expect(result).toHaveLength(0);
    });
  });
});
