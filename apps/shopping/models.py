import re
import uuid

from django.db import models


def normalize_item_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


class ShoppingItem(models.Model):
    class Aisle(models.TextChoices):
        NONE = "none", "Sin pasillo"
        FRESH = "fresh", "Frescos"
        FRIDGE = "fridge", "Nevera"
        PANTRY = "pantry", "Despensa"
        CLEANING = "cleaning", "Limpieza"
        OTHER = "other", "Otros"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="shopping_items"
    )
    name = models.CharField("nombre", max_length=120)
    normalized_name = models.CharField(max_length=120, db_index=True)
    aisle = models.CharField(
        "pasillo", max_length=16, choices=Aisle.choices, default=Aisle.NONE
    )
    done = models.BooleanField("en el carro", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "artículo"
        verbose_name_plural = "artículos"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "normalized_name"],
                name="uniq_shopping_item_name",
            ),
        ]
        indexes = [
            models.Index(fields=["household", "done"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = re.sub(r"\s+", " ", (self.name or "").strip())
        self.normalized_name = normalize_item_name(self.name)
        super().save(*args, **kwargs)
