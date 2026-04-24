'use client';

import { useCallback, useEffect, useState } from 'react';
import { useAsync } from '@/hooks/base/useAsync';
import { useLiveStream } from '@/hooks/base/useLiveStream';
import { getSceneLayout } from '@/services/api/scene';
import { listUEs, setTrajectory } from '@/services/api/ue';
import { POLL_INTERVALS_MS } from '@/config';
import type { AsyncState, LiveStatus, SceneLayout, UE, Waypoint3D } from '@/types';

interface State {
  layout: AsyncState<SceneLayout>;
  ues: UE[];                      // live-first with polling fallback
  uesStatus: LiveStatus;
  selectedUeName: string | null;
  waypoints: Waypoint3D[];
  speedMps: number;
  loop: boolean;
  applying: boolean;
  applyError: string | null;
  applySuccess: boolean;
  selectUe: (name: string | null) => void;
  setSpeed: (v: number) => void;
  setLoop: (v: boolean) => void;
  addWaypoint: (x: number, z: number) => void;
  moveWaypoint: (index: number, x: number, z: number) => void;
  removeWaypoint: (index: number) => void;
  clearWaypoints: () => void;
  apply: () => Promise<void>;
}

export function useTrajectoryEditorPage(): State {
  const layout = useAsync<SceneLayout>(getSceneLayout);
  const live = useLiveStream();

  // HTTP fallback only while WS is down — avoids wasting a request on mount
  // while WebSocket is still connecting.
  const [fallbackUEs, setFallbackUEs] = useState<UE[]>([]);
  useEffect(() => {
    if (live.status !== 'fallback') return;
    let active = true;
    const tick = async () => {
      try {
        const data = await listUEs();
        if (active) setFallbackUEs(data);
      } catch {
        /* keep stale data */
      }
    };
    tick();
    const id = setInterval(tick, POLL_INTERVALS_MS.dashboard);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [live.status]);

  const ues: UE[] =
    live.status === 'live' && live.data ? live.data.ues : fallbackUEs;

  const [selectedUeName, setSelectedUeName] = useState<string | null>(null);
  const [waypoints, setWaypoints] = useState<Waypoint3D[]>([]);
  const [speedMps, setSpeedMps] = useState<number>(3.0);
  const [loop, setLoop] = useState<boolean>(true);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applySuccess, setApplySuccess] = useState(false);

  const selectUe = useCallback((name: string | null) => {
    setSelectedUeName(name);
    setWaypoints([]);
    setApplyError(null);
    setApplySuccess(false);
  }, []);

  // Auto-select first UE when list first becomes non-empty.
  useEffect(() => {
    if (!selectedUeName && ues.length > 0) {
      setSelectedUeName(ues[0].name);
    }
  }, [selectedUeName, ues]);

  const addWaypoint = useCallback((x: number, z: number) => {
    setWaypoints((prev) => [...prev, { x, y: 0, z }]);
    setApplySuccess(false);
  }, []);

  const moveWaypoint = useCallback((index: number, x: number, z: number) => {
    setWaypoints((prev) => prev.map((w, i) => (i === index ? { x, y: 0, z } : w)));
    setApplySuccess(false);
  }, []);

  const removeWaypoint = useCallback((index: number) => {
    setWaypoints((prev) => prev.filter((_, i) => i !== index));
    setApplySuccess(false);
  }, []);

  const clearWaypoints = useCallback(() => {
    setWaypoints([]);
    setApplyError(null);
    setApplySuccess(false);
  }, []);

  const apply = useCallback(async () => {
    if (!selectedUeName) {
      setApplyError('No UE selected');
      return;
    }
    if (waypoints.length < 2) {
      setApplyError('Need at least 2 waypoints');
      return;
    }
    setApplying(true);
    setApplyError(null);
    setApplySuccess(false);
    try {
      await setTrajectory(selectedUeName, { waypoints, speedMps, loop });
      setApplySuccess(true);
    } catch (err) {
      const msg =
        typeof err === 'object' && err !== null && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Apply failed';
      setApplyError(msg);
    } finally {
      setApplying(false);
    }
  }, [selectedUeName, waypoints, speedMps, loop]);

  return {
    layout,
    ues,
    uesStatus: live.status,
    selectedUeName,
    waypoints,
    speedMps,
    loop,
    applying,
    applyError,
    applySuccess,
    selectUe,
    setSpeed: setSpeedMps,
    setLoop,
    addWaypoint,
    moveWaypoint,
    removeWaypoint,
    clearWaypoints,
    apply,
  };
}
