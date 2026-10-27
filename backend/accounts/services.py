from rest_framework_simplejwt.tokens import RefreshToken

from .sms import SMSDeliveryError, send_otp_sms


def send_sms(phone_number: str, message: str) -> None:
    """
    Send an OTP through the configured provider.

    Kept as a thin wrapper so existing call sites and tests can patch it.
    Raises SMSDeliveryError when delivery is not possible.
    """
    send_otp_sms(phone_number, message)


def _generate_tokens(teacher):
    refresh = RefreshToken.for_user(teacher)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "teacher": {
            "id": teacher.id,
            "phone_number": teacher.phone_number,
            "first_name": teacher.first_name,
            "last_name": teacher.last_name,
        },
    }
