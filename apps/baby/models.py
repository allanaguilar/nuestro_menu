import uuid
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.week import monday_of


class BabyFood(models.Model):
    class Texture(models.TextChoices):
        PUREE = "pure", "Puré"
        MASHED = "mashed", "Chafado"
        PIECES = "pieces", "Trozos"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="baby_foods"
    )
    name = models.CharField("nombre", max_length=120)
    texture = models.CharField(
        "textura", max_length=16, choices=Texture.choices, default=Texture.PUREE
    )
    is_new = models.BooleanField("nuevo", default=True)
    is_active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "alimento del bebé"
        verbose_name_plural = "alimentos del bebé"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BabyPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="baby_plans"
    )
    week_start = models.DateField("inicio de semana")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "semana del bebé"
        verbose_name_plural = "semanas del bebé"
        constraints = [
            models.UniqueConstraint(
                fields=["household", "week_start"], name="uniq_baby_household_week"
            ),
        ]
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.household} bebé {self.week_start}"

    def clean(self):
        if self.week_start and self.week_start != monday_of(self.week_start):
            raise ValidationError({"week_start": "La semana debe empezar en lunes."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def week_end(self):
        return self.week_start + timedelta(days=6)


class BabyPlanEntry(models.Model):
    class Slot(models.TextChoices):
        LUNCH = "comida", "Comida"
        SNACK = "merienda", "Merienda"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BabyPlan, on_delete=models.CASCADE, related_name="entries")
    day = models.DateField()
    slot = models.CharField(max_length=16, choices=Slot.choices)
    food = models.ForeignKey(
        BabyFood, on_delete=models.PROTECT, related_name="plan_entries"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "comida del bebé"
        verbose_name_plural = "comidas del bebé"
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "day", "slot"], name="uniq_baby_plan_day_slot"
            ),
        ]
        ordering = ["day", "slot"]

    def __str__(self):
        return f"{self.day} {self.get_slot_display()}: {self.food}"

    def clean(self):
        if not self.plan_id or not self.day or not self.food_id:
            return
        plan = self.plan
        if self.day < plan.week_start or self.day > plan.week_end:
            raise ValidationError({"day": "El día no pertenece a la semana."})
        if self.food.household_id != plan.household_id:
            raise ValidationError({"food": "El alimento debe ser del mismo hogar."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
