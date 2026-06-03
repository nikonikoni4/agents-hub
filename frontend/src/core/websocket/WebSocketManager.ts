/**
 * WebSocket 管理器
 *
 * 单例模式的 WebSocket 连接管理，支持：
 * - 自动重连（指数退避）
 * - 消息队列（离线时缓存）
 * - 事件订阅系统
 */

import type {
  WebSocketEventType,
  WebSocketEventCallback,
  WebSocketState,
  RefreshSignal,
} from '@/shared/types';

// ==================== WebSocket 管理器 ====================

class WebSocketManager {
  private static instance: WebSocketManager;
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<WebSocketEventCallback>> = new Map();
  private messageQueue: any[] = [];
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectTimeouts: number[] = [1000, 2000, 4000, 8000, 16000]; // 指数退避
  private reconnectTimer: number | null = null;
  private currentChatId: string | null = null;
  private isIntentionalClose: boolean = false;

  private constructor() {
    // 私有构造函数，防止外部实例化
  }

  /**
   * 获取单例实例
   */
  static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager();
    }
    return WebSocketManager.instance;
  }

  /**
   * 连接到指定群聊
   */
  connect(chatId: string): void {
    // 如果已连接到同一个群聊，不重复连接
    if (this.ws && this.currentChatId === chatId && this.ws.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected to', chatId);
      return;
    }

    // 断开旧连接
    if (this.ws) {
      this.disconnect();
    }

    this.currentChatId = chatId;
    this.isIntentionalClose = false;
    this.reconnectAttempts = 0;

    this._createConnection(chatId);
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.isIntentionalClose = true;
    this.currentChatId = null;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this._emit('disconnected');
  }

  /**
   * 发送消息
   */
  send(data: any): void {
    const message = JSON.stringify(data);

    // 如果连接正常，直接发送
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
      return;
    }

    // 否则加入队列
    this.messageQueue.push(data);

    // 限制队列大小
    if (this.messageQueue.length > 100) {
      this.messageQueue.shift(); // 移除最早的消息
      console.warn('[WebSocket] Message queue overflow, dropped oldest message');
    }
  }

  /**
   * 订阅事件
   */
  on(event: WebSocketEventType, callback: WebSocketEventCallback): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  /**
   * 取消订阅事件
   */
  off(event: WebSocketEventType, callback: WebSocketEventCallback): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }

  /**
   * 获取当前连接状态
   */
  getState(): WebSocketState {
    return (this.ws?.readyState ?? WebSocket.CLOSED) as WebSocketState;
  }

  /**
   * 获取当前重连次数
   */
  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  // ==================== 私有方法 ====================

  /**
   * 创建 WebSocket 连接
   */
  private _createConnection(chatId: string): void {
    const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api/v1';
    const wsUrl = `${wsBaseUrl}/ws/group_chat/${chatId}`;

    console.log('[WebSocket] Connecting to', wsUrl);

    try {
      this.ws = new WebSocket(wsUrl);
      this._setupEventHandlers();
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      this._emit('error', error);
      this._scheduleReconnect();
    }
  }

  /**
   * 设置 WebSocket 事件处理器
   */
  private _setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected');
      this.reconnectAttempts = 0;
      this._emit('connected');

      // 发送队列中的消息
      this._flushMessageQueue();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('[WebSocket] Message received:', data);

        // 根据消息类型触发不同事件
        if (data.type === 'refresh') {
          this._emit('refresh', data as RefreshSignal);
        } else {
          this._emit('message', data);
        }
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
      this._emit('error', error);
    };

    this.ws.onclose = (event) => {
      console.log('[WebSocket] Closed:', event.code, event.reason);
      this.ws = null;

      // 如果不是主动断开，尝试重连
      if (!this.isIntentionalClose) {
        this._scheduleReconnect();
      }
    };
  }

  /**
   * 调度重连
   */
  private _scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached');
      this._emit('error', new Error('Max reconnect attempts reached'));
      return;
    }

    const delay = this.reconnectTimeouts[this.reconnectAttempts] || 16000;
    this.reconnectAttempts++;

    console.log(
      `[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    this.reconnectTimer = window.setTimeout(() => {
      if (this.currentChatId) {
        this._createConnection(this.currentChatId);
      }
    }, delay);
  }

  /**
   * 发送队列中的消息
   */
  private _flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;

    console.log(`[WebSocket] Flushing ${this.messageQueue.length} queued messages`);

    while (this.messageQueue.length > 0) {
      const data = this.messageQueue.shift();
      this.send(data);
    }
  }

  /**
   * 触发事件
   */
  private _emit(event: WebSocketEventType, data?: any): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(data);
        } catch (error) {
          console.error(`[WebSocket] Error in ${event} callback:`, error);
        }
      });
    }
  }
}

// ==================== 导出 ====================

export default WebSocketManager;

// 导出单例实例（便于使用）
export const wsManager = WebSocketManager.getInstance();
