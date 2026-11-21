from django.db import migrations, models


def assign_positions(apps, schema_editor):
    ShoppingItem = apps.get_model("shopping", "ShoppingItem")
    homes = ShoppingItem.objects.values_list("household_id", flat=True).distinct()
    for household_id in homes:
        items = ShoppingItem.objects.filter(household_id=household_id).order_by("name", "id")
        for index, item in enumerate(items, start=1):
            ShoppingItem.objects.filter(pk=item.pk).update(position=index)


class Migration(migrations.Migration):

    dependencies = [
        ("shopping", "0006_purchase"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingitem",
            name="position",
            field=models.PositiveIntegerField(default=0, verbose_name="orden"),
        ),
        migrations.RunPython(assign_positions, migrations.RunPython.noop),
    ]
