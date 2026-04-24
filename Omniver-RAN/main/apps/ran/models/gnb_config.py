from django.db import models


class GnbConfig(models.Model):
    id = models.AutoField(primary_key=True)
    gnb_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=128, unique=True, db_index=True)
    freq_mhz = models.FloatField()
    power_dbm = models.FloatField()
    bw_hz = models.FloatField()
    active = models.BooleanField(default=True)
    gnb_created_at = models.DateTimeField(auto_now_add=True)
    gnb_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "gnb_config"
