"""Drop dead-code model GnbState.

Verified zero `.objects` queries in the codebase before removal.
gNBs do not move at runtime; GnbConfig already holds position.

Note: SceneSnapshot was originally bundled with this cleanup but found to
still be read by gnb_actor + tick_loop, so left untouched (see task #101).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ran', '0012_scenario'),
    ]

    operations = [
        migrations.DeleteModel(name='GnbState'),
    ]
