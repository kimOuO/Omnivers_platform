from django.db import models


class PlatformEvent(models.Model):
    id = models.AutoField(primary_key=True)
    event_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    event = models.CharField(max_length=64, db_index=True)
    payload_json = models.JSONField()
    event_ts = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "ran"
        db_table = "platform_events"
