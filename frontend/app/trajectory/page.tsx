'use client';

import { TopDownMap } from '@/components/TopDownMap';
import { useTrajectoryEditorPage } from '@/hooks/feature/useTrajectoryEditorPage';

export default function TrajectoryPage() {
  const v = useTrajectoryEditorPage();

  const layoutReady = v.layout.status === 'success' && v.layout.data !== null;
  const layoutData = v.layout.data;

  return (
    <div className="card full-width">
      <h2>Trajectory Editor</h2>
      <div className="card-body">
        <p className="muted" style={{ marginBottom: 12 }}>
          Pick a UE → click the map to add waypoints → drag to adjust → right-click to delete → Apply.
        </p>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {/* Controls */}
          <div style={{ minWidth: 260, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, color: '#7ec8e3', marginBottom: 4 }}>
                Target UE
              </label>
              <select
                value={v.selectedUeName ?? ''}
                onChange={(e) => v.selectUe(e.target.value || null)}
                style={{
                  width: '100%',
                  padding: '6px 8px',
                  background: '#1a1a2e',
                  color: '#eee',
                  border: '1px solid #0f3460',
                  borderRadius: 4,
                  fontSize: 13,
                }}
              >
                <option value="">— select —</option>
                {v.ues.map((u) => (
                  <option key={u.name} value={u.name}>{u.name}</option>
                ))}
              </select>
              <small style={{ fontSize: 10, color: '#666' }}>Stream: {v.uesStatus}</small>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, color: '#7ec8e3', marginBottom: 4 }}>
                Speed: <strong>{v.speedMps.toFixed(1)} m/s</strong>
              </label>
              <input
                type="range"
                min={0.5}
                max={10}
                step={0.5}
                value={v.speedMps}
                onChange={(e) => v.setSpeed(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
              <input
                type="checkbox"
                checked={v.loop}
                onChange={(e) => v.setLoop(e.target.checked)}
              />
              Loop (ping-pong)
            </label>

            <div style={{ fontSize: 12, color: '#888' }}>
              Waypoints: <strong>{v.waypoints.length}</strong>
              {v.waypoints.length > 0 && (
                <ul style={{ margin: '4px 0 0 16px', padding: 0, fontFamily: 'monospace', fontSize: 11 }}>
                  {v.waypoints.map((w, i) => (
                    <li key={i} style={{ listStyle: 'decimal' }}>
                      ({w.x.toFixed(0)}, {w.z.toFixed(0)})
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button
                className="btn btn-blue"
                onClick={() => { void v.apply(); }}
                disabled={v.applying || v.waypoints.length < 2}
              >
                {v.applying ? 'Applying…' : 'Apply'}
              </button>
              <button
                className="btn btn-gray"
                onClick={v.clearWaypoints}
                disabled={v.waypoints.length === 0}
              >
                Clear
              </button>
            </div>

            {v.applyError && (
              <div style={{ color: '#e53935', fontSize: 12 }}>Error: {v.applyError}</div>
            )}
            {v.applySuccess && (
              <div style={{ color: '#4CAF50', fontSize: 12 }}>✓ Trajectory applied</div>
            )}
          </div>

          {/* Map */}
          <div>
            {!layoutReady && <p className="muted">Loading layout…</p>}
            {v.layout.status === 'error' && (
              <p className="muted">Error: {v.layout.error?.message}</p>
            )}
            {layoutReady && layoutData && (
              <TopDownMap
                buildings={layoutData.buildings}
                gnbs={layoutData.gnbs}
                ues={v.ues.length > 0 ? v.ues : layoutData.ues}
                selectedUeName={v.selectedUeName}
                waypoints={v.waypoints}
                onAddWaypoint={v.addWaypoint}
                onMoveWaypoint={v.moveWaypoint}
                onRemoveWaypoint={v.removeWaypoint}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
