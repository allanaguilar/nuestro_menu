import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("shopping", "0007_shoppingitem_position"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchase",
            name="added_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchases_added",
                to=settings.AUTH_USER_MODEL,
                verbose_name="lo añadió",
            ),
        ),
        migrations.AddField(
            model_name="purchase",
            name="bought_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="purchases_bought",
                to=settings.AUTH_USER_MODEL,
                verbose_name="lo compró",
            ),
        ),
        migrations.AlterField(
            model_name="purchase",
            name="bought_on",
            field=models.DateField(verbose_name="comprado"),
        ),
    ]
