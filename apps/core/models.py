import uuid

from django.conf import settings
from django.db import models


class HouseMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Persona"
        CASA = "casa", "Casa"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="house_messages"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="house_messages",
    )
    role = models.CharField(max_length=8, choices=Role.choices)
    body = models.TextField()
    receipts = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "mensaje de casa"
        verbose_name_plural = "mensajes de casa"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["household", "user", "created_at"]),
        ]

    def __str__(self):
        return self.body[:40]
