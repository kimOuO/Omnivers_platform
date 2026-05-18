from django.db import models


class HandoverHistory(models.Model):
    """單次 handover 事件 — 由 RAN-sim CU 在 handover_executor 落地後 push 過來,
    讓 playback 能把 HO 切回對應 frame_ts。

    對齊 CU 側 cu_cp_handover_event.{ho_uuid, ue_id, source_cell, target_cell,
    trigger, status, started_at, completed_at}。
    """
    id = models.AutoField(primary_key=True)
    session_uuid = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    ho_uuid = models.CharField(max_length=255, unique=True, db_index=True)

    ue_name = models.CharField(max_length=128, db_index=True)
    source_cell = models.CharField(max_length=128)
    target_cell = models.CharField(max_length=128)
    trigger = models.CharField(max_length=32, default="A3_TTT")
    status = models.CharField(max_length=16, default="SUCC")

    event_ts = models.DateTimeField(db_index=True)

    class Meta:
        app_label = "ran"
        db_table = "handover_history"
        indexes = [
            models.Index(fields=["session_uuid", "event_ts"], name="ix_hoh_session_ts"),
            models.Index(fields=["ue_name", "event_ts"], name="ix_hoh_ue_ts"),
        ]
        ordering = ("-event_ts",)
