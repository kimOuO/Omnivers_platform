# Generated migration to fix brownstone preset rotation values
from django.db import migrations


def fix_brownstone_rotation(apps, schema_editor):
    """Fix brownstone01/02 preset rotation: [0,0,-90] (incorrect) → [-90,0,0] (correct for Z-up asset)"""
    UsdAsset = apps.get_model('ran', 'UsdAsset')
    UsdAsset.objects.filter(
        preset_id__in=['brownstone01', 'brownstone02']
    ).update(default_rotation=[-90, 0, 0])


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0005_add_default_rotation'),
    ]

    operations = [
        migrations.RunPython(fix_brownstone_rotation, migrations.RunPython.noop),
    ]
