# Use Case 時序圖 (PlantUML)

5 個 `.puml` 檔，每個對應前端一個 use case。

| 檔案 | Use Case |
|---|---|
| `UC01_dashboard_live_view.puml` | 操作員查看 Dashboard 即時狀態（初始 layout + 每秒 poll UE） |
| `UC02_scene_build_clear.puml`   | 操作員按下 Build Scene / Clear Scene 按鈕 |
| `UC03_animation_control.puml`   | 操作員按下 Start Animation / Stop Animation |
| `UC04_trajectory_edit.puml`     | 操作員在 `/trajectory` 頁編輯 waypoints 並 Apply |
| `UC05_signal_ingest.puml`       | 外部模擬 RAN 推訊號 → DB + Kit + 前端 Dashboard 更新 |

## 命名階層

```
omniver_platform [Platform]
└── ran_dt [System]
    ├── frontend_view [Module]     — Next.js 頁面 + feature hook
    ├── backend_scene [Module]     — Scene / Animation 控制 actor
    ├── backend_ue [Module]        — UE 讀取 / 控制 actor
    └── backend_ingest [Module]    — 外部訊號 ingest actor
External:
  - kit_render_server  (Omniverse Kit, host GPU)
  - external_ran_sim   (Sionna DU，未來接入)
```

## 渲染方式

- **VS Code**：裝 `PlantUML` extension → Alt+D 預覽
- **線上**：複製檔案內容到 <https://www.plantuml.com/plantuml/>
- **CLI**：`plantuml -tpng UC*.puml`（產生 PNG）
- **整合到文件**：MkDocs / Docusaurus 有 plantuml plugin

## 設計原則

- 每張圖只畫**一個 use case**，避免雜訊
- Actor 名稱跟程式碼 1:1 對齊（`UEController`, `SignalIngestor`, `TopDownMap` 等）
- `autonumber 1.1 / 1.2 / ...` 分組編號
- `activate / deactivate` 表示生命期
- `note over ...` 標注 Kit command queue 非同步執行的事實（下一幀才真正動 USD）
