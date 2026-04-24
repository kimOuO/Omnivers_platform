'use client';

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SignalPoint } from '@/services/api/history';

/** Colors per gNB. Falls back to a palette for unexpected names. */
const GNB_COLORS: Record<string, string> = {
  gNB_Macro_NW: '#e94560',
  gNB_Macro_SE: '#2196F3',
  gNB_Small_Plaza: '#4CAF50',
};
const PALETTE = ['#FF9800', '#9C27B0', '#00BCD4', '#CDDC39'];

function colorFor(name: string, idx: number): string {
  return GNB_COLORS[name] ?? PALETTE[idx % PALETTE.length];
}

interface PlotRow extends Record<string, number | string | null> {
  t: number;
  tLabel: string;
}

function buildSeries(points: SignalPoint[]): { rows: PlotRow[]; gnbs: string[] } {
  const gnbSet = new Set<string>();
  points.forEach((p) => {
    if (p.rsrp_map) Object.keys(p.rsrp_map).forEach((k) => gnbSet.add(k));
  });
  const gnbs = Array.from(gnbSet).sort();

  const rows: PlotRow[] = points.map((p) => {
    const t = new Date(p.ts).getTime();
    const d = new Date(p.ts);
    const tLabel = `${d.getHours().toString().padStart(2, '0')}:${d
      .getMinutes()
      .toString()
      .padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
    const row: PlotRow = { t, tLabel };
    for (const g of gnbs) {
      const v = p.rsrp_map?.[g];
      row[g] = typeof v === 'number' ? v : null;
    }
    row._sinr = p.sinr_db;
    return row;
  });
  return { rows, gnbs };
}

interface Props {
  points: SignalPoint[];
  height?: number;
}

export function SignalRsrpChart({ points, height = 300 }: Props) {
  const { rows, gnbs } = buildSeries(points);

  if (rows.length === 0) {
    return <p className="muted">No data in this window. Send ingest signals to see lines.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 10, left: -10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f3a" />
        <XAxis dataKey="tLabel" tick={{ fontSize: 10, fill: '#7ec8e3' }} />
        <YAxis
          tick={{ fontSize: 10, fill: '#7ec8e3' }}
          domain={[-130, -40]}
          label={{ value: 'RSRP (dBm)', angle: -90, position: 'insideLeft', fill: '#7ec8e3', fontSize: 11 }}
        />
        <Tooltip
          contentStyle={{ background: '#0d0d1a', border: '1px solid #333', fontSize: 12 }}
          labelStyle={{ color: '#aaa' }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <ReferenceLine y={-80} stroke="#4CAF50" strokeDasharray="2 4" strokeOpacity={0.4} label={{ value: 'good', fill: '#4CAF50', fontSize: 10, position: 'right' }} />
        <ReferenceLine y={-100} stroke="#FF9800" strokeDasharray="2 4" strokeOpacity={0.4} label={{ value: 'poor', fill: '#FF9800', fontSize: 10, position: 'right' }} />
        {gnbs.map((g, i) => (
          <Line
            key={g}
            type="monotone"
            dataKey={g}
            stroke={colorFor(g, i)}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SignalSinrChart({ points, height = 200 }: Props) {
  const rows = points.map((p) => {
    const d = new Date(p.ts);
    return {
      tLabel: `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`,
      sinr: p.sinr_db,
      serving: p.serving_cell,
    };
  });

  if (rows.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ top: 10, right: 20, bottom: 10, left: -10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f1f3a" />
        <XAxis dataKey="tLabel" tick={{ fontSize: 10, fill: '#7ec8e3' }} />
        <YAxis
          tick={{ fontSize: 10, fill: '#7ec8e3' }}
          domain={[-10, 30]}
          label={{ value: 'SINR (dB)', angle: -90, position: 'insideLeft', fill: '#7ec8e3', fontSize: 11 }}
        />
        <Tooltip contentStyle={{ background: '#0d0d1a', border: '1px solid #333', fontSize: 12 }} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <ReferenceLine y={0} stroke="#e53935" strokeDasharray="2 4" strokeOpacity={0.5} />
        <Line type="monotone" dataKey="sinr" stroke="#FFC107" strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
