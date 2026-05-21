"""Drop SceneSnapshot model after C-step cleanup.

After task #104 (gnb_actor reads GnbConfig.cells[]) and #105 (tick_loop deleted),
verified zero readers remain. SceneIngestor.create no longer writes to the table.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0013_drop_scene_snapshot_gnb_state'),
    ]

    operations = [
        migrations.DeleteModel(name='SceneSnapshot'),
    ]
