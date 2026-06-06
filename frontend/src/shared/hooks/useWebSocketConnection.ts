import { useEffect } from 'react';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { useSessionStore } from '@/features/session/store/sessionStore';

export function useWebSocketConnection() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);

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
