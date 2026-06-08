/**
 * SSE 流式请求客户端
 *
 * 职责：
 * - 封装 fetch + ReadSSE 流式读取
 * - 解析 SSE data 行
 * - 支持 AbortController 取消
 *
 * 与 apiClient (axios) 并列，专门处理 text/event-stream 响应
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface SSEEvent {
  type: string;
  content: Record<string, unknown>;
  session_id: string;
  timestamp: string;
  agent_name: string;
  platform: string;
  role_type: string;
}

export type SSEEventCallback = (event: SSEEvent) => void;

/**
 * 发送请求并以 SSE 方式读取流式响应
 *
 * @param path - API 路径（不含 base URL），如 `/single-chats/{id}/messages/stream`
 * @param body - 请求体
 * @param onEvent - 每收到一个 SSE 事件时的回调
 * @param signal - AbortSignal 用于取消请求
 */
export async function streamSSE(
  path: string,
  body: Record<string, unknown>,
  onEvent: SSEEventCallback,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop()!;

      for (const rawLine of lines) {
        const line = rawLine.replace(/\r$/, '');
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6)) as SSEEvent;
            onEvent(event);
          } catch {
            // 忽略解析错误的行
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
