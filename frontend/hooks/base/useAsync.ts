'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { AsyncState, AsyncStatus, ApiError } from '@/types';

export function useAsync<T>(fn: () => Promise<T>, deps: readonly unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<AsyncStatus>('idle');
  const [error, setError] = useState<ApiError | null>(null);
  const latestCall = useRef(0);

  const run = useCallback(async () => {
    const callId = ++latestCall.current;
    setStatus('loading');
    setError(null);
    try {
      const result = await fn();
      if (latestCall.current !== callId) return;
      setData(result);
      setStatus('success');
    } catch (err) {
      if (latestCall.current !== callId) return;
      const apiErr = err as ApiError;
      setError(apiErr);
      setStatus('error');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, status, error, refetch: run };
}
