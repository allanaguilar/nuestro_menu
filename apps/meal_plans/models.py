import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.week import monday_of


class MealPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        APPROVED = "approved", "Aprobado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="meal_plans"
    )
    week_start = models.DateField("inicio de semana")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_meal_plans",
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "plan semanal"
        verbose_name_plural = "planes semanales"
        constraints = [
            models.UniqueConstraint(
                fields=["household", "week_start"], name="uniq_household_week"
            ),
        ]
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.household} {self.week_start} ({self.status})"

    def clean(self):
        if self.week_start and self.week_start != monday_of(self.week_start):
            raise ValidationError(
                {"week_start": "La semana debe empezar en lunes."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def week_end(self):
        return self.week_start + timedelta(days=6)


class MealPlanEntry(models.Model):
    class Source(models.TextChoices):
        ALGORITHM = "algorithm", "Algoritmo"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meal_plan = models.ForeignKey(
        MealPlan, on_delete=models.CASCADE, related_name="entries"
    )
    day = models.DateField()
    recipe = models.ForeignKey(
        "recipes.Recipe", on_delete=models.PROTECT, related_name="plan_entries"
    )
    selection_source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.ALGORITHM
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "almuerzo"
        verbose_name_plural = "almuerzos"
        constraints = [
            models.UniqueConstraint(
                fields=["meal_plan", "day"], name="uniq_plan_day"
            ),
        ]
        ordering = ["day"]

    def __str__(self):
        return f"{self.day}: {self.recipe}"

    def clean(self):
        if not self.meal_plan_id or not self.day or not self.recipe_id:
            return
        plan = self.meal_plan
        if self.day < plan.week_start or self.day > plan.week_end:
            raise ValidationError({"day": "El día no pertenece a la semana del plan."})
        if self.recipe.household_id != plan.household_id:
            raise ValidationError(
                {"recipe": "La receta debe pertenecer al mismo hogar."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
