// WebSocket stream client. Server pushes JSON every ~500ms.
// On connect failures, retries with exponential backoff (1s, 2s, 4s). After
// 3 failed attempts, signals 'fallback' so the caller can switch to polling.

import { WS_URL } from '@/config';
import type { LiveStatus } from '@/types';

export type { LiveStatus };

interface Handle {
  close: () => void;
}

export function createLiveStream<T>(
  onMessage: (data: T) => void,
  onStatus: (s: LiveStatus) => void,
): Handle {
  let ws: WebSocket | null = null;
  let retries = 0;
  let closed = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const connect = () => {
    if (closed) return;
    onStatus('connecting');

    // Defer WS creation by one tick so React StrictMode's synthetic
    // mount→unmount→mount pair doesn't spawn a doomed socket (would log
    // "WebSocket is closed before the connection is established").
    reconnectTimer = setTimeout(() => {
      if (closed) return;
      openSocket();
    }, 0);
  };

  const openSocket = () => {
    if (closed) return;
    try {
      ws = new WebSocket(WS_URL);
    } catch {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      retries = 0;
      onStatus('live');
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as T;
        onMessage(data);
      } catch {
        /* ignore malformed */
      }
    };

    ws.onerror = () => {
      /* wait for onclose */
    };

    ws.onclose = () => {
      if (closed) return;
      scheduleReconnect();
    };
  };

  const scheduleReconnect = () => {
    retries += 1;
    if (retries >= 3) {
      onStatus('fallback');
      return;
    }
    const delay = Math.min(1000 * 2 ** (retries - 1), 4000);
    reconnectTimer = setTimeout(connect, delay);
  };

  connect();

  return {
    close: () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        try {
          ws.close();
        } catch {
          /* ignore */
        }
      }
    },
  };
}
