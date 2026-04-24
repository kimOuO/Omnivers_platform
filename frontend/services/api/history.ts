// History resource adapter.
// Backend: /api/v0.1/RAN/History/...

import { post } from '@/services/clients/http';

const BASE = '/api/v0.1/RAN/History';

export interface PositionPoint {
  ts: string;
  x: number;
  y: number;
  z: number;
}

export interface SignalPoint {
  ts: string;
  serving_cell: string;
  rsrp_dbm: number;
  sinr_db: number;
  rsrp_map: Record<string, number>;
}

export async function listPositionHistory(ueName: string, since?: string): Promise<PositionPoint[]> {
  return post<PositionPoint[]>(`${BASE}/PositionHistoryReader/read`, {
    body: { ue_name: ueName, since },
  });
}

export async function listSignalHistory(ueName: string, since?: string): Promise<SignalPoint[]> {
  return post<SignalPoint[]>(`${BASE}/SignalHistoryReader/read`, {
    body: { ue_name: ueName, since },
  });
}
