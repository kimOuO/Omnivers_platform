# 前端可編輯字段規範

## 概述
為了維護數據完整性，前端只能編輯 USD 標準規範的字段。系統會自動忽略不在許可清單的字段。

## Building（建築物）

**可編輯字段：**
- `position` [x, y, z] 或 `pos_x`, `pos_y`, `pos_z` — 空間位置
- `size` [x, y, z] 或 `size_x`, `size_y`, `size_z` — 立方體尺寸
- `color` [r, g, b] 或 `color_r`, `color_g`, `color_b` — RGB顏色 (0-1)
- `rotation_xyz_deg` [x, y, z] 或 `rot_x`, `rot_y`, `rot_z` — 旋轉角度 (度)
- `material` — Sionna 材質 (如 "itu_urban", "itu_suburban")
- `usd_path` — USD模型引用路徑
- `target_height_m` — 參考高度（用於縮放）

**禁止編輯字段：**
- `name` — 唯一識別，作為查詢鍵
- `building_uuid` — 系統ID
- `scene_id` — 場景ID
- `created_at`, `updated_at` — 時間戳

**範例請求：**
```json
{
  "name": "Building_A",
  "position": [100, 0, 50],
  "size": [60, 80, 40],
  "color": [0.8, 0.6, 0.4],
  "rotation_xyz_deg": [0, 0, 0],
  "material": "itu_urban",
  "usd_path": "/path/to/model.usda"
}
```

## Obstacle（障礙物）

**可編輯字段：**
- `position` [x, y, z] 或 `pos_x`, `pos_y`, `pos_z`
- `size` [x, y, z] 或 `size_x`, `size_y`, `size_z`
- `color` [r, g, b] 或 `color_r`, `color_g`, `color_b`
- `scale` [x, y, z] 或 `scale_x`, `scale_y`, `scale_z` — 幾何縮放
- `material`
- `usd_path`

**禁止編輯字段：**
- `name`
- `obstacle_uuid`
- `scene_id`
- `created_at`, `updated_at`

## gNB（基地台）

**可編輯字段：**
- `position` [x, y, z] — 基地台位置
- `color` [r, g, b] — 顯示顏色
- `frequency_ghz` — 頻率 (GHz)
- `bandwidth_mhz` — 帶寬 (MHz)
- `power_dbm` — 發射功率 (dBm)
- `target_height_m` — 天線高度

## UE（使用者設備）

**可編輯字段：**
- `position` [x, y, z] — 起始位置
- `color` [r, g, b] — 顯示顏色
- `waypoints` — 移動路徑點陣列
- `speed_mps` — 移動速度 (m/s)
- `loop` — 是否循環 (bool)

## 驗證行為

- ✅ 允許的字段會被接受並更新到數據庫
- ⚠️ 禁止字段被**靜默忽略**（不會返回錯誤）
- 🔄 更新後自動觸發 Omniverse 場景重建

## 前端實現建議

```javascript
// 允許的字段清單
const EDITABLE_BUILDING_FIELDS = [
  'position', 'pos_x', 'pos_y', 'pos_z',
  'size', 'size_x', 'size_y', 'size_z',
  'color', 'color_r', 'color_g', 'color_b',
  'rotation_xyz_deg', 'rot_x', 'rot_y', 'rot_z',
  'material', 'usd_path', 'target_height_m'
];

// 過濾前端表單，只送出允許的字段
function prepareUpdatePayload(formData) {
  const payload = { name: formData.name };
  EDITABLE_BUILDING_FIELDS.forEach(field => {
    if (field in formData) {
      payload[field] = formData[field];
    }
  });
  return payload;
}
```
