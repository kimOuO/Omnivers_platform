import type { GNB } from '@/types';

function fmtPos(x: number, y: number, z: number): string {
  return `(${x.toFixed(0)}, ${y.toFixed(0)}, ${z.toFixed(0)})`;
}

interface Props {
  gnbs: GNB[];
}

export function GNBTable({ gnbs }: Props) {
  if (gnbs.length === 0) return <p>No gNBs</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Position</th>
          <th>Freq (GHz)</th>
          <th>Power (dBm)</th>
          <th>Active</th>
        </tr>
      </thead>
      <tbody>
        {gnbs.map((g) => (
          <tr key={g.name}>
            <td>{g.name}</td>
            <td>{fmtPos(g.position.x, g.position.y, g.position.z)}</td>
            <td>{(g.freqMhz / 1000).toFixed(1)}</td>
            <td>{g.powerDbm}</td>
            <td>{g.active ? 'Yes' : 'No'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
