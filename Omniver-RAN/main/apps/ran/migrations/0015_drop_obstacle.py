"""Drop ObstacleObject and remove obstacle UsdAsset presets.

Obstacle subsystem retired — never used (0 rows in obstacle_object), Sionna
scene builder did not consume `config["obstacles"]`. Functionality fully
covered by BuildingObject (which has material/size/rotation that Sionna actually
uses).
"""
from django.db import migrations


def _delete_obstacle_assets(apps, schema_editor):
    UsdAsset = apps.get_model("ran", "UsdAsset")
    UsdAsset.objects.filter(object_type="obstacle").delete()


def _noop(apps, schema_editor):
    # Forward-only; no automatic recreation of obstacle presets.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0014_drop_scene_snapshot'),
    ]

    operations = [
        migrations.RunPython(_delete_obstacle_assets, _noop),
        migrations.DeleteModel(name='ObstacleObject'),
    ]
