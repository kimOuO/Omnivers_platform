import type { UE } from './domain';

/** WebSocket stream state machine. */
export type LiveStatus = 'connecting' | 'live' | 'fallback' | 'error';

/** Snapshot pushed from backend every ~500ms over /api/v0.1/RAN/UE/live. */
export interface LiveSnapshot {
  type: 'ue_update';
  ts: number;
  ues: UE[];
}

/** First message after connect. */
export interface LiveHello {
  type: 'hello';
  group: string;
}

export type LiveMessage = LiveSnapshot | LiveHello;
