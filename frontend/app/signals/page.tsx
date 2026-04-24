'use client';

import { SignalRsrpChart, SignalSinrChart } from '@/components/SignalChart';
import { useSignalsPage, WINDOWS } from '@/hooks/feature/useSignalsPage';

export default function SignalsPage() {
  const v = useSignalsPage();
  const data = v.history.data ?? [];

  return (
    <div className="card full-width">
      <h2>Signal History</h2>
      <div className="card-body">
        {/* Controls */}
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end', marginBottom: 16, flexWrap: 'wrap' }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: '#7ec8e3', marginBottom: 4 }}>
              UE
            </label>
            <select
              value={v.selectedUe ?? ''}
              onChange={(e) => v.selectUe(e.target.value || null)}
              style={{
                padding: '6px 10px',
                background: '#1a1a2e',
                color: '#eee',
                border: '1px solid #0f3460',
                borderRadius: 4,
                fontSize: 13,
              }}
            >
              <option value="">— select —</option>
              {v.ues.map((u) => (
                <option key={u.name} value={u.name}>
                  {u.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 12, color: '#7ec8e3', marginBottom: 4 }}>
              Time window
            </label>
            <div style={{ display: 'flex', gap: 4 }}>
              {WINDOWS.map((w) => (
                <button
                  key={w}
                  onClick={() => v.setWindow(w)}
                  className={v.window === w ? 'btn btn-blue' : 'btn btn-gray'}
                  style={{ padding: '4px 10px', fontSize: 12, margin: 0 }}
                >
                  {w}
                </button>
              ))}
            </div>
          </div>

          <button className="btn btn-gray" onClick={v.refresh}>
            Refresh
          </button>

          <div style={{ fontSize: 12, color: '#666', marginLeft: 'auto' }}>
            Stream: {v.uesStatus} · Points: {data.length} · Auto-refresh 5s
          </div>
        </div>

        {v.history.status === 'loading' && data.length === 0 && (
          <p className="muted">Loading…</p>
        )}
        {v.history.status === 'error' && (
          <p className="muted">Error: {v.history.error?.message}</p>
        )}

        {v.selectedUe && (
          <>
            <h3 style={{ fontSize: 14, margin: '12px 0 4px', color: '#aad4ff' }}>
              RSRP per gNB
            </h3>
            <SignalRsrpChart points={data} />

            <h3 style={{ fontSize: 14, margin: '20px 0 4px', color: '#aad4ff' }}>
              SINR (serving cell)
            </h3>
            <SignalSinrChart points={data} />
          </>
        )}

        {!v.selectedUe && v.ues.length === 0 && (
          <p className="muted">
            No UEs in live stream. Ensure Kit is running and a scene is built, then come back.
          </p>
        )}

        <div style={{ marginTop: 20, padding: 12, background: '#0d0d1a', border: '1px solid #333', borderRadius: 4 }}>
          <div style={{ fontSize: 12, color: '#7ec8e3', marginBottom: 6 }}>
            <strong>Need test data?</strong> Run from host:
          </div>
          <pre style={{ fontSize: 11, color: '#aaa', overflowX: 'auto', margin: 0 }}>
{`curl -X POST http://localhost:8001/api/v0.1/RAN/Ingest/SignalIngestor/create \\
  -H "Content-Type: application/json" \\
  -d '{"ts":"${new Date().toISOString()}","signals":[
    {"ue_name":"${v.selectedUe ?? 'UE_Handover_Path'}","serving_cell":"gNB_Macro_NW",
     "rsrp_dbm":-78,"sinr_db":12,
     "rsrp_map":{"gNB_Macro_NW":-78,"gNB_Macro_SE":-92,"gNB_Small_Plaza":-85}}
  ]}'`}
          </pre>
        </div>
      </div>
    </div>
  );
}
