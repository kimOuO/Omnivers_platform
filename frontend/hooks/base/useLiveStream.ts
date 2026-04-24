'use client';

import { useEffect, useState } from 'react';
import { createLiveStream, type LiveStatus } from '@/services/clients/websocket';
import type { LiveMessage, LiveSnapshot } from '@/types';

interface State {
  /** Latest UE snapshot, null until first ue_update arrives. */
  data: LiveSnapshot | null;
  /** Stream lifecycle state. UI uses `fallback` to re-enable HTTP polling. */
  status: LiveStatus;
}

/** Subscribe to /api/v0.1/RAN/UE/live for 2 Hz UE snapshots. */
export function useLiveStream(): State {
  const [data, setData] = useState<LiveSnapshot | null>(null);
  const [status, setStatus] = useState<LiveStatus>('connecting');

  useEffect(() => {
    const stream = createLiveStream<LiveMessage>(
      (msg) => {
        if (msg.type === 'ue_update') {
          setData(msg);
        }
      },
      setStatus,
    );
    return () => stream.close();
  }, []);

  return { data, status };
}
