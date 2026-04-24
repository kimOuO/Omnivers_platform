from django.db import models


class UeState(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, unique=True, db_index=True)
    position_json = models.JSONField(default=dict)
    serving_cell = models.CharField(max_length=128, null=True, blank=True)
    rsrp_dbm = models.FloatField(null=True, blank=True)
    sinr_db = models.FloatField(null=True, blank=True)
    state_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "ue_state"
