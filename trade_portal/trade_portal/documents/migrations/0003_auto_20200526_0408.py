# Generated by Django 2.2.10 on 2020-05-25 18:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_auto_20200526_0339"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("documents", "0002_fixture"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="party",
            options={"ordering": ("name",), "verbose_name_plural": "parties"},
        ),
        migrations.RemoveField(
            model_name="document",
            name="created_by",
        ),
        migrations.AddField(
            model_name="document",
            name="created_by_org",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="users.Organisation",
            ),
        ),
        migrations.AddField(
            model_name="document",
            name="created_by_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="document",
            name="type",
            field=models.CharField(
                choices=[
                    ("pref_coo", "Preferential Certificate of Origin"),
                    ("non_pref_coo", "Non-preferential Certificate of Origin"),
                ],
                max_length=64,
            ),
        ),
    ]
