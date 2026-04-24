// gNB resource adapter.
// Backend: /api/v0.1/RAN/GNB/...

import { post } from '@/services/clients/http';
import type { GNB, Position3D } from '@/types';

const BASE = '/api/v0.1/RAN/GNB';

interface GNBDTO {
  name: string;
  position?: { x?: number; y?: number; z?: number };
  freq_mhz?: number;
  power_dbm?: number;
  bw_hz?: number;
  active?: boolean;
}

function normalizeGNB(dto: GNBDTO): GNB {
  const p = dto.position ?? { x: 0, y: 0, z: 0 };
  const pos: Position3D = { x: p.x ?? 0, y: p.y ?? 0, z: p.z ?? 0 };
  return {
    name: dto.name,
    position: pos,
    freqMhz: dto.freq_mhz ?? 0,
    powerDbm: dto.power_dbm ?? 0,
    bwHz: dto.bw_hz ?? 0,
    active: dto.active ?? true,
  };
}

export async function listGNBs(): Promise<GNB[]> {
  const dtos = await post<GNBDTO[]>(`${BASE}/GNBReader/read`);
  return dtos.map(normalizeGNB);
}

export async function updateGNBState(
  name: string,
  params: { powerDbm?: number; active?: boolean },
): Promise<void> {
  await post(`${BASE}/GNBController/update`, {
    body: {
      name,
      power_dbm: params.powerDbm,
      active: params.active,
    },
  });
}
