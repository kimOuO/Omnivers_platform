# 材質完整清單

## 📦 Building_1 (Brownstone01) - 可用材質

| 材質名稱 | MDL 檔案 | 顏色 | 用途 |
|---------|---------|------|------|
| **Cladding_Pella_White** | Cladding_Pella_White.mdl | 白色 (1.0, 1.0, 1.0) | 外牆護板 |
| **Default_New_Material** | Default_New_Material.mdl | 標準灰 | 預設材質 |
| **Mesh** | Mesh.mdl | 標準 | 網格結構 |
| **Rigid_insulation** | Rigid_insulation.mdl | 淺灰 | 絕緣層 |
| **STONE_PAVERS** | STONE_PAVERS.mdl | 石色 | 石板鋪面 |

## 📦 Building_2 (Brownstone02) - 可用材質

| 材質名稱 | MDL 檔案 | 用途 |
|---------|---------|------|
| **COUNTER_TOP_OWNER** | COUNTER_TOP__OWNER_.mdl | 檯面 |
| **Grout** | Grout.mdl | 灰縫 |
| **Phase_Exist** | Phase___Exist.mdl | 現有面層 |

## 🏢 障礙物 (Obstacles) - 分配材質

### Building_3 (Factory)
```
原配置：磚紅色 [0.72, 0.36, 0.28]
分配材質：STONE_PAVERS (石材效果)
原因：工廠通常用粗糙石材或混凝土
```

### Building_4
```
原配置：淺藍 [0.5, 0.7, 0.9]
分配材質：Cladding_Pella_White (白色外牆)
原因：通用建築外牆
```

### Building_5
```
原配置：深灰 [0.3, 0.3, 0.3]
分配材質：Rigid_insulation (灰色絕緣)
原因：深灰色，適合隔熱層
```

### Building_6
```
原配置：淺灰 [0.6, 0.6, 0.6]
分配材質：Default_New_Material (標準灰)
原因：通用灰色材質
```

## 🎨 Materials 目錄結構

```
/home/mitlab/XAPP_DT/Omnivers_platform/assets/building/brownstone/Materials/
├── Cladding_Pella_White.mdl         (1.4 KB) - 白色護板
├── COUNTER_TOP__OWNER_.mdl          (1.4 KB) - 檯面
├── Default_New_Material.mdl          (1.4 KB) - 預設材質
├── Grout.mdl                         (1.4 KB) - 灰縫
├── Mesh.mdl                          (1.4 KB) - 網格
├── Phase___Exist.mdl                 (1.4 KB) - 面層
├── Rigid_insulation.mdl              (1.4 KB) - 絕緣層
└── STONE_PAVERS.mdl                  (1.4 KB) - 石板

總計：8 個材質文件，來自 Revit Brownstone 資料庫
```

## 📊 所有物件材質分配

### Buildings (主建築)
| 物件 | 材質 | MDL 檔案 | 狀態 |
|-----|------|---------|------|
| Building_1 | 26 種（來自 Revit） | Revit_Brownstone01/ | ✅ 已修復 |
| Building_2 | 15 種（來自 Revit） | Revit_Brownstone02/ | ✅ 已修復 |

### Obstacles (障礙物)
| 物件 | 分配材質 | MDL 檔案 | 視覺效果 |
|-----|--------|---------|--------|
| Building_3 | STONE_PAVERS | STONE_PAVERS.mdl | 石材紋理 |
| Building_4 | Cladding_Pella_White | Cladding_Pella_White.mdl | 白色光滑 |
| Building_5 | Rigid_insulation | Rigid_insulation.mdl | 深灰絕緣 |
| Building_6 | Default_New_Material | Default_New_Material.mdl | 標準灰色 |

## 🔧 MDL 材質特性（基於 OmniPBR）

所有材質都基於 NVIDIA OmniPBR 標準，支持：

```
✓ Diffuse Color (漫反射顏色)
✓ Roughness (粗糙度)
✓ Metallic (金屬度)
✓ Normal Map (法線貼圖)
✓ Emission (自發光)
✓ AO (環境遮蔽)
```

## 💾 Dockerfile 更新

已將 Materials 目錄添加到 COPY 指令：

```dockerfile
COPY assets/ /app/assets/
```

此命令會自動複製所有子目錄，包括：
```
/app/assets/building/brownstone/Materials/
```

---

最後更新: 2026-04-26
