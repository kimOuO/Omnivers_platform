'use client';

import { StatusBar } from '@/components/StatusBar';
import { UETable } from '@/components/UETable';
import { GNBTable } from '@/components/GNBTable';
import { SceneControls } from '@/components/SceneControls';
import { useDashboardPage } from '@/hooks/feature/useDashboardPage';

const UE_TITLE_BY_STATUS: Record<string, string> = {
  connecting: 'UE Info (connecting…)',
  live: 'UE Info (live · 2 Hz WS)',
  fallback: 'UE Info (fallback · 1 Hz polling)',
  error: 'UE Info (error)',
};

export default function DashboardPage() {
  const { status, layout, ues, uesStatus } = useDashboardPage();

  const apiOnline = status.status !== 'error' && uesStatus !== 'error';

  return (
    <>
      <StatusBar status={status.data} apiOnline={apiOnline} />

      <div className="grid">
        <div className="card">
          <h2>Scene Control</h2>
          <div className="card-body">
            <SceneControls />
          </div>
        </div>

        <div className="card">
          <h2>gNB Info (static)</h2>
          <div className="card-body">
            {layout.status === 'loading' && <p className="muted">Loading…</p>}
            {layout.status === 'error' && <p className="muted">Error: {layout.error?.message}</p>}
            {layout.data && <GNBTable gnbs={layout.data.gnbs} />}
          </div>
        </div>

        <div className="card full-width">
          <h2>{UE_TITLE_BY_STATUS[uesStatus] ?? 'UE Info'}</h2>
          <div className="card-body">
            {uesStatus === 'connecting' && ues.length === 0 && (
              <p className="muted">Connecting to live stream…</p>
            )}
            {ues.length > 0 && <UETable ues={ues} />}
          </div>
        </div>
      </div>
    </>
  );
}
