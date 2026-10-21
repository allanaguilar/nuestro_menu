import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.recipes.utils import normalize_recipe_name


class Recipe(models.Model):
    class Category(models.TextChoices):
        LEGUMBRES = "legumbres", "Legumbres"
        CARNE = "carne", "Carne"
        PESCADO = "pescado", "Pescado"
        PASTA = "pasta", "Pasta"
        ARROZ = "arroz", "Arroz"
        VERDURAS = "verduras", "Verduras"
        HUEVOS = "huevos", "Huevos"
        OTROS = "otros", "Otros"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="recipes"
    )
    name = models.CharField("nombre", max_length=180)
    normalized_name = models.CharField(max_length=180, db_index=True)
    category = models.CharField(
        "categoría", max_length=20, choices=Category.choices, default=Category.OTROS
    )
    prep_time_minutes = models.PositiveIntegerField(
        "tiempo de preparación (minutos)",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    notes = models.TextField("notas", blank=True)
    is_active = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "receta"
        verbose_name_plural = "recetas"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(prep_time_minutes__isnull=True)
                | models.Q(prep_time_minutes__gte=1),
                name="recipe_prep_time_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["household", "normalized_name"]),
            models.Index(fields=["household", "is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_recipe_name(self.name)
        super().save(*args, **kwargs)
