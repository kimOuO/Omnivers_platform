# 🌐 Omniver Platform - Frontend

Next.js (App Router) + React + TypeScript 前端應用，嚴守 `../frontend_rule.md` 架構規範。

---

## 概述

Omniver 前端提供：

- 📊 **RAN 場景儀表板**：查看基站、使用者設備、訊號覆蓋
- 🎯 **場景配置**：創建和管理場景、基站、UE 設定
- 📈 **訊號監控**：實時 RSRP/SINR 指標顯示
- 🛠️ **軌跡編輯**：定義和編輯 UE 移動路徑
- 🎮 **3D 互動**：與虛擬顯示同步

---

## 啟動方式

### 透過 Docker Compose（推薦）

```bash
# 啟動所有服務，包括前端
docker compose up -d

# 單獨重啟前端
docker compose restart frontend
```

### 訪問前端

```
http://localhost:3001
```

### 檢查前端日誌

```bash
# 實時日誌
docker compose logs -f frontend

# 查看錯誤
docker compose logs frontend | grep ERROR
```

---

## 專案結構

```
frontend/
├── Dockerfile              前端容器定義
├── next.config.js         Next.js 配置
├── tsconfig.json          TypeScript 配置
├── package.json           NPM 依賴清單
├── .eslintrc.json        ESLint 規則
│
├── app/                  Next.js App Router（路由和佈局）
│   ├── layout.tsx        根佈局
│   ├── page.tsx          首頁
│   ├── (dashboard)/      儀表板群組
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── scenes/       場景頁面
│   │   └── signals/      訊號頁面
│   └── api/              API 路由（如需）
│
├── components/           React 元件（純 UI 渲染）
│   ├── common/          通用元件（Button、Card 等）
│   ├── dashboard/       儀表板元件
│   ├── scene/           場景管理元件
│   └── signal/          訊號顯示元件
│
├── hooks/                Custom React Hooks
│   ├── base/            基礎 hooks（useAsync、useLocalStorage）
│   └── feature/         功能 hooks（useSceneState、useSignalData）
│
├── services/             資料訪問層（所有 API 呼叫）
│   ├── clients/         API 客戶端（axios、fetch）
│   ├── api/             API 服務（SceneService、SignalService）
│   ├── workflows/       複雜工作流程
│   └── server/          伺服器端服務（如需）
│
├── types/                TypeScript 型別定義
│   ├── api.ts           API 回應型別
│   ├── domain.ts        領域模型
│   ├── async.ts         非同步狀態型別（AsyncState<T>）
│   └── errors.ts        錯誤型別
│
├── config/              靜態配置
│   ├── env.ts           環境配置
│   ├── api.ts           API 端點配置
│   └── constants.ts     常數定義
│
├── styles/              全域樣式
│   ├── globals.css      全域樣式
│   └── theme.css        主題令牌
│
├── public/              靜態資產
│   ├── images/          圖片
│   └── icons/           圖標
│
├── .env.example         環境變數範例
├── package-lock.json    NPM 版本鎖定
└── README.md           本檔案
```

---

## 架構邊界

嚴守 `../frontend_rule.md` 定義的邊界：

```
┌─────────────────────────────────────────────────┐
│ app/                                             │
│ (路由、頁面、伺服器編排)                         │
│ ⬇️ 可 import                                   │
│ components/, hooks/, services/, types/, config/ │
└─────────────────────────────────────────────────┘
        ⬇️
┌─────────────────────────────────────────────────┐
│ components/                                     │
│ (純 UI 渲染，無狀態邏輯)                       │
│ ⬇️ 可 import                                   │
│ hooks/ (feature only), types/, config/         │
└─────────────────────────────────────────────────┘
        ⬇️
┌─────────────────────────────────────────────────┐
│ hooks/ (base/ + feature/)                       │
│ (狀態管理、互動邏輯、副作用)                   │
│ ⬇️ 可 import                                   │
│ services/, types/, config/                     │
└─────────────────────────────────────────────────┘
        ⬇️
┌─────────────────────────────────────────────────┐
│ services/                                       │
│ (資料訪問層，不得 import components/hooks/)    │
│ ⬇️ 可 import                                   │
│ types/, config/                                │
└─────────────────────────────────────────────────┘
```

### Import 禁區

```typescript
// ❌ 禁止：services 導入 components 或 hooks
import Button from '@/components/Button';           // 違反！
import useAsync from '@/hooks/base/useAsync';       // 違反！

// ✅ 正確：services 只導入 types 和 config
import { SceneResponse } from '@/types/api';       // 正確
import { API_BASE_URL } from '@/config/env';       // 正確
```

---

## 容器配置

### docker-compose.yml 中的 Frontend 設定

```yaml
frontend:
  image: node:20-alpine
  container_name: omniver_frontend
  working_dir: /app
  command: sh -c "npm install && npm run dev"
  ports:
    - "3001:3000"  # 主機:容器
  environment:
    # 環境變數在編譯時進行評估
    NEXT_PUBLIC_API_BASE_URL: http://localhost:8001
    NEXT_PUBLIC_WS_URL: ws://localhost:8001/api/v0.1/RAN/UE/live
  volumes:
    - ./frontend:/app                  # 熱重載
    - frontend_node_modules:/app/node_modules
    - frontend_next_cache:/app/.next
  depends_on:
    - backend
  restart: unless-stopped
```

