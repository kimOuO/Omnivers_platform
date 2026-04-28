'use client';

import { useState, useCallback } from 'react';
import { useAsync } from '@/hooks/base/useAsync';
import * as omniverseApi from '@/services/api/omniverse';
import { initScene } from '@/services/api/scene';
import type { UsdAsset, Building, AsyncState } from '@/types';

export interface SceneEditorState {
  buildings: AsyncState<Building[]>;
  gnbs: AsyncState<any[]>;
  ues: AsyncState<any[]>;
  assets: AsyncState<UsdAsset[]>;
  createBuilding: (data: Partial<Building>) => Promise<void>;
  deleteBuilding: (name: string) => Promise<void>;
  applyScene: (sceneId: string) => Promise<void>;
  isCreating: boolean;
  isDeleting: boolean;
  isApplying: boolean;
}

export function useSceneEditor(): SceneEditorState {
  const [isCreating, setIsCreating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isApplying, setIsApplying] = useState(false);

  const buildings = useAsync(() => omniverseApi.listBuildings());
  const gnbs = useAsync(() => omniverseApi.listGnbs());
  const ues = useAsync(() => omniverseApi.listUes());
  const assets = useAsync(() => omniverseApi.listAssets());

  const createBuilding = useCallback(
    async (data: Partial<Building>) => {
      try {
        setIsCreating(true);
        await omniverseApi.createBuilding(data);
        await buildings.refetch();
      } finally {
        setIsCreating(false);
      }
    },
    [buildings]
  );

  const deleteBuilding = useCallback(
    async (name: string) => {
      try {
        setIsDeleting(true);
        await omniverseApi.deleteBuilding(name);
        await buildings.refetch();
      } finally {
        setIsDeleting(false);
      }
    },
    [buildings]
  );

  const applyScene = useCallback(
    async (sceneId: string) => {
      try {
        setIsApplying(true);
        // Only send scene_id; SceneGateway/init will fetch from DB if needed
        const config = {
          scene_id: sceneId,
          ground: { material: 'grass', size: [1000, 1000] },
          buildings: buildings.data || [],
          gnbs: gnbs.data || [],
          ues: ues.data || [],
        };
        await initScene(config);
      } finally {
        setIsApplying(false);
      }
    },
    [buildings.data, gnbs.data, ues.data]
  );

  return {
    buildings,
    gnbs,
    ues,
    assets,
    createBuilding,
    deleteBuilding,
    applyScene,
    isCreating,
    isDeleting,
    isApplying,
  };
}
