"""Scenario — 外部模擬系統匯入的 UE 軌跡 + traffic 時間軸,給 Phase B fast-replay 模式用。

Lifecycle:
  upload   → status=pending, raw_json 落地
  precompute trigger → status=running,Sionna 離線批次計算 channel cache
  precompute done    → status=ready,cache_path 指向 parquet 檔
  Fast Run         → RU 切 cached mode 讀 cache,scenario_driver(RANsim-UE) 推位置 + traffic
"""
from django.db import models


class Scenario(models.Model):
    id = models.AutoField(primary_key=True)
    scenario_id = models.CharField(max_length=128, unique=True, db_index=True)
    scene_id = models.CharField(max_length=128, db_index=True)

    # raw scenario JSON(完整 schema 見 docs/plan/fast-replay-mode.md B.1)
    raw_json = models.JSONField(default=dict)

    # 從 raw_json 提取的冗餘欄位,方便 list 不用 parse JSON
    duration_sec = models.FloatField(default=0.0)
    tick_ms = models.IntegerField(default=500)
    ue_count = models.IntegerField(default=0)

    # Precompute job state
    precompute_status = models.CharField(
        max_length=16, default="pending", db_index=True
    )  # pending | running | ready | failed
    precompute_progress = models.FloatField(default=0.0)  # 0~100
    precompute_error = models.TextField(blank=True, default="")
    cache_path = models.CharField(max_length=512, blank=True, default="")
    cache_size_bytes = models.BigIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "scenario"
        indexes = [
            models.Index(fields=["scene_id", "precompute_status"], name="ix_scen_scene_status"),
            models.Index(fields=["-created_at"], name="ix_scen_created"),
        ]
        ordering = ("-created_at",)
