'use client';

import { useEffect, useState } from 'react';
import { useAsync } from '@/hooks/base/useAsync';
import { useLiveStream } from '@/hooks/base/useLiveStream';
import { listSignalHistory, type SignalPoint } from '@/services/api/history';
import type { AsyncState, LiveStatus, UE } from '@/types';

const WINDOWS = ['-5m', '-15m', '-30m', '-1h'] as const;
type Window = (typeof WINDOWS)[number];

interface State {
  ues: UE[];
  uesStatus: LiveStatus;
  selectedUe: string | null;
  selectUe: (name: string | null) => void;
  window: Window;
  setWindow: (w: Window) => void;
  history: AsyncState<SignalPoint[]>;
  refresh: () => void;
}

export function useSignalsPage(): State {
  const live = useLiveStream();
  const ues = live.status === 'live' && live.data ? live.data.ues : [];

  const [selectedUe, setSelectedUe] = useState<string | null>(null);
  const [window, setWindowState] = useState<Window>('-15m');

  // Auto-select first UE once list populates.
  useEffect(() => {
    if (!selectedUe && ues.length > 0) setSelectedUe(ues[0].name);
  }, [selectedUe, ues]);

  const fetchHistory = async () => {
    if (!selectedUe) return [];
    return listSignalHistory(selectedUe, window);
  };

  const history = useAsync<SignalPoint[]>(fetchHistory, [selectedUe, window]);

  // Auto-refresh every 5 seconds so new ingested data shows up.
  useEffect(() => {
    if (!selectedUe) return;
    const id = setInterval(() => history.refetch(), 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUe, window]);

  return {
    ues,
    uesStatus: live.status,
    selectedUe,
    selectUe: setSelectedUe,
    window,
    setWindow: setWindowState,
    history,
    refresh: history.refetch,
  };
}

export { WINDOWS };
export type { Window };
