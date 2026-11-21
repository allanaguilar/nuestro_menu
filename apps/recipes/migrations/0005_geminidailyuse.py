from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("recipes", "0004_recipe_servings_recipe_recipe_servings_positive"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeminiDailyUse",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("model_name", models.CharField(max_length=80)),
                ("day", models.DateField()),
                ("count", models.PositiveIntegerField(default=0)),
                ("daily_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("exhausted", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "uso de Gemini",
                "verbose_name_plural": "usos de Gemini",
            },
        ),
        migrations.AddConstraint(
            model_name="geminidailyuse",
            constraint=models.UniqueConstraint(
                fields=("model_name", "day"), name="uniq_gemini_daily_use"
            ),
        ),
    ]
