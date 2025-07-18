# Generated by Django 5.2 on 2025-05-08 12:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='behavior',
            options={'ordering': ['sort'], 'verbose_name': '算法', 'verbose_name_plural': '算法'},
        ),
        migrations.AlterModelOptions(
            name='notification',
            options={'verbose_name': '通知', 'verbose_name_plural': '通知'},
        ),
        migrations.AddField(
            model_name='behavior',
            name='name_en',
            field=models.CharField(default='', max_length=50, verbose_name='算法英文名称'),
        ),
        migrations.AddField(
            model_name='behavior',
            name='sort',
            field=models.IntegerField(default=0, verbose_name='排序'),
        ),
        migrations.AddField(
            model_name='behavior',
            name='state',
            field=models.IntegerField(default=0, verbose_name='状态'),
        ),
        migrations.AlterField(
            model_name='camera',
            name='last_update_time',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
        migrations.AlterField(
            model_name='camera',
            name='remark',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='备注'),
        ),
        migrations.AlterField(
            model_name='control',
            name='interval',
            field=models.IntegerField(default=0, verbose_name='检测间隔'),
        ),
        migrations.AlterField(
            model_name='control',
            name='last_update_time',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
        migrations.AlterField(
            model_name='control',
            name='overlap_thresh',
            field=models.FloatField(default=0.0, verbose_name='阈值'),
        ),
        migrations.AlterField(
            model_name='control',
            name='push_stream_app',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='推流应用'),
        ),
        migrations.AlterField(
            model_name='control',
            name='push_stream_name',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='推流名称'),
        ),
        migrations.AlterField(
            model_name='control',
            name='sensitivity',
            field=models.FloatField(default=0.0, verbose_name='灵敏度'),
        ),
        migrations.AlterField(
            model_name='control',
            name='user_id',
            field=models.IntegerField(default=0, verbose_name='用户'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='last_update_time',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
        migrations.AlterField(
            model_name='notification',
            name='state',
            field=models.IntegerField(default=0, verbose_name='状态'),
        ),
        migrations.AlterModelTable(
            name='alarm',
            table='av_alarm',
        ),
        migrations.AlterModelTable(
            name='chathistory',
            table='av_chat_history',
        ),
        migrations.AlterModelTable(
            name='chatmessage',
            table='av_chat_message',
        ),
    ]
