'use client';

import { useRef, useState, type MouseEvent as RMouseEvent } from 'react';
import type { Building, GNB, UE, Waypoint3D } from '@/types';

// Scene coordinate bounds (meters). Chosen to cover the default 250m scene
// with some padding. Y-axis is up (ignored in this top-down view).
const SCENE_MIN_X = -130;
const SCENE_MAX_X = 130;
const SCENE_MIN_Z = -130;
const SCENE_MAX_Z = 130;

const GNB_COLORS: Record<string, string> = {
  gNB_Macro_NW: '#e94560',
  gNB_Macro_SE: '#2196F3',
  gNB_Small_Plaza: '#4CAF50',
};

function pick<T extends { name: string; position: { x: number; z: number } }>(arr: T[]) {
  return arr;
}

interface Props {
  width?: number;
  height?: number;
  buildings: Building[];
  gnbs: GNB[];
  ues: UE[];
  selectedUeName: string | null;
  waypoints: Waypoint3D[];
  onAddWaypoint: (x: number, z: number) => void;
  onMoveWaypoint: (index: number, x: number, z: number) => void;
  onRemoveWaypoint: (index: number) => void;
}

export function TopDownMap({
  width = 520,
  height = 520,
  buildings,
  gnbs,
  ues,
  selectedUeName,
  waypoints,
  onAddWaypoint,
  onMoveWaypoint,
  onRemoveWaypoint,
}: Props) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [draggingIdx, setDraggingIdx] = useState<number | null>(null);

  const scaleX = (x: number) => ((x - SCENE_MIN_X) / (SCENE_MAX_X - SCENE_MIN_X)) * width;
  const scaleZ = (z: number) => height - ((z - SCENE_MIN_Z) / (SCENE_MAX_Z - SCENE_MIN_Z)) * height;
  const invertX = (px: number) => SCENE_MIN_X + (px / width) * (SCENE_MAX_X - SCENE_MIN_X);
  const invertZ = (py: number) => SCENE_MIN_Z + ((height - py) / height) * (SCENE_MAX_Z - SCENE_MIN_Z);

  const svgCoords = (ev: RMouseEvent<SVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, z: 0 };
    const rect = svg.getBoundingClientRect();
    return {
      x: invertX(ev.clientX - rect.left),
      z: invertZ(ev.clientY - rect.top),
    };
  };

  const handleBgClick = (ev: RMouseEvent<SVGRectElement>) => {
    if (!selectedUeName) return;
    const { x, z } = svgCoords(ev);
    onAddWaypoint(x, z);
  };

  const handleDragStart = (idx: number) => (ev: RMouseEvent<SVGCircleElement>) => {
    ev.stopPropagation();
    setDraggingIdx(idx);
  };

  const handleDrag = (ev: RMouseEvent<SVGElement>) => {
    if (draggingIdx === null) return;
    const { x, z } = svgCoords(ev);
    onMoveWaypoint(draggingIdx, x, z);
  };

  const handleDragEnd = () => {
    if (draggingIdx !== null) setDraggingIdx(null);
  };

  const handleWaypointContextMenu = (idx: number) => (ev: RMouseEvent<SVGCircleElement>) => {
    ev.preventDefault();
    ev.stopPropagation();
    onRemoveWaypoint(idx);
  };

  const selectedUe = selectedUeName ? ues.find((u) => u.name === selectedUeName) ?? null : null;

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      onMouseMove={handleDrag}
      onMouseUp={handleDragEnd}
      onMouseLeave={handleDragEnd}
      style={{ background: '#0d0d1a', border: '1px solid #1a1a3e', borderRadius: 6, display: 'block' }}
    >
      {/* Background (clickable to add waypoints) — must stay at bottom of z-order */}
      <rect x={0} y={0} width={width} height={height} fill="transparent" onClick={handleBgClick} />

      {/* All visual overlays — pointer-events:none so clicks fall through to bg rect.
          Waypoint handles are rendered AFTER this group and intentionally keep
          pointer events (for drag / right-click delete). */}
      <g style={{ pointerEvents: 'none' }}>
        {/* Grid lines every 50 m */}
        {[-100, -50, 0, 50, 100].map((v) => (
          <g key={`grid-${v}`}>
            <line x1={scaleX(v)} y1={0} x2={scaleX(v)} y2={height} stroke="#1f1f3a" strokeWidth={1} />
            <line x1={0} y1={scaleZ(v)} x2={width} y2={scaleZ(v)} stroke="#1f1f3a" strokeWidth={1} />
            <text x={scaleX(v) + 3} y={scaleZ(0) - 3} fill="#555" fontSize={9}>{v === 0 ? '' : `${v}m`}</text>
            <text x={scaleX(0) + 3} y={scaleZ(v) - 3} fill="#555" fontSize={9}>{v === 0 ? '' : `${v}m`}</text>
          </g>
        ))}

        {/* Axes */}
        <line x1={0} y1={scaleZ(0)} x2={width} y2={scaleZ(0)} stroke="#333" strokeWidth={1} />
        <line x1={scaleX(0)} y1={0} x2={scaleX(0)} y2={height} stroke="#333" strokeWidth={1} />

        {/* Buildings */}
        {pick(buildings).map((b) => {
          const w = Math.abs(b.size.x);
          const d = Math.abs(b.size.z);
          const px = scaleX(b.position.x - w / 2);
          const py = scaleZ(b.position.z + d / 2);
          const pw = (w / (SCENE_MAX_X - SCENE_MIN_X)) * width;
          const ph = (d / (SCENE_MAX_Z - SCENE_MIN_Z)) * height;
          return (
            <g key={b.name}>
              <rect x={px} y={py} width={pw} height={ph} fill="#38384a" stroke="#5a5a7a" strokeWidth={1} />
            </g>
          );
        })}

        {/* gNBs */}
        {pick(gnbs).map((g) => {
          const px = scaleX(g.position.x);
          const py = scaleZ(g.position.z);
          const color = GNB_COLORS[g.name] ?? '#E94560';
          return (
            <g key={g.name}>
              <circle cx={px} cy={py} r={150 / (SCENE_MAX_X - SCENE_MIN_X) * width / 2} fill={color} fillOpacity={0.08} stroke={color} strokeOpacity={0.5} strokeDasharray="4,4" />
              <circle cx={px} cy={py} r={6} fill={color} stroke="#fff" strokeWidth={1} />
              <text x={px + 9} y={py - 6} fill={color} fontSize={10} fontWeight={600}>{g.name}</text>
            </g>
          );
        })}

        {/* UEs (non-selected) */}
        {pick(ues).filter((u) => u.name !== selectedUeName).map((u) => {
          const px = scaleX(u.position.x);
          const py = scaleZ(u.position.z);
          return (
            <g key={u.name}>
              <circle cx={px} cy={py} r={4} fill="#FF9800" stroke="#fff" strokeWidth={0.5} />
              <text x={px + 6} y={py + 3} fill="#aaa" fontSize={9}>{u.name}</text>
            </g>
          );
        })}

        {/* Selected UE highlight */}
        {selectedUe && (
          <g>
            <circle cx={scaleX(selectedUe.position.x)} cy={scaleZ(selectedUe.position.z)} r={7} fill="#FFC107" stroke="#fff" strokeWidth={1.5} />
            <text x={scaleX(selectedUe.position.x) + 10} y={scaleZ(selectedUe.position.z) + 4} fill="#FFC107" fontSize={11} fontWeight={700}>
              {selectedUe.name}
            </text>
          </g>
        )}

        {/* Waypoint polyline */}
        {waypoints.length > 1 && (
          <polyline
            points={waypoints.map((w) => `${scaleX(w.x)},${scaleZ(w.z)}`).join(' ')}
            fill="none"
            stroke="#4CAF50"
            strokeWidth={2}
            strokeDasharray="6,3"
          />
        )}

        {/* Line from UE current pos to waypoint[0] */}
        {selectedUe && waypoints.length > 0 && (
          <line
            x1={scaleX(selectedUe.position.x)}
            y1={scaleZ(selectedUe.position.z)}
            x2={scaleX(waypoints[0].x)}
            y2={scaleZ(waypoints[0].z)}
            stroke="#4CAF50"
            strokeWidth={1}
            strokeDasharray="2,4"
            strokeOpacity={0.4}
          />
        )}
      </g>

      {/* Waypoint handles */}
      {waypoints.map((w, i) => {
        const px = scaleX(w.x);
        const py = scaleZ(w.z);
        return (
          <g key={`wp-${i}`}>
            <circle
              cx={px}
              cy={py}
              r={8}
              fill={draggingIdx === i ? '#FFD54F' : '#4CAF50'}
              stroke="#fff"
              strokeWidth={2}
              onMouseDown={handleDragStart(i)}
              onContextMenu={handleWaypointContextMenu(i)}
              style={{ cursor: 'grab' }}
            />
            <text x={px} y={py + 3} textAnchor="middle" fill="#fff" fontSize={9} fontWeight={700} pointerEvents="none">
              {i + 1}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
