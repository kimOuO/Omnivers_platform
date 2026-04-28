from django.db import models


class UsdAsset(models.Model):
    OBJECT_TYPE_CHOICES = [
        ("building", "Building"),
        ("ue", "User Equipment"),
        ("obstacle", "Obstacle"),
        ("gnb", "gNodeB"),
    ]

    id = models.AutoField(primary_key=True)
    asset_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    object_type = models.CharField(
        max_length=32, choices=OBJECT_TYPE_CHOICES, db_index=True
    )
    preset_id = models.CharField(max_length=128, unique=True, db_index=True)
    label = models.CharField(max_length=256)
    description = models.CharField(max_length=512, blank=True, default="")
    usd_path = models.CharField(max_length=512)
    default_size = models.JSONField(null=True, blank=True, default=None)
    default_color = models.JSONField(null=True, blank=True, default=None)
    default_scale = models.JSONField(null=True, blank=True, default=None)
    default_rotation = models.JSONField(null=True, blank=True, default=None)
    active = models.BooleanField(default=True, db_index=True)
    asset_created_at = models.DateTimeField(auto_now_add=True)
    asset_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "usd_asset"
