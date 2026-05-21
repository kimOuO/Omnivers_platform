from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0011_controlaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='Scenario',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('scenario_id', models.CharField(db_index=True, max_length=128, unique=True)),
                ('scene_id', models.CharField(db_index=True, max_length=128)),
                ('raw_json', models.JSONField(default=dict)),
                ('duration_sec', models.FloatField(default=0.0)),
                ('tick_ms', models.IntegerField(default=500)),
                ('ue_count', models.IntegerField(default=0)),
                ('precompute_status', models.CharField(db_index=True, default='pending', max_length=16)),
                ('precompute_progress', models.FloatField(default=0.0)),
                ('precompute_error', models.TextField(blank=True, default='')),
                ('cache_path', models.CharField(blank=True, default='', max_length=512)),
                ('cache_size_bytes', models.BigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'scenario',
                'ordering': ('-created_at',),
                'indexes': [
                    models.Index(fields=['scene_id', 'precompute_status'], name='ix_scen_scene_status'),
                    models.Index(fields=['-created_at'], name='ix_scen_created'),
                ],
            },
        ),
    ]
