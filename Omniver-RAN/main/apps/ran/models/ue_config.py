from django.db import models


class UeConfig(models.Model):
    id = models.AutoField(primary_key=True)
    ue_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=128, unique=True, db_index=True)
    waypoints_json = models.JSONField(default=list)
    speed_mps = models.FloatField(default=1.0)
    loop = models.BooleanField(default=True)
    ue_created_at = models.DateTimeField(auto_now_add=True)
    ue_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "ue_config"
