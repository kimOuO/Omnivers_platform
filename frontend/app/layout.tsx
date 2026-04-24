import type { ReactNode } from 'react';
import Link from 'next/link';
import '@/styles/globals.css';

export const metadata = {
  title: 'Omniver Platform',
  description: 'RAN Digital Twin control and observation platform',
};

interface Props {
  children: ReactNode;
}

export default function RootLayout({ children }: Props) {
  return (
    <html lang="zh-TW">
      <body>
        <div className="container">
          <h1>Omniver Platform</h1>
          <nav className="topnav">
            <Link href="/">Dashboard</Link>
            <Link href="/trajectory">Trajectory</Link>
            <Link href="/signals">Signal History</Link>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
