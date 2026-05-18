from django.db import models


class SignalHistory(models.Model):
    id = models.AutoField(primary_key=True)
    session_uuid = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    signal_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    ue_name = models.CharField(max_length=128, db_index=True)
    serving_cell = models.CharField(max_length=128)
    serving_gnb = models.CharField(max_length=128, null=True, blank=True)
    serving_pci = models.IntegerField(null=True, blank=True)
    serving_cell_id = models.CharField(max_length=128, null=True, blank=True)
    rsrp_dbm = models.FloatField()
    sinr_db = models.FloatField()
    rsrp_map_json = models.JSONField(default=dict)
    # 2026-05-17 #2: KPM 補完 wireless KPI,讓 playback 能重現 throughput/PRB/MCS.
    # 來源:CU `kpm_reporter.collect().ue_status[]`,由 Dashboard / RAN-sim 在 ingest 時帶上。
    throughput_dl_mbps = models.FloatField(null=True, blank=True)
    throughput_ul_mbps = models.FloatField(null=True, blank=True)
    mcs_dl = models.IntegerField(null=True, blank=True)
    prb_used_dl = models.IntegerField(null=True, blank=True)
    mimo_rank = models.IntegerField(null=True, blank=True)
    signal_ts = models.DateTimeField(db_index=True)

    class Meta:
        app_label = "ran"
        db_table = "signal_history"
        indexes = [
            models.Index(fields=["ue_name", "signal_ts"], name="ix_sigh_ue_ts"),
            models.Index(fields=["session_uuid", "signal_ts"], name="ix_sigh_session_ts"),
        ]
