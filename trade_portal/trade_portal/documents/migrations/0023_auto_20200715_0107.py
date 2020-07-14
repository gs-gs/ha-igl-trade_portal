# Generated by Django 2.2.10 on 2020-07-14 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0022_auto_20200714_2155'),
    ]

    operations = [
        migrations.AddField(
            model_name='party',
            name='bid_prefix',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='party',
            name='clear_business_id',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
    ]
