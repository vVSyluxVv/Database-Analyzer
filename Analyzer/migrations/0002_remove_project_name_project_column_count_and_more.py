# Generated by Django 5.2.2 on 2025-06-06 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Analyzer', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='name',
        ),
        migrations.AddField(
            model_name='project',
            name='column_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='project',
            name='db_name',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AddField(
            model_name='project',
            name='table_count',
            field=models.IntegerField(default=0),
        ),
    ]
