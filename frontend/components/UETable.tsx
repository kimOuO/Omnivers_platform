import type { UE } from '@/types';

function rsrpClass(v: number | null): string {
  if (v == null) return '';
  if (v > -80) return 'rsrp-good';
  if (v > -100) return 'rsrp-mid';
  return 'rsrp-bad';
}

function fmtPos(x: number, y: number, z: number): string {
  return `(${x.toFixed(0)}, ${y.toFixed(0)}, ${z.toFixed(0)})`;
}

function fmtNum(v: number | null, unit = ''): string {
  return v == null ? '-' : `${v.toFixed(1)}${unit}`;
}

interface Props {
  ues: UE[];
}

export function UETable({ ues }: Props) {
  if (ues.length === 0) return <p>No UEs</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Position</th>
          <th>Serving Cell</th>
          <th>RSRP (dBm)</th>
          <th>SINR (dB)</th>
        </tr>
      </thead>
      <tbody>
        {ues.map((ue) => (
          <tr key={ue.name}>
            <td>{ue.name}</td>
            <td>{fmtPos(ue.position.x, ue.position.y, ue.position.z)}</td>
            <td className="serving">{ue.servingCell ?? '-'}</td>
            <td className={rsrpClass(ue.rsrpDbm)}>{fmtNum(ue.rsrpDbm)}</td>
            <td>{fmtNum(ue.sinrDb)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
