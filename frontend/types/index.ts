export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  status: AsyncStatus;
  error: Error | null;
  refetch: () => void;
}

export interface ApiError {
  success: false;
  message: string;
  errors?: Record<string, unknown>;
}

export interface ApiSuccess<T> {
  success: true;
  message: string;
  data: T;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

export interface UsdAsset {
  asset_uuid: string;
  preset_id: string;
  object_type: 'building' | 'ue' | 'obstacle' | 'gnb';
  label: string;
  description?: string;
  usd_path: string;
  default_size?: [number, number, number] | null;
  default_color?: [number, number, number] | null;
  default_scale?: [number, number, number] | null;
  active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Building {
  name: string;
  position: [number, number, number];
  size: [number, number, number];
  color: [number, number, number];
  usd?: string;
  preset_type?: string;
  scale?: [number, number, number];
}

export interface Ground {
  material: string;
  size: [number, number];
}

export interface GNB {
  name: string;
  pci?: number;
  cell_id?: string;
  position: [number, number, number];
  color: [number, number, number];
  frequency_ghz: number;
  power_dbm: number;
  bandwidth_mhz: number;
  active?: boolean;
}

export interface UE {
  name: string;
  prim_path?: string;
  position: [number, number, number];
  color: [number, number, number];
  usd?: string;
  scale?: [number, number, number];
  speed_mps: number;
  waypoints?: Array<[number, number, number]>;
}

export interface SceneConfig {
  scene_id?: string;
  ground: Ground;
  buildings: Building[];
  gnbs: GNB[];
  ues: UE[];
}

export interface InitSceneResponse {
  session_uuid: string;
  scene_id: string;
}

export interface SetupUERequest {
  ues: Array<{
    name: string;
    waypoints: Array<[number, number, number]>;
    speed_mps: number;
    loop?: boolean;
  }>;
}

export interface UESignalData {
  ue_name: string;
  rsrp_dbm?: number;
  sinr_db?: number;
  serving_cell?: string;
  position?: [number, number, number];
}

export interface SimStatus {
  running: boolean;
  current_tick?: number;
  ues?: UESignalData[];
}

export interface PlaybackSession {
  session_uuid: string;
  scene_id: string;
  timestamp: string;
  frame_count: number;
}

export interface PlaybackFrame {
  tick: number;
  ues: UESignalData[];
}
