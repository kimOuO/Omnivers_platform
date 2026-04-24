# 📋 scene_config.json 生成指南

詳細說明如何生成和自訂場景配置文件。

---

## 🎯 快速生成

### 方式 1：使用已有的範例（推薦）

```bash
# 我已經為你創建了一個完整的範例
ls -lh /home/mitlab/Omniverse/scene_config.json

# 查看內容
cat /home/mitlab/Omniverse/scene_config.json | python3 -m json.tool

# 編輯自訂
nano /home/mitlab/Omniverse/scene_config.json
```

### 方式 2：從頭開始創建

```bash
cat > /home/mitlab/Omniverse/scene_config.json << 'EOF'
{
  "environment": {
    "usd": "file:///path/to/environment.usd"
  },
  "ground": {
    "material": "grass"
  },
  "buildings": [],
  "gnbs": [],
  "ues": [],
  "metadata": {
    "version": "1.0"
  }
}
EOF
```

---

## 📐 配置文件結構詳解

### 根層級 (Root Level)

```json
{
  "environment": {},      ← 環境資源
  "ground": {},          ← 地面設定
  "buildings": [],       ← 建築物列表
  "gnbs": [],           ← 基站列表
  "ues": [],            ← UE（用戶設備）列表
  "metadata": {}        ← 元數據（可選）
}
```

---

## 🏗️ 詳細結構

### 1️⃣ environment（環境）

背景環境資源的參考。

```json
"environment": {
  "description": "背景環境資源",
  "usd": "file:///path/to/environment.usd"
}
```

**參數：**
| 參數 | 型別 | 說明 | 例子 |
|------|------|------|------|
| `usd` | String | USD 文件路徑 | `file:///assets/environment.usd` |

**說明：** 若無背景資源，可留空或設為 `""` 字串。

---

### 2️⃣ ground（地面）

地面材質和大小。

```json
"ground": {
  "material": "grass",
  "size": [1000, 1000]
}
```

**參數：**
| 參數 | 型別 | 說明 | 例子 |
|------|------|------|------|
| `material` | String | 材質名稱 | `grass`, `asphalt`, `concrete` |
| `size` | Array[2] | [寬, 深] 米 | `[1000, 1000]` |

**預設值：**
```json
{
  "material": "grass",
  "size": [1000, 1000]
}
```

---

### 3️⃣ buildings（建築物）

場景中的建築物。

```json
"buildings": [
  {
    "name": "Building_1",
    "description": "辦公大樓",
    "position": [0, 0, 0],
    "size": [50, 30, 100],
    "material": "concrete",
    "usd": "file:///path/to/building.usd"
  }
]
```

**參數：**
| 參數 | 型別 | 必需 | 說明 | 例子 |
|------|------|------|------|------|
| `name` | String | ✓ | 建築物唯一名稱 | `Building_1` |
| `description` | String | | 描述 | `辦公大樓 A` |
| `position` | Array[3] | ✓ | [X, Y, Z] 座標 | `[0, 0, 0]` |
| `size` | Array[3] | ✓ | [寬, 深, 高] 米 | `[50, 30, 100]` |
| `material` | String | | 材質 | `concrete`, `steel`, `glass` |
| `usd` | String | | USD 文件路徑 | `file:///assets/building.usd` |

**示例：5 棟不同建築物**

```json
"buildings": [
  {
    "name": "Office_A",
    "position": [0, 0, 0],
    "size": [50, 30, 100],
    "material": "concrete"
  },
  {
    "name": "Factory",
    "position": [100, 50, 0],
    "size": [80, 60, 30],
    "material": "steel"
  },
  {
    "name": "Residential",
    "position": [-100, -80, 0],
    "size": [120, 100, 20],
    "material": "brick"
  },
  {
    "name": "Mall",
    "position": [50, -100, 0],
    "size": [60, 50, 40],
    "material": "glass"
  },
  {
    "name": "DataCenter",
    "position": [150, 150, 0],
    "size": [40, 40, 50],
    "material": "concrete"
  }
]
```

---

### 4️⃣ gnbs（基站）

5G/NR 基站。

