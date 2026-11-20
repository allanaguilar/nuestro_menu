import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chores", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChorePhoto",
            fields=[
                (
                    "chore",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="photo",
                        serialize=False,
                        to="chores.chore",
                    ),
                ),
                ("content", models.BinaryField()),
                (
                    "content_type",
                    models.CharField(default="image/jpeg", max_length=40),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "foto de la tarea",
                "verbose_name_plural": "fotos de las tareas",
            },
        ),
    ]
