'use client';

import { useEffect, useRef } from 'react';

export function usePolling(callback: () => void, intervalMs: number, enabled: boolean = true): void {
  const ref = useRef(callback);
  ref.current = callback;

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;
    const id = setInterval(() => ref.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}
