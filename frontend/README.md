# Omniver Platform — Frontend

Next.js (App Router) + React + TypeScript (strict)。嚴守 `../frontend_rule.md`。

## 架構邊界

```
app/        routing + composition + server orchestration (NO fetch/axios)
components/ UI rendering only
hooks/      state + interaction + client effects (base/ + feature/)
services/   all data access (clients/ + api/ + client/ + server/ + workflows/)
types/      shared types (ApiError, AsyncState<T>, domain DTOs)
config/     static config (no runtime logic)
styles/     globals.css + theme tokens
public/     static assets
```

## Import 邊界（ESLint 強制）

- `app/` → `components/`, `hooks/`, `services/`, `types/`, `config/`, `styles/`
- `components/` → `hooks/` (feature only), `types/`, `config/`
- `hooks/` → `services/`, `types/`, `config/`
- `services/` → `types/`, `config/`（不得 import components / hooks）

## 開發

```bash
cp .env.example .env.local
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run typecheck
```
