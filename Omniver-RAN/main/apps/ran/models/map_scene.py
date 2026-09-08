"""MapScene — 由 OpenStreetMap bbox 產生的地圖 USD 場景。

Lifecycle:
  generate  → Overpass 抓 OSM → osm_to_usd 轉 USD → status=ready, usd_path 落地
  apply     → 注入 environment.template_usd + skip_buildings 推給 Kit 顯示
以 name 為選取鍵(例如 "NTUST")。
"""
from django.db import models


class MapScene(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, unique=True, db_index=True)  # 選取鍵
    label = models.CharField(max_length=256, blank=True, default="")

    # bbox(WGS84)
    min_lon = models.FloatField()
    min_lat = models.FloatField()
    max_lon = models.FloatField()
    max_lat = models.FloatField()

    usd_path = models.CharField(max_length=512, blank=True, default="")

    status = models.CharField(max_length=16, default="pending", db_index=True)  # pending|ready|failed
    error = models.TextField(blank=True, default="")

    # 是否為「當前套用到場景」的地圖(同時只有一張 active)。
    # generate() 讀 active 地圖 → 輸出 environment.template_usd + skip_buildings,
    # 讓 Scene Layout / build 都一致帶上地圖(統一場景狀態)。
    active = models.BooleanField(default=False, db_index=True)

    # 室內掃描模式:天花板收起來(否則從外面只看到一個封閉盒子)、
    # gNB 視覺尺寸縮小(塔身半徑與輻射環都是 gnb_visual_scale 的倍數,
    # 預設 1.0 是給城市尺度用的,放進 6 m 高的走廊會塞爆)。
    # 存在 DB 而不是只塞進某一次的 scene config —— 任何觸發 build 的動作
    # 都會用 generator 重新產生 config,不存起來就會被蓋回去。
    indoor_mode = models.BooleanField(default=False)
    gnb_visual_scale = models.FloatField(default=1.0)

    # 產出統計(方便 list 顯示)
    building_count = models.IntegerField(default=0)
    height_max_m = models.FloatField(default=0.0)
    extent_ew_m = models.FloatField(default=0.0)
    extent_ns_m = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "map_scene"
        ordering = ("-created_at",)
