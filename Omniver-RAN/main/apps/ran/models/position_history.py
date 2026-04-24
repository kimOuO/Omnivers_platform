from django.db import models


class PositionHistory(models.Model):
    id = models.AutoField(primary_key=True)
    entity_name = models.CharField(max_length=128, db_index=True)
    entity_type = models.CharField(max_length=16)  # "ue" or "gnb"
    x = models.FloatField()
    y = models.FloatField()
    z = models.FloatField()
    position_ts = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "ran"
        db_table = "position_history"
        indexes = [models.Index(fields=["entity_name", "position_ts"], name="ix_posh_entity_ts")]
