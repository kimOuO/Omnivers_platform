import { omniverseClient } from '@/services/clients/httpClient';
import type { UsdAsset, Building } from '@/types';

// ─── Assets ─────────────────────────────────────────────────────

export const listAssets = async (objectType?: string): Promise<UsdAsset[]> => {
  const response = await omniverseClient.post<{ data: UsdAsset[] }>(
    '/api/v0.1/RAN/Assets/UsdAssetReader/list',
    { object_type: objectType }
  );
  return response.data.data || [];
};

export const createAsset = async (data: Partial<UsdAsset>): Promise<UsdAsset> => {
  const response = await omniverseClient.post<{ data: UsdAsset }>(
    '/api/v0.1/RAN/Assets/UsdAssetController/create',
    data
  );
  return response.data.data;
};

export const updateAsset = async (
  presetId: string,
  data: Partial<UsdAsset>
): Promise<UsdAsset> => {
  const response = await omniverseClient.post<{ data: UsdAsset }>(
    '/api/v0.1/RAN/Assets/UsdAssetController/update',
    { preset_id: presetId, ...data }
  );
  return response.data.data;
};

export const deleteAsset = async (presetId: string): Promise<void> => {
  await omniverseClient.post('/api/v0.1/RAN/Assets/UsdAssetController/delete', {
    preset_id: presetId,
  });
};

// ─── Buildings ──────────────────────────────────────────────────

export const listBuildings = async (): Promise<Building[]> => {
  const response = await omniverseClient.post<{ data: Building[] }>(
    '/api/v0.1/RAN/Scene/BuildingController/read',
    {}
  );
  return response.data.data || [];
};

export const createBuilding = async (data: Partial<Building>): Promise<Building> => {
  const response = await omniverseClient.post<{ data: Building }>(
    '/api/v0.1/RAN/Scene/BuildingController/create',
    data
  );
  return response.data.data;
};

export const updateBuilding = async (
  name: string,
  data: Partial<Building>
): Promise<Building> => {
  const response = await omniverseClient.post<{ data: Building }>(
    '/api/v0.1/RAN/Scene/BuildingController/update',
    { name, ...data }
  );
  return response.data.data;
};

export const deleteBuilding = async (name: string): Promise<void> => {
  await omniverseClient.post('/api/v0.1/RAN/Scene/BuildingController/delete', {
    name,
  });
};

// ─── GNBs ───────────────────────────────────────────────────────

export const listGnbs = async (): Promise<any[]> => {
  const response = await omniverseClient.post<{ data: any[] }>(
    '/api/v0.1/RAN/GNB/GNBReader/read',
    {}
  );
  return response.data.data || [];
};

// ─── UEs ────────────────────────────────────────────────────────

export const listUes = async (): Promise<any[]> => {
  const response = await omniverseClient.post<{ data: any[] }>(
    '/api/v0.1/RAN/UE/UEReader/read',
    {}
  );
  return response.data.data || [];
};
