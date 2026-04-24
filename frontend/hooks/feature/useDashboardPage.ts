'use client';

import { useEffect, useState } from 'react';
import { useAsync } from '@/hooks/base/useAsync';
import { useLiveStream } from '@/hooks/base/useLiveStream';
import { usePolling } from '@/hooks/base/usePolling';
import { getSceneLayout, getSceneStatus } from '@/services/api/scene';
import { listUEs } from '@/services/api/ue';
import { POLL_INTERVALS_MS } from '@/config';
import type { AsyncState, LiveStatus, SceneLayout, SceneStatus, UE } from '@/types';

interface DashboardState {
  status: AsyncState<SceneStatus>;    // polled: animating flag
  layout: AsyncState<SceneLayout>;    // ONE-SHOT: buildings + gNBs (static)
  ues: UE[];                          // live-first; falls back to polling
  uesStatus: LiveStatus;              // UI signal: 'live' | 'fallback' | ...
}

/**
 * Data contract for the dashboard:
 *   - buildings / gnbs come from `layout` — fetched once (they don't move)
 *   - UE positions + signals come from WebSocket live stream (2 Hz)
 *   - On WS fallback, falls back to 1 Hz HTTP polling (no request while WS is live)
 *   - `status.animating` tells whether the scene animation is running
 */
export function useDashboardPage(): DashboardState {
  const status = useAsync<SceneStatus>(getSceneStatus);
  const layout = useAsync<SceneLayout>(getSceneLayout);
  const live = useLiveStream();

  // HTTP fallback: only fetches when live status is in 'fallback' — avoids
  // wasting a request on mount while WebSocket is still connecting.
  const [fallbackUEs, setFallbackUEs] = useState<UE[]>([]);
  useEffect(() => {
    if (live.status !== 'fallback') return;

    let active = true;
    const tick = async () => {
      try {
        const data = await listUEs();
        if (active) setFallbackUEs(data);
      } catch {
        /* keep stale data; UI shows last-known state */
      }
    };
    tick(); // immediate fetch on entering fallback
    const id = setInterval(tick, POLL_INTERVALS_MS.dashboard);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [live.status]);

  usePolling(status.refetch, POLL_INTERVALS_MS.dashboard);

  // Layout is static, but the initial fetch can race with backend cold-start
  // (daphne returns 404 for ~5s before URLConf is loaded). Retry on error
  // until we get it, then stop — no ongoing polling cost once successful.
  useEffect(() => {
    if (layout.status !== 'error') return;
    const id = setTimeout(() => { layout.refetch(); }, 2000);
    return () => clearTimeout(id);
  }, [layout.status, layout.refetch]);

  const ues: UE[] =
    live.status === 'live' && live.data ? live.data.ues : fallbackUEs;

  return { status, layout, ues, uesStatus: live.status };
}
