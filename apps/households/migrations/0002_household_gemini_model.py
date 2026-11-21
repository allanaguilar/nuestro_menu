from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("households", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="household",
            name="gemini_model",
            field=models.CharField(
                default="gemini-3.5-flash", max_length=80, verbose_name="modelo de IA"
            ),
        ),
    ]
