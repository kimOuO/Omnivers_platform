from django.db import models


class GnbState(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, unique=True, db_index=True)
    position_json = models.JSONField()
    state_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "gnb_state"
