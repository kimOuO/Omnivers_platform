from django.db import migrations, models


def seed_default_rotations(apps, schema_editor):
    """Set default_rotation for building presets (Brownstone: Z-axis -90 for correct orientation)."""
    UsdAsset = apps.get_model('ran', 'UsdAsset')
    UsdAsset.objects.filter(
        object_type='building',
        preset_id__in=['brownstone01', 'brownstone02', 'factory', 'cube'],
    ).update(default_rotation=[0, 0, -90])


def reverse_seed(apps, schema_editor):
    UsdAsset = apps.get_model('ran', 'UsdAsset')
    UsdAsset.objects.filter(object_type='building').update(default_rotation=None)


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0004_add_gnb_obstacle_usd_assets'),
    ]

    operations = [
        migrations.AddField(
            model_name='usdasset',
            name='default_rotation',
            field=models.JSONField(blank=True, default=None, null=True),
        ),
        migrations.RunPython(seed_default_rotations, reverse_seed),
    ]
