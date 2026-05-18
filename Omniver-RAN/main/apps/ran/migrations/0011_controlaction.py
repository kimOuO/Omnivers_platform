from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0010_signalhistory_throughput_mcs_prb'),
    ]

    operations = [
        migrations.CreateModel(
            name='ControlAction',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('session_uuid', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('ric_req_id', models.JSONField(default=dict)),
                ('control_style', models.IntegerField()),
                ('control_action_id', models.IntegerField()),
                ('action_label', models.CharField(max_length=64)),
                ('ue_name', models.CharField(blank=True, db_index=True, max_length=128, null=True)),
                ('cell_id', models.CharField(blank=True, db_index=True, max_length=128, null=True)),
                ('payload_json', models.JSONField(default=dict)),
                ('outcome', models.CharField(default='OK', max_length=64)),
                ('error', models.TextField(blank=True, null=True)),
                ('action_ts', models.DateTimeField(db_index=True)),
            ],
            options={
                'db_table': 'control_action',
                'ordering': ('-action_ts',),
                'indexes': [
                    models.Index(fields=['session_uuid', 'action_ts'], name='ix_ctrl_session_ts'),
                ],
            },
        ),
    ]
