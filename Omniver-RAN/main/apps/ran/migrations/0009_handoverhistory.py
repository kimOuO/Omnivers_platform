from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0008_signalhistory_serving_cell_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='HandoverHistory',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('session_uuid', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('ho_uuid', models.CharField(db_index=True, max_length=255, unique=True)),
                ('ue_name', models.CharField(db_index=True, max_length=128)),
                ('source_cell', models.CharField(max_length=128)),
                ('target_cell', models.CharField(max_length=128)),
                ('trigger', models.CharField(default='A3_TTT', max_length=32)),
                ('status', models.CharField(default='SUCC', max_length=16)),
                ('event_ts', models.DateTimeField(db_index=True)),
            ],
            options={
                'db_table': 'handover_history',
                'ordering': ('-event_ts',),
                'indexes': [
                    models.Index(fields=['session_uuid', 'event_ts'], name='ix_hoh_session_ts'),
                    models.Index(fields=['ue_name', 'event_ts'], name='ix_hoh_ue_ts'),
                ],
            },
        ),
    ]
