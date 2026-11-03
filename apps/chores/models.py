import re
import uuid

from django.conf import settings
from django.db import models


class Chore(models.Model):
    class Cadence(models.TextChoices):
        TODAY = "hoy", "Hoy"
        DAILY = "dia", "Cada día"
        WEEKLY = "semana", "Cada semana"
        SOMEDAY = "cuando", "Cuando puedas"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="chores"
    )
    title = models.CharField("tarea", max_length=80)
    cadence = models.CharField(
        "cuándo", max_length=16, choices=Cadence.choices, default=Cadence.TODAY
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_chores",
        verbose_name="quién",
    )
    weekday = models.PositiveSmallIntegerField(null=True, blank=True)
    done_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["household", "cadence"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.title = re.sub(r"\s+", " ", (self.title or "").strip())
        super().save(*args, **kwargs)
