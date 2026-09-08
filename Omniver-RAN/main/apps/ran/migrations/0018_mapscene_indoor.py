"""室內模式旗標 —— 讓「這張地圖是室內掃描」的設定跟著地圖走。

沒有這個欄位的話，室內化設定只存在於某一次 push 的 config 裡，
任何其他觸發 build 的動作（新增 gNB、套用劇本…）都會用 generator
重新產生 config，天花板又蓋回去、gNB 又變回城市尺度的巨塔。
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ran", "0017_mapscene_active")]

    operations = [
        migrations.AddField(
            model_name="mapscene",
            name="indoor_mode",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="mapscene",
            name="gnb_visual_scale",
            field=models.FloatField(default=1.0),
        ),
    ]
