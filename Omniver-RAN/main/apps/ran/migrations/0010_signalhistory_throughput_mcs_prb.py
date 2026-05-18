from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0009_handoverhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='signalhistory',
            name='throughput_dl_mbps',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='signalhistory',
            name='throughput_ul_mbps',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='signalhistory',
            name='mcs_dl',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='signalhistory',
            name='prb_used_dl',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='signalhistory',
            name='mimo_rank',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
