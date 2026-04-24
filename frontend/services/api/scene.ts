// Scene resource adapter.
// Backend: /api/v0.1/RAN/Scene/...

import { post } from '@/services/clients/http';
import type { Building, Position3D, SceneLayout, SceneStatus } from '@/types';

const BASE = '/api/v0.1/RAN/Scene';

interface SceneStatusDTO {
  buildings?: number;
  gnbs?: number;
  ues?: number;
  animating?: boolean;
}

function normalizeSceneStatus(dto: SceneStatusDTO): SceneStatus {
  return {
    buildings: dto.buildings ?? 0,
    gnbs: dto.gnbs ?? 0,
    ues: dto.ues ?? 0,
    animating: dto.animating ?? false,
  };
}

export async function getSceneStatus(): Promise<SceneStatus> {
  const dto = await post<SceneStatusDTO>(`${BASE}/SceneStateReader/read`);
  return normalizeSceneStatus(dto);
}

interface BuildingDTO {
  name: string;
  position?: { x?: number; y?: number; z?: number };
  size?: { x?: number; y?: number; z?: number };
  material?: string | null;
}

function toXYZ(p?: { x?: number; y?: number; z?: number }): Position3D {
  const v = p ?? {};
  return { x: v.x ?? 0, y: v.y ?? 0, z: v.z ?? 0 };
}

function normalizeBuilding(dto: BuildingDTO): Building {
  return {
    name: dto.name,
    position: toXYZ(dto.position),
    size: toXYZ(dto.size),
    material: dto.material ?? null,
  };
}

interface LayoutDTO {
  buildings?: BuildingDTO[];
  gnbs?: {
    name: string;
    position?: { x?: number; y?: number; z?: number };
    freq_mhz?: number;
    power_dbm?: number;
    bw_hz?: number;
    active?: boolean;
  }[];
  ues?: {
    name: string;
    position?: { x?: number; y?: number; z?: number };
    serving_cell?: string | null;
    rsrp_dbm?: number | null;
    sinr_db?: number | null;
    speed_mps?: number | null;
  }[];
  ground?: { size?: [number, number] };
}

export async function getSceneLayout(): Promise<SceneLayout> {
  const dto = await post<LayoutDTO>(`${BASE}/SceneLayoutReader/read`);
  return {
    buildings: (dto.buildings ?? []).map(normalizeBuilding),
    gnbs: (dto.gnbs ?? []).map((g) => ({
      name: g.name,
      position: toXYZ(g.position),
      freqMhz: g.freq_mhz ?? 0,
      powerDbm: g.power_dbm ?? 0,
      bwHz: g.bw_hz ?? 0,
      active: g.active ?? true,
    })),
    ues: (dto.ues ?? []).map((u) => ({
      name: u.name,
      position: toXYZ(u.position),
      servingCell: u.serving_cell ?? null,
      rsrpDbm: u.rsrp_dbm ?? null,
      sinrDb: u.sinr_db ?? null,
      speedMps: u.speed_mps ?? null,
    })),
    ground: dto.ground ?? {},
  };
}

export async function buildScene(): Promise<void> {
  await post(`${BASE}/SceneController/build`);
}

export async function clearScene(): Promise<void> {
  await post(`${BASE}/SceneController/clear`);
}

export async function startAnimation(): Promise<void> {
  await post(`${BASE}/AnimationController/start`);
}

export async function stopAnimation(): Promise<void> {
  await post(`${BASE}/AnimationController/stop`);
}
