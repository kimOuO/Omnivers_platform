from django.db import models


class ObstacleObject(models.Model):
    id = models.AutoField(primary_key=True)
    obstacle_uuid = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=128, unique=True, db_index=True)
    scene_id = models.CharField(max_length=128, blank=True, default="")
    pos_x = models.FloatField(default=0)
    pos_y = models.FloatField(default=0)
    pos_z = models.FloatField(default=0)
    size_x = models.FloatField(default=10)
    size_y = models.FloatField(default=10)
    size_z = models.FloatField(default=10)
    color_r = models.FloatField(default=0.75)
    color_g = models.FloatField(default=0.75)
    color_b = models.FloatField(default=0.75)
    material = models.CharField(max_length=128, blank=True, default="")
    usd_path = models.CharField(max_length=512, blank=True, default="")
    scale_x = models.FloatField(default=1.0)
    scale_y = models.FloatField(default=1.0)
    scale_z = models.FloatField(default=1.0)
    obstacle_created_at = models.DateTimeField(auto_now_add=True)
    obstacle_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ran"
        db_table = "obstacle_object"
