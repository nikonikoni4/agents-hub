/**
 * 集成测试示例
 *
 * 验证 API 调用和 WebSocket 连接
 */

import { createGroupChat, listGroupChats, getMessages, listRoles, USE_MOCK } from '@/core/api';
import { wsManager } from '@/core/websocket/WebSocketManager';

// ==================== 测试场景 1：API 调用流程 ====================

export async function testApiFlow() {
  console.log('=== 测试 API 调用流程 ===');
  console.log('Mock 模式:', USE_MOCK ? '开启' : '关闭');

  try {
    // 1. 创建群聊
    console.log('\n1. 创建群聊...');
    const chat = await createGroupChat({
      team_members: ['Agent1', 'Agent2'],
      project_path: '/home/user/test-project',
      group_chat_name: 'Test Chat',
    });
    console.log('✓ 群聊创建成功:', chat);

    // 2. 获取群聊列表
    console.log('\n2. 获取群聊列表...');
    const chats = await listGroupChats();
    console.log(`✓ 获取到 ${chats.length} 个群聊`);

    // 3. 获取消息历史
    console.log('\n3. 获取消息历史...');
    const messages = await getMessages(chat.group_chat_id);
    console.log(`✓ 获取到 ${messages.length} 条消息`);

    // 4. 获取角色列表
    console.log('\n4. 获取角色列表...');
    const roles = await listRoles();
    console.log(`✓ 获取到 ${roles.length} 个角色`);

    console.log('\n✅ API 调用流程测试通过');
  } catch (error) {
    console.error('❌ API 调用流程测试失败:', error);
  }
}

// ==================== 测试场景 2：WebSocket 连接 ====================

export function testWebSocketConnection() {
  console.log('\n=== 测试 WebSocket 连接 ===');

  // 订阅事件
  wsManager.on('connected', () => {
    console.log('✓ WebSocket 连接成功');
    console.log('当前状态:', wsManager.getState());
  });

  wsManager.on('disconnected', () => {
    console.log('✓ WebSocket 断开连接');
  });

  wsManager.on('message', (data) => {
    console.log('✓ 收到消息:', data);
  });

  wsManager.on('refresh', (signal) => {
    console.log('✓ 收到刷新信号:', signal);
  });

  wsManager.on('error', (error) => {
    console.error('✗ WebSocket 错误:', error);
  });

  // 连接到测试群聊
  console.log('\n连接到测试群聊...');
  wsManager.connect('test-chat-001');

  // 5 秒后断开测试
  setTimeout(() => {
    console.log('\n断开连接...');
    wsManager.disconnect();
  }, 5000);
}

// ==================== 测试场景 3：WebSocket 重连 ====================

export function testWebSocketReconnect() {
  console.log('\n=== 测试 WebSocket 重连机制 ===');

  let reconnectCount = 0;

  wsManager.on('connected', () => {
    reconnectCount++;
    console.log(`✓ 第 ${reconnectCount} 次连接成功`);
    console.log('重连尝试次数:', wsManager.getReconnectAttempts());

    // 第一次连接后立即断开（模拟网络中断）
    if (reconnectCount === 1) {
      setTimeout(() => {
        console.log('\n模拟网络中断...');
        // 直接关闭底层 WebSocket（不调用 disconnect）
        // @ts-expect-error - 访问私有属性用于测试
        if (wsManager.ws) {
          // @ts-expect-error - 访问私有属性用于测试
          wsManager.ws.close();
        }
      }, 1000);
    }
  });

  wsManager.on('error', (error) => {
    console.log('✗ 连接错误:', error.message);
  });

  wsManager.connect('test-chat-reconnect');

  // 20 秒后清理
  setTimeout(() => {
    console.log('\n清理测试...');
    wsManager.disconnect();
    console.log(`\n✅ 重连测试完成，共重连 ${reconnectCount - 1} 次`);
  }, 20000);
}

// ==================== 运行所有测试 ====================

export async function runAllTests() {
  console.log('🚀 开始集成测试\n');

  // 测试 1: API 调用
  await testApiFlow();

  // 等待 2 秒
  await new Promise((resolve) => setTimeout(resolve, 2000));

  // 测试 2: WebSocket 连接
  testWebSocketConnection();

  // 等待 7 秒（测试 2 完成）
  await new Promise((resolve) => setTimeout(resolve, 7000));

  // 测试 3: WebSocket 重连
  // testWebSocketReconnect(); // 取消注释以测试重连

  console.log('\n🎉 所有测试完成');
}

// ==================== 使用说明 ====================

/**
 * 在浏览器控制台中运行：
 *
 * // 导入测试函数
 * import { runAllTests, testApiFlow, testWebSocketConnection } from '@/tests/integration.test';
 *
 * // 运行所有测试
 * runAllTests();
 *
 * // 或单独运行某个测试
 * testApiFlow();
 * testWebSocketConnection();
 */
