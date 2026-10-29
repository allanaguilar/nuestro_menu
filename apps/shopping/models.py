import re
import uuid

from django.conf import settings
from django.db import models


def normalize_item_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


class ShoppingItem(models.Model):
    class Aisle(models.TextChoices):
        NONE = "none", "Sin pasillo"
        FRUIT = "frutas", "Frutas"
        VEGETABLE = "verduras", "Verduras"
        DAIRY = "lacteos", "Lácteos"
        MEAT = "carnes", "Carnes"
        FISH = "pescados", "Pescados"
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
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shopping_items_added",
    )
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


class ShoppingPresence(models.Model):
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="shopping_presence"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shopping_presence",
    )
    client_key = models.CharField(max_length=64, blank=True, default="")
    last_seen = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["household", "user", "client_key"],
                name="uniq_shopping_presence",
            )
        ]
