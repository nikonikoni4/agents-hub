import { useEffect } from 'react';
import { wsManager } from '@/core/websocket/WebSocketManager';

export function useWebSocketConnection(activeSessionId: string | null) {
  useEffect(() => {
    if (!activeSessionId) {
      wsManager.disconnect();
      return;
    }

    wsManager.connect(activeSessionId);

    return () => {
      wsManager.disconnect();
    };
  }, [activeSessionId]);
}
