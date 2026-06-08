/**
 * navigationParser 测试
 *
 * 契约驱动测试：验证 parseNavigationMark 函数承诺的行为
 */

import { describe, it, expect } from 'vitest';
import { parseNavigationMark } from './navigationParser';

describe('parseNavigationMark', () => {
  // =========================================================================
  // 正常流程
  // =========================================================================

  describe('解析群聊导航标记', () => {
    it('应正确解析完整的群聊导航标记', () => {
      /**
       * 契约：当 content 包含合法的群聊导航标记时，
       * 返回 { type: 'group_chat', data: {...}, linkText: '...' }
       *
       * 验证方式：
       * 1. 准备包含完整标记的 content
       * 2. 调用 parseNavigationMark
       * 3. 验证返回的 type、data、linkText 正确
       *
       * 如果失败，说明：正则匹配或 JSON 解析逻辑有误
       */
      const content = `这是一些前置文本

<!-- navigation:group_chat -->
{"group_chat_id":"abc-123","name":"测试群聊","members":["manager","developer"],"project_path":"/path/to/project"}

[点击进入群聊 →](#)

这是后续文本`;

      const result = parseNavigationMark(content);

      expect(result).not.toBeNull();
      expect(result!.type).toBe('group_chat');
      expect(result!.data).toEqual({
        group_chat_id: 'abc-123',
        name: '测试群聊',
        members: ['manager', 'developer'],
        project_path: '/path/to/project',
      });
      expect(result!.linkText).toBe('点击进入群聊 →');
    });

    it('应正确解析只有必要字段的群聊标记', () => /**
     * 契约：即使 data 中包含额外字段，也能正确解析
     */ {
      const content = `<!-- navigation:group_chat -->
{"group_chat_id":"id-1","name":"群聊","members":[],"project_path":"/p"}

[进入](#)`;

      const result = parseNavigationMark(content);

      expect(result).not.toBeNull();
      expect(result!.type).toBe('group_chat');
      expect((result!.data as any).members).toEqual([]);
    });
  });

  describe('解析单聊创建导航标记', () => {
    it('应正确解析完整的单聊创建导航标记', () => {
      /**
       * 契约：当 content 包含合法的单聊创建导航标记时，
       * 返回 { type: 'create_single_chat', data: {...}, linkText: '...' }
       *
       * 如果失败，说明：类型识别或数据解析有误
       */
      const content = `推荐一个开发助手给你

<!-- navigation:create_single_chat -->
{"agent_name":"developer","platform":"claude","description":"专业的开发助手"}

[点击开始对话 →](#)`;

      const result = parseNavigationMark(content);

      expect(result).not.toBeNull();
      expect(result!.type).toBe('create_single_chat');
      expect(result!.data).toEqual({
        agent_name: 'developer',
        platform: 'claude',
        description: '专业的开发助手',
      });
      expect(result!.linkText).toBe('点击开始对话 →');
    });
  });

  // =========================================================================
  // 异常情况
  // =========================================================================

  describe('无标记时返回 null', () => {
    it('普通文本应返回 null', () => {
      /**
       * 契约：当 content 不包含导航标记时，返回 null
       *
       * 如果失败，说明：正则过于宽松，误匹配了普通文本
       */
      const content = '这是一条普通消息，没有导航标记';

      const result = parseNavigationMark(content);

      expect(result).toBeNull();
    });

    it('空字符串应返回 null', () => /**
     * 契约：空输入返回 null，不抛异常
     */ {
      expect(parseNavigationMark('')).toBeNull();
    });

    it('只有部分标记应返回 null', () => /**
     * 契约：标记不完整时返回 null
     */ {
      const content = '<!-- navigation:group_chat -->\n{"group_chat_id":"id"}';

      expect(parseNavigationMark(content)).toBeNull();
    });
  });

  describe('无效类型返回 null', () => {
    it('不支持的 navigation 类型应返回 null', () => {
      /**
       * 契约：当 type 不是 'group_chat' 或 'create_single_chat' 时，返回 null
       *
       * 如果失败，说明：类型校验逻辑缺失
       */
      const content = `<!-- navigation:unknown_type -->
{"data":"value"}

[点击](#)`;

      const result = parseNavigationMark(content);

      expect(result).toBeNull();
    });
  });

  describe('JSON 解析失败返回 null', () => {
    it('无效 JSON 应返回 null', () => {
      /**
       * 契约：当 JSON 格式错误时，返回 null 而不是抛异常
       *
       * 如果失败，说明：try-catch 块缺失或 JSON.parse 异常未捕获
       */
      const content = `<!-- navigation:group_chat -->
{invalid json}

[点击](#)`;

      const result = parseNavigationMark(content);

      expect(result).toBeNull();
    });

    it('JSON 缺少必要字段时仍返回数据（不做字段校验）', () => /**
     * 契约：parseNavigationMark 只负责解析格式，不校验字段完整性
     * 字段校验由使用方负责
     */ {
      const content = `<!-- navigation:group_chat -->
{"group_chat_id":"id"}

[点击](#)`;

      const result = parseNavigationMark(content);

      // 解析成功，但 data 中缺少 name、members、project_path
      expect(result).not.toBeNull();
      expect(result!.type).toBe('group_chat');
    });
  });

  // =========================================================================
  // 边界情况
  // =========================================================================

  describe('边界情况', () => {
    it('标记前后有大量文本也能正确解析', () => {
      /**
       * 契约：标记可以出现在 content 的任意位置
       *
       * 如果失败，说明：正则没有使用 /s 标志或多行匹配
       */
      const prefix = 'A'.repeat(1000);
      const suffix = 'B'.repeat(1000);
      const content = `${prefix}

<!-- navigation:group_chat -->
{"group_chat_id":"id","name":"n","members":[],"project_path":"/p"}

[点击](#)

${suffix}`;

      const result = parseNavigationMark(content);

      expect(result).not.toBeNull();
      expect(result!.type).toBe('group_chat');
    });

    it('linkText 包含特殊字符也能正确解析', () => /**
     * 契约：linkText 可以包含中文、特殊符号
     */ {
      const content = `<!-- navigation:group_chat -->
{"group_chat_id":"id","name":"n","members":[],"project_path":"/p"}

[👉 点击这里进入群聊！→](#)`;

      const result = parseNavigationMark(content);

      expect(result).not.toBeNull();
      expect(result!.linkText).toBe('👉 点击这里进入群聊！→');
    });

    it('JSON 中包含中文字符也能正确解析', () => /**
     * 契约：JSON 值可以包含 Unicode 字符
     */ {
      const content = `<!-- navigation:create_single_chat -->
{"agent_name":"开发助手","platform":"claude","description":"专业的全栈开发助手，擅长 TypeScript 和 Python"}

[开始对话](#)`;

      const result = parseNavigationMark(content);

      expect(result).not.toBeNull();
      expect((result!.data as any).agent_name).toBe('开发助手');
    });

    it('content 中有多个标记时只解析第一个', () => /**
     * 契约：使用 match（非 matchAll），只返回第一个匹配
     */ {
      const content = `<!-- navigation:group_chat -->
{"group_chat_id":"id-1","name":"群聊1","members":[],"project_path":"/p"}

[点击1](#)

<!-- navigation:group_chat -->
{"group_chat_id":"id-2","name":"群聊2","members":[],"project_path":"/p"}

[点击2](#)`;

      const result = parseNavigationMark(content);

      expect(result).not.toBeNull();
      expect((result!.data as any).group_chat_id).toBe('id-1');
    });
  });
});
