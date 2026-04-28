# Generated migration to add cells JSONField to GnbConfig

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0006_fix_brownstone_rotation'),
    ]

    operations = [
        migrations.AddField(
            model_name='gnbconfig',
            name='cells',
            field=models.JSONField(blank=True, default=list, null=True),
        ),
    ]
