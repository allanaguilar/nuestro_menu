from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RecipePreference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipe_preferences",
    )
    recipe = models.ForeignKey(
        "recipes.Recipe",
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    rating = models.PositiveSmallIntegerField(
        "puntuación",
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    is_favorite = models.BooleanField("favorita", default=False)
    is_avoided = models.BooleanField("evitar", default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "preferencia"
        verbose_name_plural = "preferencias"
        constraints = [
            models.UniqueConstraint(fields=["user", "recipe"], name="uniq_user_recipe_pref"),
            models.CheckConstraint(
                check=models.Q(rating__isnull=True)
                | models.Q(rating__gte=1, rating__lte=5),
                name="pref_rating_range",
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.recipe}"
