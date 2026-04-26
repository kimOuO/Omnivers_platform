# Building_2 材質詳細說明

## 📦 基本信息

| 項目 | 內容 |
|------|------|
| **名稱** | Building_2 |
| **USD 檔案** | Brownstone02_Building.usda |
| **引用來源** | brownstone/Revit_Brownstone02/Revit_Brownstone02_Exterior.usd |
| **檔案格式** | USD Crate (二進制) v0.7.0 |
| **檔案大小** | 912 KB |
| **座標** | [300, 0, 0] |
| **高度** | 500 m |
| **材質系統** | Revit MDL (NVIDIA Material Definition Language) |

---

## 🎨 包含的材質列表（共 15 個）

Building_2 (Brownstone 棕石建築 - 第二棟) 包含以下建築材質：

### 1. **Concrete_Cast_in_Place_Concrete** (現澆混凝土)
```
Looks: Concrete___Cast_in_Place_Concrete
Shaders: Shaders2
材質 ID: 8778852934025906622
材質名: Concrete_Formed (成型混凝土)
用途: 混凝土結構/基礎
```

### 2. **Concrete** (一般混凝土)
```
Looks: Concrete
Shaders: Shaders3
材質 ID: 10672945374328417773
材質名: Concrete_Smooth (光滑混凝土)
用途: 混凝土地面
```

### 3. **Glass** (玻璃)
```
Looks: Glass
Shaders: Shaders4
材質 ID: 15181436960767156555
材質名: Clear_Glass (透明玻璃)
用途: 窗戶/玻璃面板
```

### 4. **Wood** (木質)
```
Looks: Wood
Shaders: Shaders5
材質 ID: 9517907869643977269
材質名: Bamboo_Planks (竹木地板)
用途: 木製結構/裝飾
```

### 5. **Invalid** (無效/預設)
```
Looks: Invalid
Shaders: Shaders6
材質 ID: 10244412757990298668
材質名: WhiteMode (白模式)
用途: 降級渲染用
```

### 6. **Cherry** (櫻桃木)
```
Looks: Cherry
Shaders: Shaders7
材質 ID: 2904120789804736982
材質名: Cherry (櫻桃木)
用途: 高級木質裝飾
```

### 7. **Metal** (金屬)
```
Looks: Metal
Shaders: Shaders8
材質 ID: 8240979829490134409
材質名: Steel_Carbon (碳鋼)
用途: 金屬結構/配件
```

### 8. **Miscellaneous** (雜項)
```
Looks: Miscellaneous
Shaders: Shaders9
材質 ID: 14864800830175488526
材質名: Porcelain_Smooth (光滑瓷器)
用途: 其他配件
```

### 9. **Door_Frame** (門框)
```
Looks: Door___Frame
Shaders: Shaders10
材質 ID: 9512042109002033194
材質名: Ash (灰木)
用途: 木質門框
```

### 10. **Door_Panel** (門板)
```
Looks: Door___Panel
Shaders: Shaders11
材質 ID: 9512042109002033194
材質名: Ash (灰木)
用途: 木質門板
```

### 11. **Plastic** (塑膠)
```
Looks: Plastic
Shaders: Shaders12
材質 ID: 11736549630521104194
材質名: Plastic (塑膠)
用途: 塑膠配件/裝飾
```

### 12. **Paint** (油漆)
```
Looks: Paint
Shaders: Shaders13
材質 ID: 6385189579961142547
材質名: Paint_Satin (緞面油漆)
用途: 外牆油漆表面
```

### 13. **Grass** (草坪)
```
Looks: Grass
Shaders: Shaders14
材質 ID: 1468004562323631318
材質名: Grass_Countryside (鄉村草)
用途: 周圍景觀
```

### 14. **Default_Wall** (預設牆面)
```
Looks: Default_Wall
Shaders: Shaders1
材質 ID: 8874546620069064972
材質名: Plaster (石膏)
用途: 主要牆面
```

### 15. **未命名材質** (可能有多個)
```
可能存在其他細節材質，在日誌中未完全列出
```

---

## ⚠️ 當前狀態：材質加載問題

