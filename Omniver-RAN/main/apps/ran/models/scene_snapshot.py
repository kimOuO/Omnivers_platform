from django.db import models


class SceneSnapshot(models.Model):
    id = models.AutoField(primary_key=True)
    scene_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    scene_id = models.CharField(max_length=128, db_index=True)
    config_json = models.JSONField()
    scene_created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "ran"
        db_table = "scene_snapshot"
