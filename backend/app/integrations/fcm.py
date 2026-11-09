import logging

import firebase_admin
from firebase_admin import credentials, messaging

from ..core.config import settings

logger = logging.getLogger(__name__)


def send(token: str, title: str, body: str) -> bool:
    """Send one push notification. Return False if FCM is unavailable."""

    credentials_path = settings.fcm_credentials_path

    if not credentials_path:
        logger.warning("FCM credentials are not configured.")
        return False

    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                credentials.Certificate(credentials_path)
            )

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )

        messaging.send(message)
        return True

    except Exception:
        logger.exception("Failed to send FCM notification.")
        return False