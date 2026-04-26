# RAN 數字孿生場景控制手冊

## 📋 快速開始

### 查看所有對象
```bash
cd /home/mitlab/XAPP_DT/Omnivers_platform
python3 configure_scene.py list
```

### 修改配置並應用
```bash
# 改 Building_1 高度為 500m
python3 configure_scene.py building --name Building_1 --height 500

# 改 gNB 高度為 500m
python3 configure_scene.py gnb --name gNB_Macro_NW --height 500

# 改 UE 速度為 20 m/s
python3 configure_scene.py ue --name UE_1 --speed 20

# 應用所有變更（清除緩存、重建場景）
python3 configure_scene.py apply
```

---

## 🏢 Buildings（建築物）

### 可調參數
| 參數 | 類型 | 說明 | 例子 |
|------|------|------|------|
| `--height` | float | 目標高度（米） | `--height 400` |
| `--position` | [x,y,z] | 3D 位置 | `--position -300 0 0` |
| `--color` | [R,G,B] | 顏色（0-1 範圍） | `--color 0.5 0.7 0.9` |

### 操作示例

**改 Building_1 高度**
```bash
python3 configure_scene.py building --name Building_1 --height 300
```

**改 Building_2 位置**
```bash
python3 configure_scene.py building --name Building_2 --position 400 0 100
```

**改顏色**
```bash
python3 configure_scene.py building --name Building_1 --color 1.0 0.0 0.0  # 紅色
```

### 目前配置

| 建築 | 高度 | 位置 | 說明 |
|------|------|------|------|
| Building_1 | 400m | [-300, 0, 0] | Brownstone 3D |
| Building_2 | 400m | [300, 0, 0] | Brownstone 3D |

---

## 📡 gNBs（基站）

### 可調參數
| 參數 | 類型 | 說明 | 例子 |
|------|------|------|------|
| `--height` | float | 視覺高度（米） | `--height 500` |
| `--power` | float | 發射功率（dBm） | `--power 43` |
| `--frequency` | float | 中心頻率（GHz） | `--frequency 3.5` |
| `--bandwidth` | float | 帶寬（MHz） | `--bandwidth 100` |

### 操作示例

**改基站高度**
```bash
python3 configure_scene.py gnb --name gNB_Macro_NW --height 600
```

**改基站功率**
```bash
python3 configure_scene.py gnb --name gNB_Macro_NW --power 45
```

**同時改多個參數**（分開執行）
```bash
python3 configure_scene.py gnb --name gNB_Macro_NW --height 500
python3 configure_scene.py gnb --name gNB_Macro_NW --power 45
python3 configure_scene.py apply
```

### 目前配置

| gNB | 高度 | 功率 | 頻率 | 帶寬 | 位置 |
|-----|------|------|------|------|------|
| gNB_Macro_NW | 400m | 43 dBm | 3.5 GHz | 100 MHz | [200, 50, 200] |
| gNB_Macro_SE | 400m | 40 dBm | 3.5 GHz | 100 MHz | [-200, 45, -200] |
| gNB_Micro_Central | 400m | 20 dBm | 2.6 GHz | 20 MHz | [0, 30, 0] |

---

## 👤 UEs（用戶設備/角色）

### 可調參數
| 參數 | 類型 | 說明 | 例子 |
|------|------|------|------|
| `--height` | float | 角色身高（米） | `--height 50` |
| `--speed` | float | 移動速度（m/s） | `--speed 15` |
| `--position` | [x,y,z] | 起始位置 | `--position 0 0 0` |

### 操作示例

**改 UE 身高**
```bash
python3 configure_scene.py ue --name UE_Handover_Path --height 40
```

**改 UE 移動速度**
```bash
python3 configure_scene.py ue --name UE_3 --speed 10
```

**改 UE 起始位置**
```bash
python3 configure_scene.py ue --name UE_2 --position 150 0 150
```

### 目前配置

| UE | 身高 | 速度 | 位置 | 說明 |
|----|------|------|------|------|
| UE_Handover_Path | 34m | 10 m/s | [0, 0, 0] | 往返路徑（5點） |
| UE_2 | 34m | 0 m/s | [100, 0, 0] | 靜止 |
| UE_3 | 34m | 5 m/s | [0, 0, 100] | 移動路徑（3點） |
| UE_4 | 34m | 15 m/s | [-100, 0, 100] | 往返路徑（3點） |
| UE_5 | 34m | 8 m/s | [150, 0, 150] | 大型往返路徑（5點） |