```json
"gnbs": [
  {
    "name": "gNB_Macro_1",
    "description": "宏基站",
    "position": [200, 200, 50],
    "frequency_ghz": 3.5,
    "power_dbm": 43,
    "bandwidth_mhz": 100,
    "active": true
  }
]
```

**參數：**
| 參數 | 型別 | 必需 | 說明 | 有效範圍 |
|------|------|------|------|---------|
| `name` | String | ✓ | 基站唯一名稱 | `gNB_Macro_1` |
| `description` | String | | 描述 | `宏基站` |
| `position` | Array[3] | ✓ | [X, Y, Z] 座標 | 任何數字 |
| `frequency_ghz` | Float | ✓ | 頻率 (GHz) | 0.6-6.0 |
| `power_dbm` | Float | ✓ | 發射功率 (dBm) | 0-46 |
| `bandwidth_mhz` | Float | ✓ | 頻寬 (MHz) | 5-400 |
| `active` | Boolean | | 是否激活 | `true` / `false` |

**常見頻率和帶寬組合：**
```json
"gnbs": [
  {
    "name": "gNB_n78",
    "position": [200, 200, 50],
    "frequency_ghz": 3.5,
    "power_dbm": 43,
    "bandwidth_mhz": 100
  },
  {
    "name": "gNB_n77",
    "position": [-200, -200, 50],
    "frequency_ghz": 3.8,
    "power_dbm": 40,
    "bandwidth_mhz": 100
  },
  {
    "name": "gNB_n71",
    "position": [0, 0, 30],
    "frequency_ghz": 0.617,
    "power_dbm": 38,
    "bandwidth_mhz": 20
  },
  {
    "name": "gNB_n41",
    "position": [100, 100, 40],
    "frequency_ghz": 2.5,
    "power_dbm": 36,
    "bandwidth_mhz": 100
  }
]
```

**5G FR1 頻段參考：**
| 頻段 | 頻率範圍 | 建議帶寬 | 用途 |
|------|---------|---------|------|
| n71 | 617-653 MHz | 20 MHz | 廣覆蓋 |
| n78 | 3.4-3.8 GHz | 100 MHz | 都市密集 |
| n79 | 4.4-5.0 GHz | 100+ MHz | 熱點覆蓋 |

---

### 5️⃣ ues（用戶設備）

移動設備。

```json
"ues": [
  {
    "name": "UE_1",
    "description": "行人",
    "prim_path": "/World/UE_1",
    "position": [0, 0, 1.7],
    "speed": 5.0,
    "trajectory": {
      "waypoints": [
        [0, 0, 1.7],
        [100, 100, 1.7],
        [0, 0, 1.7]
      ],
      "loop": true
    }
  }
]
```

**參數：**
| 參數 | 型別 | 必需 | 說明 | 例子 |
|------|------|------|------|------|
| `name` | String | ✓ | UE 唯一名稱 | `UE_1` |
| `description` | String | | 描述 | `行人`, `車輛` |
| `prim_path` | String | ✓ | USD Prim 路徑 | `/World/UE_1` |
| `position` | Array[3] | ✓ | 起始位置 [X, Y, Z] | `[0, 0, 1.7]` |
| `speed` | Float | ✓ | 移動速度 (m/s) | 0 (靜止) - 50 |
| `trajectory` | Object | | 軌跡（可選） | 見下 |

**軌跡 (trajectory) 子參數：**
```json
"trajectory": {
  "waypoints": [
    [X1, Y1, Z1],
    [X2, Y2, Z2],
    ...
  ],
  "loop": true
}
```

| 參數 | 說明 |
|------|------|
| `waypoints` | 路點列表 (座標陣列) |
| `loop` | 是否循環 (`true`/`false`) |

**不同場景的 UE 配置：**

**場景 1：靜止 UE（無軌跡）**
```json
{
  "name": "UE_Static",
  "position": [0, 0, 1.7],
  "speed": 0,
  "trajectory": null
}
```

**場景 2：簡單直線移動**
```json
{
  "name": "UE_Linear",
  "position": [0, 0, 1.7],
  "speed": 10.0,
  "trajectory": {
    "waypoints": [
      [0, 0, 1.7],
      [100, 0, 1.7],
      [200, 0, 1.7]
    ],
    "loop": false
  }
}
```

