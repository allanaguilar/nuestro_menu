from django.db import migrations, models


def move_fresh_to_unassigned(apps, schema_editor):
    ShoppingItem = apps.get_model("shopping", "ShoppingItem")
    ShoppingItem.objects.filter(aisle="fresh").update(aisle="none")


def restore_fresh(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("shopping", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(move_fresh_to_unassigned, restore_fresh),
        migrations.AlterField(
            model_name="shoppingitem",
            name="aisle",
            field=models.CharField(
                choices=[
                    ("none", "Sin pasillo"),
                    ("frutas", "Frutas"),
                    ("verduras", "Verduras"),
                    ("lacteos", "Lácteos"),
                    ("carnes", "Carnes"),
                    ("pescados", "Pescados"),
                    ("fridge", "Nevera"),
                    ("pantry", "Despensa"),
                    ("cleaning", "Limpieza"),
                    ("other", "Otros"),
                ],
                default="none",
                max_length=16,
                verbose_name="pasillo",
            ),
        ),
    ]
