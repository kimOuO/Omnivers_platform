'use client';

import { buildScene, clearScene, startAnimation, stopAnimation } from '@/services/api/scene';

export function SceneControls() {
  return (
    <div className="scene-controls">
      <button className="btn btn-blue" onClick={() => void buildScene()}>
        Build Scene
      </button>
      <button className="btn btn-gray" onClick={() => void clearScene()}>
        Clear Scene
      </button>
      <button className="btn btn-green" onClick={() => void startAnimation()}>
        ▶ Start Animation
      </button>
      <button className="btn btn-red" onClick={() => void stopAnimation()}>
        ■ Stop Animation
      </button>
    </div>
  );
}
