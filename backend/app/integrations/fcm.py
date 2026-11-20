import logging

import firebase_admin
from firebase_admin import credentials, messaging

from ..core.config import settings

logger = logging.getLogger(__name__)


def send(token: str, title: str, body: str) -> bool:
    """Send a push notification to an FCM registration token."""

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
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    icon="/icons/Icon-192.png",
                )
            ),
        )

        messaging.send(message)
        logger.info("FCM notification accepted by Firebase.")
        return True

    except Exception:
        logger.exception("Failed to send FCM notification.")
        return False