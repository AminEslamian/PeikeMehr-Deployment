"""SMS provider abstraction.

Only the "sms_ir" provider sends a real message. The "mock" provider is
allowed for local development/tests only when explicitly enabled. A missing
provider or a provider error raises SMSDeliveryError so callers never report a
false success.
"""

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSDeliveryError(Exception):
    """Raised when an OTP SMS could not be delivered."""


def mask_phone(phone_number: str) -> str:
    digits = str(phone_number or "")
    if len(digits) < 6:
        return "***"
    return f"{digits[:4]}***{digits[-2:]}"


def send_otp_sms(phone_number: str, code: str) -> None:
    provider = (settings.SMS_PROVIDER or "disabled").strip().lower()

    if provider == "mock":
        if not settings.SMS_ALLOW_MOCK and not settings.DEBUG:
            raise SMSDeliveryError(
                "Mock SMS provider is disabled outside development."
            )
        if settings.OTP_LOG_CODES:
            logger.info(
                "Local test OTP for %s is %s (OTP_LOG_CODES enabled)",
                mask_phone(phone_number),
                code,
            )
        logger.info(
            "Mock OTP SMS generated for %s (no message sent)",
            mask_phone(phone_number),
        )
        return

    if provider in {"sms_ir", "sms.ir", "smsir"}:
        _send_sms_ir(phone_number, code)
        return

    raise SMSDeliveryError("No SMS provider is configured.")


def _send_sms_ir(phone_number: str, code: str) -> None:
    if not settings.SMS_IR_API_KEY:
        raise SMSDeliveryError("SMS provider API key is not configured.")

    if not settings.SMS_IR_TEMPLATE_ID:
        raise SMSDeliveryError("SMS provider template ID is not configured.")

    url = settings.SMS_IR_VERIFY_URL
    headers = {
        "X-API-KEY": settings.SMS_IR_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "mobile": phone_number,
        "templateId": settings.SMS_IR_TEMPLATE_ID,
        "parameters": [{"name": "Code", "value": str(code)}],
    }

    attempts = max(1, settings.SMS_MAX_RETRIES)
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=settings.SMS_REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            last_error = exc.__class__.__name__
            logger.warning(
                "SMS provider request failed for %s (attempt %s/%s): %s",
                mask_phone(phone_number),
                attempt,
                attempts,
                last_error,
            )
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 4))
                continue
            raise SMSDeliveryError(
                "SMS provider is unreachable."
            ) from exc

        if response.status_code >= 500:
            last_error = f"HTTP {response.status_code}"
            logger.warning(
                "SMS provider server error for %s (attempt %s/%s): %s",
                mask_phone(phone_number),
                attempt,
                attempts,
                last_error,
            )
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 4))
                continue
            raise SMSDeliveryError("SMS provider server error.")

        if response.status_code != 200:
            logger.warning(
                "SMS provider rejected request for %s: HTTP %s",
                mask_phone(phone_number),
                response.status_code,
            )
            raise SMSDeliveryError("SMS provider rejected the request.")

        try:
            data = response.json()
        except ValueError:
            logger.warning(
                "SMS provider returned a non-JSON response for %s",
                mask_phone(phone_number),
            )
            raise SMSDeliveryError("SMS provider returned an invalid response.")

        if data.get("status") != 1:
            logger.warning(
                "SMS provider did not accept message for %s (status=%s)",
                mask_phone(phone_number),
                data.get("status"),
            )
            raise SMSDeliveryError("SMS provider did not accept the message.")

        logger.info("OTP SMS accepted by provider for %s", mask_phone(phone_number))
        return

    raise SMSDeliveryError("SMS delivery failed.")
