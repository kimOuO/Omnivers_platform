// Static configuration only. No runtime logic. No React. No network.

export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export const WS_URL: string =
  process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:8000/api/ws/live';

export const DEFAULT_FETCH_TIMEOUT_MS = 10_000;

export const POLL_INTERVALS_MS = {
  dashboard: 1000,
  gnbTable: 10_000,
} as const;