**注意**：
- 環境變數必須以 `NEXT_PUBLIC_` 前綴（瀏覽器可訪問）
- 熱重載啟用（修改代碼自動重新整理）
- node_modules 使用 Docker volume（提高性能）

---

## 開發

### 進入容器進行開發

```bash
# 進入容器
docker exec -it omniver_frontend sh

# 安裝依賴
npm install

# 執行 linting
npm run lint

# 類型檢查
npm run typecheck

# 構建
npm run build
```

### 本地開發（不用 Docker）

```bash
# 安裝依賴
npm install

# 啟動開發伺服器
npm run dev
# 訪問 http://localhost:3000

# 代碼檢查
npm run lint

# 類型檢查
npm run typecheck
```

### 檢查日誌

```bash
# 實時日誌
docker compose logs -f frontend

# 構建日誌
docker compose logs frontend | grep -i "next"

# 錯誤日誌
docker compose logs frontend | grep -i "error"
```

---

## API 整合

### 連接到 Backend

前端透過環境變數配置 Backend URL：

```typescript
// config/env.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
// 在 docker-compose.yml 中設定為 http://localhost:8001
```

### API 呼叫示例

```typescript
// services/api/sceneService.ts
import axios from 'axios';
import { API_BASE_URL } from '@/config/env';

export const sceneService = {
  // 查詢場景狀態
  async getSceneState() {
    const response = await axios.post(
      `${API_BASE_URL}/api/v0.1/RAN/Scene/SceneStateReader/read`,
      {}
    );
    return response.data;
  },

  // 構建場景
  async buildScene(name: string) {
    const response = await axios.post(
      `${API_BASE_URL}/api/v0.1/RAN/Scene/SceneBuilder/create`,
      { name, buildings: 6, gnbs: 3, ues: 5 }
    );
    return response.data;
  }
};
```

### 在頁面中使用

```typescript
// app/(dashboard)/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { sceneService } from '@/services/api/sceneService';

export default function DashboardPage() {
  const [state, setState] = useState(null);

  useEffect(() => {
    sceneService.getSceneState().then(setState);
  }, []);

  return <div>{/* 渲染場景狀態 */}</div>;
}
```

---

## 類型系統

### AsyncState 模式

```typescript
// types/async.ts
export interface AsyncState<T> {
  status: 'idle' | 'loading' | 'success' | 'error';
  data?: T;
  error?: string;
}
```

### 使用 AsyncState

```typescript
// hooks/feature/useSceneState.ts
import { AsyncState } from '@/types/async';
import { sceneService } from '@/services/api/sceneService';

export function useSceneState(): AsyncState<SceneData> {
  const [state, setState] = useState<AsyncState<SceneData>>({ status: 'idle' });

  useEffect(() => {
    setState({ status: 'loading' });
    sceneService.getSceneState()
      .then(data => setState({ status: 'success', data }))
      .catch(error => setState({ status: 'error', error: error.message }));
  }, []);

  return state;
}
```

---

## 問題排除

### 無法連接到 Backend

```bash
# 檢查環境變數
docker exec omniver_frontend env | grep NEXT_PUBLIC

# 測試 API 連接
docker exec omniver_frontend curl http://backend:8001/api/v0.1/RAN/status

# 查看瀏覽器控制台
# F12 → Console 檢查 CORS 或網路錯誤
```

### 熱重載不工作

```bash
# 重啟前端
docker compose restart frontend

# 檢查 volume 掛載
docker inspect omniver_frontend | grep Mounts
```

### NPM 依賴問題

```bash
# 清理依賴快取
docker exec omniver_frontend rm -rf node_modules package-lock.json

# 重新安裝
docker compose restart frontend
```

### TypeScript 錯誤

```bash
# 執行類型檢查
docker exec omniver_frontend npm run typecheck

# 查看詳細錯誤
docker exec omniver_frontend npx tsc --noEmit
```

---

## 性能最佳化

### Next.js 配置

- 啟用 Image 優化
- Code splitting 自動化
- 靜態生成（如適用）
- ISR（增量靜態再生）

### 監控

```bash
# 檢查前端資源使用
docker stats omniver_frontend

# 構建大小
docker exec omniver_frontend npm run build
# 查看 .next/static/ 大小
```

---

## 維護

### 依賴更新

```bash
# 檢查過期依賴
docker exec omniver_frontend npm outdated

# 更新依賴
docker exec omniver_frontend npm update

# 更新主要版本（謹慎）
docker exec omniver_frontend npm install <package>@latest
```

### 重建容器

```bash
# 完全重建（不使用快取）
docker compose build --no-cache frontend

# 重啟服務
docker compose up -d frontend
```

---

## 相關資源

- **主文檔**：../README.md
- **Docker 操作**：../DOCKER_QUICKSTART.md
- **架構規範**：../frontend_rule.md（必讀）
- **Backend API**：../docs/ingest_api.md
- **場景配置**：../SCENE_CONFIG_GUIDE.md

---

最後更新：2026-04-25
