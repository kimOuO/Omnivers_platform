# Generated migration to add gNB and Obstacle USD assets

from django.db import migrations
from main.apps.ran.services.common.uuid_service import UUIDService
from main.apps.ran.services.common.timestamp_service import TimestampService


def seed_gnb_obstacle_assets(apps, schema_editor):
    """Seed gNB and Obstacle USD assets"""
    UsdAsset = apps.get_model('ran', 'UsdAsset')
    timestamp = TimestampService.get_current_timestamp()

    assets_data = [
        {
            'preset_id': 'gnb_standard',
            'object_type': 'gnb',
            'label': 'Standard gNB',
            'usd_path': '/omniverse/Library/gnb_standard.usda',
            'default_size': [4, 4, 8],
            'default_color': [0.2, 0.8, 1.0],  # Light blue
        },
        {
            'preset_id': 'gnb_tower',
            'object_type': 'gnb',
            'label': 'Tower gNB',
            'usd_path': '/omniverse/Library/gnb_tower.usda',
            'default_size': [3, 3, 15],
            'default_color': [0.3, 0.7, 0.9],  # Sky blue
        },
        {
            'preset_id': 'obstacle_wall',
            'object_type': 'obstacle',
            'label': 'Concrete Wall',
            'usd_path': '/omniverse/Library/obstacle_wall.usda',
            'default_size': [50, 0.3, 3],
            'default_color': [0.5, 0.5, 0.5],  # Gray
        },
        {
            'preset_id': 'obstacle_building_small',
            'object_type': 'obstacle',
            'label': 'Small Building',
            'usd_path': '/omniverse/Library/obstacle_building_small.usda',
            'default_size': [30, 30, 20],
            'default_color': [0.6, 0.4, 0.2],  # Brown
        },
    ]

    for asset_data in assets_data:
        asset_uuid = UUIDService.generate_uuid("asset", asset_data['preset_id'])
        UsdAsset.objects.create(
            asset_uuid=asset_uuid,
            object_type=asset_data['object_type'],
            preset_id=asset_data['preset_id'],
            label=asset_data['label'],
            usd_path=asset_data['usd_path'],
            default_size=asset_data['default_size'],
            default_color=asset_data['default_color'],
            active=True,
        )


def reverse_seed(apps, schema_editor):
    """Reverse seed operation"""
    UsdAsset = apps.get_model('ran', 'UsdAsset')
    preset_ids = ['gnb_standard', 'gnb_tower', 'obstacle_wall', 'obstacle_building_small']
    UsdAsset.objects.filter(preset_id__in=preset_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0003_add_usd_asset_and_preset_type'),
    ]

    operations = [
        migrations.RunPython(seed_gnb_obstacle_assets, reverse_seed),
    ]
