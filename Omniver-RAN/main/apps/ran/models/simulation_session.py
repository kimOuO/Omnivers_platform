from django.db import models


class SimulationSession(models.Model):
    """記錄整個模擬批次的 session 元數據。"""
    session_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    scene_id = models.CharField(max_length=128, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=[("running", "Running"), ("ended", "Ended")],
        default="running",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    metadata_json = models.JSONField(default=dict)  # gnb_count, ue_count, etc.

    class Meta:
        app_label = "ran"
        db_table = "simulation_session"
        indexes = [
            models.Index(fields=["session_uuid"], name="ix_simsession_uuid"),
            models.Index(fields=["scene_id", "created_at"], name="ix_simsession_scene_created"),
        ]

    def __str__(self):
        return f"SimSession {self.session_uuid[:8]}... ({self.scene_id})"
