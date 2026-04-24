import type { SceneStatus } from '@/types';

interface Props {
  status: SceneStatus | null;
  apiOnline: boolean;
}

export function StatusBar({ status, apiOnline }: Props) {
  const fmt = (n: number | undefined) => (n == null ? '-' : String(n));
  return (
    <div className="status-bar">
      <span>Buildings: {fmt(status?.buildings)}</span>
      <span>gNBs: {fmt(status?.gnbs)}</span>
      <span>UEs: {fmt(status?.ues)}</span>
      <span>Animation: {status?.animating ? 'Running' : 'Stopped'}</span>
      <span>API: {apiOnline ? 'ONLINE' : 'OFFLINE'}</span>
    </div>
  );
}