### 現象
```
Error: Unable to find SdrShaderNode for prim: '/World/Building_2/Asset/Brownstone02/Looks/...'
with identifier: '....<MaterialName><mdl>'
```

### 特點
- Building_2 比 Building_1 **材質數量少** (15 vs 26)
- 材質 **簡化了** (沒有複雜的裝飾材質)
- 主要集中在 **基本建築材料**

### 原因 - 與 Building_1 相同
```
Revit 導出的 USD 使用 NVIDIA MDL 材質格式
├─ MDL = Material Definition Language
├─ 需要 NVIDIA 的 MDL 著色器庫
└─ Kit 中未安裝完整的 MDL 定義
```

### 影響
- ✅ 建築物幾何形狀正常顯示
- ❌ 所有 MDL 材質無法渲染
- 🎨 降級為默認灰色/白色
- 📊 不影響場景功能或測試

---

## 📊 材質統計

| 類型 | 數量 | 例子 |
|------|------|------|
| 混凝土/石材 | 2 | Concrete_Formed, Concrete_Smooth |
| 玻璃 | 1 | Clear_Glass |
| 木質 | 2 | Bamboo_Planks, Cherry |
| 金屬 | 1 | Steel_Carbon |
| 其他 | 7 | Plaster, Ash, Plastic, Paint, Grass, Porcelain, WhiteMode |
| 未分類 | 2 | (可能有其他材質未列出) |
| **總計** | **15** | - |

---

## 🔍 Building_1 vs Building_2 比較

| 特性 | Building_1 | Building_2 |
|------|-----------|-----------|
| **USD 檔案大小** | 18 MB | 912 KB |
| **材質數量** | 26 個 | 15 個 |
| **複雜度** | 高（包含裝飾材質） | 中（基本材質為主） |
| **特殊材質** | 大理石、瓷磚、各式木材 | 油漆、混凝土 |
| **材質渲染狀態** | 同樣無法加載 MDL | 同樣無法加載 MDL |
| **視覺效果** | 降級為灰色 | 降級為灰色 |

---

## ❓ "Revit_Brownstone02_Exterior (MDL)" 解釋

### MDL 是什麼？

```
MDL = Material Definition Language (材質定義語言)
├─ NVIDIA 開發的著色器語言
├─ 用於 Omniverse 和專業渲染
└─ Revit 導出 USD 時自動使用 MDL 格式
```

### 在你的場景中

```
Brownstone02_Building.usda
    ↓ 引用
Revit_Brownstone02_Exterior.usd
    ↓ 包含
MDL 材質定義
    ├─ Paint_Satin (緞面油漆)
    ├─ Concrete_Formed (成型混凝土)
    ├─ Clear_Glass (透明玻璃)
    └─ 其他 12 個 MDL 材質
```

### 為什麼顯示為 "(MDL)"？

當前配置文檔中寫 `Revit_Brownstone02_Exterior (MDL)` 是為了說明：
- **來源**：Revit 導出的 USD 檔案
- **材質格式**：使用 NVIDIA MDL 語言
- **現狀**：未被 Kit 正確渲染

---

## 🔧 可能的解決方案

### 方案 1：安裝 MDL 著色器庫（推薦）
```bash
# 在 Dockerfile 中添加
RUN /opt/omniverse-env/bin/pip install \
    nvidia-omniverse-mdl
```

### 方案 2：轉換為 USD Native Materials
```bash
# 在 Revit 中導出時
# 選擇 "USD Preview Surface" 而非 "MDL"
```

### 方案 3：手動設置 MDL 搜索路徑
```bash
# 在 Kit 配置文件中
OMNIVERSE_MDL_PATHS=/path/to/mdl/libraries
```

---

## 📌 現況總結

| 項目 | 狀態 |
|------|------|
| **建築物加載** | ✅ 成功 |
| **幾何形狀** | ✅ 正確 |
| **位置和大小** | ✅ 準確 |
| **MDL 材質渲染** | ❌ 未設置 |
| **視覺效果** | ⚠️ 降級為灰色 |
| **場景功能** | ✅ 完全正常 |

---

**結論：Building_2 可以正常使用，只是視覺效果可以通過安裝 MDL 著色器庫來改善。**

---

最後更新: 2026-04-26