---

## 🔧 進階：直接編輯配置

如果需要批量修改，可以直接編輯 JSON：

```bash
# 編輯配置文件
nano scene_config.json

# 驗證 JSON 語法
python3 -m json.tool scene_config.json > /dev/null && echo "✓ 有效"

# 應用變更
python3 configure_scene.py apply
```

### 配置文件結構

```json
{
  "buildings": [
    {
      "name": "Building_1",
      "position": [-300, 0, 0],
      "target_height_m": 400,
      "color": [0.5, 0.7, 0.9],
      "rotation_xyz_deg": [-90, 0, 0],
      "usd": "path/to/Brownstone01_Building.usda"
    }
  ],
  "obstacles": [
    {
      "name": "Building_3",
      "position": [-100, 0, -80],
      "size": [120, 20, 100],
      "color": [0.72, 0.36, 0.28]
    }
  ],
  "gnbs": [
    {
      "name": "gNB_Macro_NW",
      "position": [200, 50, 200],
      "target_height_m": 400,
      "frequency_ghz": 3.5,
      "power_dbm": 43,
      "bandwidth_mhz": 100,
      "active": true
    }
  ],
  "ues": [
    {
      "name": "UE_1",
      "position": [0, 0, 0],
      "target_height_m": 34.0,
      "speed_mps": 10.0,
      "waypoints": [[0,0,0], [50,0,50], [100,0,100]]
    }
  ]
}
```

---

## ⚡ 快速命令參考

```bash
# 查看所有對象
python3 configure_scene.py list

# Building 操作
python3 configure_scene.py building --name Building_1 --height 500
python3 configure_scene.py building --name Building_2 --position 400 0 0

# gNB 操作
python3 configure_scene.py gnb --name gNB_Macro_NW --height 600
python3 configure_scene.py gnb --name gNB_Macro_NW --power 45
python3 configure_scene.py gnb --name gNB_Macro_NW --frequency 2.6

# UE 操作
python3 configure_scene.py ue --name UE_1 --speed 20
python3 configure_scene.py ue --name UE_2 --height 50
python3 configure_scene.py ue --name UE_3 --position 200 0 200

# 應用所有變更（重建場景）
python3 configure_scene.py apply
```

---

## 🔄 工作流程

1. **修改配置**
   ```bash
   python3 configure_scene.py building --name Building_1 --height 500
   ```

2. **查看變更**
   ```bash
   python3 configure_scene.py list
   ```

3. **應用到場景**
   ```bash
   python3 configure_scene.py apply
   ```

4. **在 VNC 查看效果**
   - 訪問 `http://localhost:6080`
   - 觀察場景中的變化

---

## 📌 重要說明

### 為什麼不需要重啟 container？

配置修改工具使用 **sed** 方式保持文件 inode，Docker volume mount 仍然有效：
- ✅ 修改配置（sed 保持 inode）
- ✅ 清除 Kit 緩存 
- ✅ 重建場景
- ❌ 無需重啟 container
- ❌ 無需重建 Docker image

### 修改後多久生效？

配置修改後運行 `apply` 命令：
```bash
python3 configure_scene.py apply
```

大約 10-15 秒後在 VNC 中可以看到變更。

---

## 🐛 故障排除

### 問題：修改後看不到變化
**解決方案：**
```bash
# 清除緩存並重新應用
docker exec omniver_kit rm -rf /root/.local/share/ov/data/Kit/ran_server
python3 configure_scene.py apply
```

### 問題：JSON 語法錯誤
**檢查：**
```bash
python3 -m json.tool scene_config.json
```

如果有錯誤會顯示。編輯 `scene_config.json` 修正後再試。

### 問題：curl 連線失敗
**檢查 Kit 是否運行：**
```bash
curl http://localhost:8080/health
docker logs omniver_kit | tail -20
```

---

## 📞 常見問題

**Q: 可以改顏色嗎？**
A: Building 和 gNB 都支持 RGB 顏色參數。

**Q: UE 的路徑點怎麼改？**
A: 目前需要直接編輯 `scene_config.json` 中的 `waypoints` 陣列。

**Q: 改了參數但沒生效？**
A: 記得執行 `python3 configure_scene.py apply` 來應用變更。

---

最後更新：2026-04-26
