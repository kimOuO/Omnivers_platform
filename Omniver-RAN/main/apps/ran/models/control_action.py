from django.db import models


class ControlAction(models.Model):
    """單次 E2 Control Request — xApp / RIC 下給 CU 的指令。

    由 RAN-sim CU 在 E2ControlActor 各 (style, action) 分支落地後 fire-and-forget push 過來,
    讓 playback 把 RIC 控制決策切回對應 frame_ts。
    與 HandoverHistory 視角互補:HO history 看「實際做了 HO」,ControlAction 看「xApp 下了甚麼」。
    """
    id = models.AutoField(primary_key=True)
    session_uuid = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    ric_req_id = models.JSONField(default=dict)  # {requestor_id, instance_id}
    control_style = models.IntegerField()
    control_action_id = models.IntegerField()
    action_label = models.CharField(max_length=64)  # e.g. "HANDOVER", "PRB_QUOTA"

    ue_name = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    cell_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)

    payload_json = models.JSONField(default=dict)   # 原 control_message dump
    outcome = models.CharField(max_length=64, default="OK")  # ACK / REJECT / ...
    error = models.TextField(null=True, blank=True)

    action_ts = models.DateTimeField(db_index=True)

    class Meta:
        app_label = "ran"
        db_table = "control_action"
        indexes = [
            models.Index(fields=["session_uuid", "action_ts"], name="ix_ctrl_session_ts"),
        ]
        ordering = ("-action_ts",)
