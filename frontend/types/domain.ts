// Domain DTOs — shapes returned by the backend, normalized by services/.

export interface Position3D {
  x: number;
  y: number;
  z: number;
}

export interface GNB {
  name: string;
  position: Position3D;
  freqMhz: number;
  powerDbm: number;
  bwHz: number;
  active: boolean;
}

export interface UE {
  name: string;
  position: Position3D;
  servingCell: string | null;
  rsrpDbm: number | null;
  sinrDb: number | null;
  speedMps: number | null;
}

export interface SceneStatus {
  buildings: number;
  gnbs: number;
  ues: number;
  animating: boolean;
}

export interface SignalSample {
  ueName: string;
  servingCell: string;
  rsrpDbm: number;
  sinrDb: number;
  rsrpMap: Record<string, number>;
  ts: string;
}

export interface Waypoint3D {
  x: number;
  y: number;
  z: number;
}

export interface Trajectory {
  waypoints: Waypoint3D[];
  speedMps: number;
  loop: boolean;
}

export interface Building {
  name: string;
  position: Position3D;
  size: Position3D;
  material: string | null;
}

export interface Ground {
  size?: [number, number];
}

export interface SceneLayout {
  buildings: Building[];
  gnbs: GNB[];
  ues: UE[];
  ground: Ground;
}
