import json
import logging
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """El servicio de correo no aceptó o no alcanzó el envío."""


class BrevoEmailBackend(BaseEmailBackend):
    """Envía por la API HTTPS de Brevo. Render bloquea los puertos SMTP."""

    endpoint = "https://api.brevo.com/v3/smtp/email"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _send(self, message):
        from_email = message.from_email or settings.DEFAULT_FROM_EMAIL
        name, email = parseaddr(from_email)
        if not email:
            email = from_email
        recipients = [{"email": address} for address in message.to]
        if not recipients:
            return False
        payload = {
            "sender": {"name": name or "Nuestro Menú", "email": email},
            "to": recipients,
            "subject": message.subject,
            "textContent": message.body,
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": settings.BREVO_API_KEY,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=15) as response:
                response.read()
        except HTTPError as exc:
            logger.error("Brevo rechazó el correo (%s).", exc.code)
            if not self.fail_silently:
                raise EmailDeliveryError("No se pudo enviar el correo.") from exc
            return False
        except (URLError, TimeoutError, OSError) as exc:
            logger.error("Brevo no respondió.")
            if not self.fail_silently:
                raise EmailDeliveryError("No se pudo enviar el correo.") from exc
            return False
        return True
