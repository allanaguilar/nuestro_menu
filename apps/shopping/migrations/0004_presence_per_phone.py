from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shopping", "0003_added_by_and_presence"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="shoppingpresence",
            name="uniq_shopping_presence",
        ),
        migrations.AddField(
            model_name="shoppingpresence",
            name="client_key",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="shoppingpresence",
            constraint=models.UniqueConstraint(
                fields=("household", "user", "client_key"),
                name="uniq_shopping_presence",
            ),
        ),
    ]
