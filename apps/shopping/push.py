import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from apps.shopping.models import ShoppingPushSubscription
from apps.shopping.selectors import person_label

log = logging.getLogger(__name__)


def notify_others(household, user, client_key, body):
    private_key = getattr(settings, "VAPID_PRIVATE_KEY", "")
    if not private_key:
        return
    subscriptions = ShoppingPushSubscription.objects.filter(household=household)
    if client_key:
        subscriptions = subscriptions.exclude(client_key=client_key)
    payload = json.dumps(
        {"title": "Lista de compra", "body": body, "url": "/lista/"},
        ensure_ascii=False,
    )
    claims = {"sub": settings.VAPID_SUBJECT}
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=claims,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                subscription.delete()
            else:
                log.warning("No se pudo avisar del cambio en la lista")
        except Exception:
            log.warning("No se pudo avisar del cambio en la lista")


def added_notice(user, item_name):
    return f"{person_label(user)} añadió {item_name}"


def cleared_notice(user):
    return f"{person_label(user)} ha hecho la compra"
