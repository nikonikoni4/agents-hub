/**
 * WebSocket 相关类型定义
 */

// ==================== WebSocket 事件类型 ====================

/**
 * 刷新信号
 * 对应后端 RefreshSignal
 */
export interface RefreshSignal {
  type: string; // 信号类型（默认 "refresh"）
  group_chat_id: string; // 群聊 ID
  timestamp: string; // 信号时间戳
}

/**
 * WebSocket 事件名称
 */
export type WebSocketEventType =
  | 'message' // 新消息到达
  | 'refresh' // 刷新信号
  | 'connected' // 连接成功
  | 'disconnected' // 连接断开
  | 'error'; // 发生错误

/**
 * WebSocket 连接状态
 */
export enum WebSocketState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3,
}

/**
 * WebSocket 事件回调类型
 */
export type WebSocketEventCallback = (data?: unknown) => void;

// ==================== WebSocket 消息格式 ====================

/**
 * WebSocket 消息包装
 */
export interface WebSocketMessage {
  event: string;
  data: unknown;
  timestamp: string;
}
