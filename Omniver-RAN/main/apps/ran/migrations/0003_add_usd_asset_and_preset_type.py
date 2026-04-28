# Generated migration for UsdAsset and preset_type fields

from django.db import migrations, models
from main.apps.ran.services.common.uuid_service import UUIDService
from main.apps.ran.services.common.timestamp_service import TimestampService


def seed_usd_assets(apps, schema_editor):
    """Seed initial USD assets"""
    UsdAsset = apps.get_model('ran', 'UsdAsset')
    timestamp = TimestampService.get_current_timestamp()

    assets_data = [
        {
            'preset_id': 'brownstone01',
            'object_type': 'building',
            'label': 'Brownstone 01',
            'usd_path': '/omniverse/Library/Brownstone01_Building.usda',
            'default_size': [60, 80, 40],
            'default_color': [0.8, 0.6, 0.4],
        },
        {
            'preset_id': 'brownstone02',
            'object_type': 'building',
            'label': 'Brownstone 02',
            'usd_path': '/omniverse/Library/Brownstone02_Building.usda',
            'default_size': [100, 200, 60],
            'default_color': [0.8, 0.6, 0.4],
        },
        {
            'preset_id': 'factory',
            'object_type': 'building',
            'label': 'Factory',
            'usd_path': '/omniverse/Library/factory.usda',
            'default_size': [100, 80, 50],
            'default_color': [0.7, 0.7, 0.7],
        },
        {
            'preset_id': 'cube',
            'object_type': 'building',
            'label': 'Generic Box',
            'usd_path': '',
            'default_size': [10, 10, 10],
            'default_color': [0.75, 0.75, 0.75],
        },
        {
            'preset_id': 'female_office',
            'object_type': 'ue',
            'label': 'Office Woman',
            'usd_path': '/omniverse/Library/female_office.usda',
            'default_size': None,
            'default_color': [1.0, 0.5, 0.0],
        },
        {
            'preset_id': 'male_party',
            'object_type': 'ue',
            'label': 'Casual Man',
            'usd_path': '/omniverse/Library/male_party.usda',
            'default_size': None,
            'default_color': [0.0, 0.5, 1.0],
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
    UsdAsset.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0002_buildingobject_obstacleobject_simulationsession_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UsdAsset',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('asset_uuid', models.CharField(db_index=True, max_length=255, unique=True)),
                ('object_type', models.CharField(
                    choices=[
                        ('building', 'Building'),
                        ('ue', 'User Equipment'),
                        ('obstacle', 'Obstacle'),
                        ('gnb', 'gNodeB'),
                    ],
                    db_index=True,
                    max_length=32,
                )),
                ('preset_id', models.CharField(db_index=True, max_length=128, unique=True)),
                ('label', models.CharField(max_length=256)),
                ('description', models.CharField(blank=True, default='', max_length=512)),
                ('usd_path', models.CharField(max_length=512)),
                ('default_size', models.JSONField(blank=True, default=None, null=True)),
                ('default_color', models.JSONField(blank=True, default=None, null=True)),
                ('default_scale', models.JSONField(blank=True, default=None, null=True)),
                ('active', models.BooleanField(db_index=True, default=True)),
                ('asset_created_at', models.DateTimeField(auto_now_add=True)),
                ('asset_updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'usd_asset',
            },
        ),
        migrations.AddField(
            model_name='buildingobject',
            name='preset_type',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='ueconfig',
            name='preset_type',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='obstacleobject',
            name='preset_type',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.RunPython(seed_usd_assets, reverse_seed),
    ]
