# Generated by Django 2.2.10 on 2020-06-10 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20200526_0339'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='dot_separated_id',
            field=models.CharField(blank=True, default='fill.that.value.au', max_length=256),
        ),
    ]
