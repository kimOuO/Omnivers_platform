// UE resource adapter.
// Backend: /api/v0.1/RAN/UE/...
//
// NOTE: ue name goes in the POST body (backend_rule.md §7-2, POST-only).

import { post } from '@/services/clients/http';
import type { Position3D, Trajectory, UE } from '@/types';

const BASE = '/api/v0.1/RAN/UE';

interface UEDTO {
  name: string;
  position?: { x?: number; y?: number; z?: number };
  serving_cell?: string | null;
  rsrp_dbm?: number | null;
  sinr_db?: number | null;
}

function normalizeUE(dto: UEDTO): UE {
  const p = dto.position ?? { x: 0, y: 0, z: 0 };
  return {
    name: dto.name,
    position: { x: p.x ?? 0, y: p.y ?? 0, z: p.z ?? 0 },
    servingCell: dto.serving_cell ?? null,
    rsrpDbm: dto.rsrp_dbm ?? null,
    sinrDb: dto.sinr_db ?? null,
    speedMps: null,
  };
}

export async function listUEs(): Promise<UE[]> {
  const dtos = await post<UEDTO[]>(`${BASE}/UEReader/read`);
  return dtos.map(normalizeUE);
}

export async function moveUE(name: string, position: Position3D): Promise<void> {
  await post(`${BASE}/UEController/move`, {
    body: { name, x: position.x, y: position.y, z: position.z },
  });
}

export async function setTrajectory(name: string, trajectory: Trajectory): Promise<void> {
  await post(`${BASE}/UEController/trajectory`, {
    body: {
      name,
      waypoints: trajectory.waypoints.map((w) => [w.x, w.y, w.z]),
      speed_mps: trajectory.speedMps,
      loop: trajectory.loop,
    },
  });
}