**場景 3：往返運動**
```json
{
  "name": "UE_Roundtrip",
  "position": [0, 0, 1.7],
  "speed": 8.0,
  "trajectory": {
    "waypoints": [
      [0, 0, 1.7],
      [100, 100, 1.7],
      [0, 0, 1.7]
    ],
    "loop": true
  }
}
```

**場景 4：複雜軌跡（園區巡迴）**
```json
{
  "name": "UE_Complex",
  "position": [0, 0, 1.7],
  "speed": 5.0,
  "trajectory": {
    "waypoints": [
      [0, 0, 1.7],
      [100, 0, 1.7],
      [100, 100, 1.7],
      [0, 100, 1.7],
      [0, 0, 1.7]
    ],
    "loop": true
  }
}
```

**典型高度：**
- 行人：`1.7` m（眼睛高度）
- 車輛：`1.5` m（車頂高度）
- 無人機：`50+` m（飛行高度）

---

### 6️⃣ metadata（元數據，可選）

```json
"metadata": {
  "version": "1.0",
  "author": "RAN Team",
  "created": "2026-04-24",
  "description": "RAN 數字孿生場景",
  "notes": [
    "所有座標基於笛卡爾坐標系",
    "高度 (Z 軸) 可為負值（地下）",
    "UE 軌跡自動迴圈"
  ]
}
```

---

## 🛠️ 生成工具和方法

### 方法 1：手動編輯（最簡單）

```bash
nano /home/mitlab/Omniverse/scene_config.json
```

編輯器打開後，修改相應欄位。

**常用快捷鍵：**
- `Ctrl+X` - 退出
- `Ctrl+O` - 保存
- `Ctrl+A` - 全選
- `Ctrl+K` - 刪除行

---

### 方法 2：Python 腳本生成

若要動態生成配置，可使用 Python：

```python
#!/usr/bin/env python3
import json

config = {
    "environment": {
        "usd": "file:///path/to/environment.usd"
    },
    "ground": {
        "material": "grass",
        "size": [1000, 1000]
    },
    "buildings": [
        {
            "name": f"Building_{i}",
            "position": [i*100, i*100, 0],
            "size": [50, 30, 100],
            "material": "concrete"
        }
        for i in range(1, 4)
    ],
    "gnbs": [
        {
            "name": "gNB_Macro_1",
            "position": [200, 200, 50],
            "frequency_ghz": 3.5,
            "power_dbm": 43,
            "bandwidth_mhz": 100
        }
    ],
    "ues": [
        {
            "name": "UE_1",
            "prim_path": "/World/UE_1",
            "position": [0, 0, 1.7],
            "speed": 5.0,
            "trajectory": {
                "waypoints": [[0, 0, 1.7], [100, 100, 1.7], [0, 0, 1.7]],
                "loop": True
            }
        }
    ]
}

# 寫入檔案
with open("/home/mitlab/Omniverse/scene_config.json", "w") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("✓ scene_config.json 已生成")
```

保存為 `generate_config.py`，然後執行：

```bash
python3 generate_config.py
```

---

### 方法 3：從模板複製

```bash
# 複製我為你創建的範例
cp /home/mitlab/Omniverse/scene_config.json \
   /home/mitlab/Omniverse/scene_config_backup.json

# 然後編輯原文件
nano /home/mitlab/Omniverse/scene_config.json
```

---

## ✅ 驗證配置文件

### 驗證 JSON 格式

```bash
python3 -m json.tool /home/mitlab/Omniverse/scene_config.json
```

若格式正確，會輸出格式化的 JSON。若有錯誤，會顯示錯誤信息。

### 驗證配置內容

```bash
# 查看完整配置
cat /home/mitlab/Omniverse/scene_config.json | python3 -m json.tool

# 查看建築物數量
python3 -c "import json; cfg = json.load(open('/home/mitlab/Omniverse/scene_config.json')); print(f'建築物數: {len(cfg.get(\"buildings\", []))}')"

# 查看基站信息
python3 -c "import json; cfg = json.load(open('/home/mitlab/Omniverse/scene_config.json')); [print(f'{g[\"name\"]}: {g[\"frequency_ghz\"]} GHz') for g in cfg.get('gnbs', [])]"

# 查看 UE 信息
python3 -c "import json; cfg = json.load(open('/home/mitlab/Omniverse/scene_config.json')); [print(f'{u[\"name\"]}: 速度 {u[\"speed\"]} m/s') for u in cfg.get('ues', [])]"
```

---

## 📊 完整範例：小型園區

```json
{
  "environment": {
    "usd": "file:///assets/sky.usd"
  },
  "ground": {
    "material": "asphalt",
    "size": [500, 500]
  },
  "buildings": [
    {
      "name": "Main_Office",
      "position": [0, 0, 0],
      "size": [100, 80, 50],
      "material": "concrete"
    },
    {
      "name": "Warehouse",
      "position": [150, 0, 0],
      "size": [120, 100, 30],
      "material": "steel"
    },
    {
      "name": "Cafeteria",
      "position": [-100, 50, 0],
      "size": [50, 40, 15],
      "material": "glass"
    }
  ],
  "gnbs": [
    {
      "name": "gNB_1",
      "position": [250, 250, 40],
      "frequency_ghz": 3.5,
      "power_dbm": 40,
      "bandwidth_mhz": 100
    },
    {
      "name": "gNB_2",
      "position": [-250, -250, 35],
      "frequency_ghz": 3.5,
      "power_dbm": 38,
      "bandwidth_mhz": 100
    }
  ],
  "ues": [
    {
      "name": "UE_Visitor",
      "position": [0, 0, 1.7],
      "speed": 1.4,
      "trajectory": {
        "waypoints": [
          [0, 0, 1.7],
          [100, 0, 1.7],
          [100, 100, 1.7],
          [0, 100, 1.7],
          [0, 0, 1.7]
        ],
        "loop": true
      }
    },
    {
      "name": "UE_Staff",
      "position": [100, 100, 1.7],
      "speed": 5.0,
      "trajectory": {
        "waypoints": [
          [100, 100, 1.7],
          [150, 100, 1.7],
          [150, 0, 1.7],
          [100, 100, 1.7]
        ],
        "loop": true
      }
    },
    {
      "name": "UE_Vehicle",
      "position": [-100, 50, 1.5],
      "speed": 10.0,
      "trajectory": {
        "waypoints": [
          [-100, 50, 1.5],
          [200, 50, 1.5],
          [-100, 50, 1.5]
        ],
        "loop": true
      }
    }
  ],
  "metadata": {
    "version": "1.0",
    "description": "小型園區配置",
    "buildings_count": 3,
    "gnbs_count": 2,
    "ues_count": 3
  }
}
```

---

## 🔄 修改後重新加載

修改 `scene_config.json` 後，重新啟動 Kit 即可加載新配置：

```bash
# 停止現有系統
./stop.sh

# 啟動系統（會讀取最新配置）
./start.sh
```

或在菜單中：

```bash
./run.sh
# 選擇 2 (停止所有)
# 選擇 1 (啟動完整系統)
```

---

## 💡 最佳實踐

1. **從範例開始** → 複製 `scene_config.json.example`
2. **逐步修改** → 一次修改一個部分
3. **驗證格式** → `python3 -m json.tool` 檢查
4. **備份原文件** → 修改前備份
5. **小範圍測試** → 先少量建築/基站/UE 測試
6. **重啟系統** → 修改後重新啟動

---

## 🚨 常見錯誤

### 錯誤 1：JSON 格式錯誤

```
JSONDecodeError: Expecting value
```

**原因：** 遺漏逗號或引號

**修復：**
```bash
python3 -m json.tool /home/mitlab/Omniverse/scene_config.json
```

檢查錯誤位置。

### 錯誤 2：陣列格式錯誤

```json
// ❌ 錯誤：少一個中括號
"position": [0, 0, 0

// ✅ 正確
"position": [0, 0, 0]
```

### 錯誤 3：軌跡路點缺少高度

```json
// ❌ 錯誤：只有 X, Y
"waypoints": [[0, 0], [100, 100]]

// ✅ 正確：X, Y, Z
"waypoints": [[0, 0, 1.7], [100, 100, 1.7]]
```

---

現在你完全掌握了如何生成和自訂 `scene_config.json`！🎉

開始編輯吧：

```bash
nano /home/mitlab/Omniverse/scene_config.json
```
