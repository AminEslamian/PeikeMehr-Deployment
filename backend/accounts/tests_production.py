import re
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import OTPVerification, Teacher
from accounts.sms import SMSDeliveryError, send_otp_sms


def make_teacher(**kwargs):
    defaults = {
        "phone_number": "09123456789",
        "first_name": "Production",
        "last_name": "Teacher",
        "province": "Qom",
        "city": "Qom",
        "school": "Production School",
        "position": "teacher",
        "gender": "man",
        "national_id": "1234567890",
    }
    defaults.update(kwargs)
    return Teacher.objects.create(**defaults)


class SMSProviderTests(APITestCase):
    @override_settings(
        SMS_PROVIDER="mock",
        SMS_ALLOW_MOCK=False,
        DEBUG=False,
    )
    def test_mock_provider_is_rejected_in_production(self):
        with self.assertRaises(SMSDeliveryError):
            send_otp_sms("09123456789", "1234")

    @override_settings(
        SMS_PROVIDER="mock",
        SMS_ALLOW_MOCK=True,
        OTP_LOG_CODES=False,
    )
    @patch("builtins.print")
    def test_mock_provider_does_not_print_otp(self, mock_print):
        send_otp_sms("09123456789", "1234")
        mock_print.assert_not_called()

    @override_settings(
        SMS_PROVIDER="mock",
        SMS_ALLOW_MOCK=True,
        OTP_LOG_CODES=True,
    )
    def test_mock_provider_logs_code_when_enabled(self):
        with self.assertLogs("accounts.sms", level="INFO") as captured:
            send_otp_sms("09123456789", "4321")

        self.assertIn("4321", "\n".join(captured.output))

    @override_settings(
        SMS_PROVIDER="mock",
        SMS_ALLOW_MOCK=True,
        OTP_LOG_CODES=False,
    )
    def test_mock_provider_does_not_log_code_when_disabled(self):
        with self.assertLogs("accounts.sms", level="INFO") as captured:
            send_otp_sms("09123456789", "4321")

        self.assertNotIn("4321", "\n".join(captured.output))

    @override_settings(
        SMS_PROVIDER="sms_ir",
        SMS_IR_API_KEY="test-key",
        SMS_IR_TEMPLATE_ID=1,
        OTP_LOG_CODES=True,
    )
    @patch("accounts.sms._send_sms_ir")
    @patch("accounts.sms.logger")
    def test_code_is_not_logged_for_real_provider(
        self, mock_logger, _mock_send
    ):
        send_otp_sms("09123456789", "9876")

        logged = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        self.assertNotIn("9876", logged)

    @override_settings(
        SMS_PROVIDER="mock",
        SMS_ALLOW_MOCK=False,
        DEBUG=False,
        OTP_LOG_CODES=True,
    )
    @patch("accounts.sms.logger")
    def test_code_is_not_logged_when_mock_is_disabled(self, mock_logger):
        with self.assertRaises(SMSDeliveryError):
            send_otp_sms("09123456789", "9876")

        logged = " ".join(
            str(call) for call in mock_logger.info.call_args_list
        )
        self.assertNotIn("9876", logged)

    @override_settings(SMS_PROVIDER="disabled")
    def test_missing_provider_raises(self):
        with self.assertRaises(SMSDeliveryError):
            send_otp_sms("09123456789", "1234")

    @override_settings(
        SMS_PROVIDER="sms_ir",
        SMS_IR_API_KEY="",
        SMS_IR_TEMPLATE_ID=0,
    )
    def test_missing_sms_ir_credentials_raise(self):
        with self.assertRaises(SMSDeliveryError):
            send_otp_sms("09123456789", "1234")


class OTPCodeLoggingIntegrationTests(APITestCase):
    @override_settings(
        SMS_PROVIDER="mock",
        SMS_ALLOW_MOCK=True,
        OTP_LOG_CODES=True,
    )
    def test_login_send_logs_the_generated_otp(self):
        make_teacher()

        with self.assertLogs("accounts.sms", level="INFO") as captured:
            response = self.client.post(
                reverse("login-send-otp"),
                {"phone_number": "09123456789"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        match = re.search(r"is (\d{4})", "\n".join(captured.output))
        self.assertIsNotNone(match)

        otp = OTPVerification.objects.get(
            phone_number="09123456789"
        )
        self.assertEqual(otp.code, match.group(1))


class OTPDeliveryFailureTests(APITestCase):
    def setUp(self):
        self.teacher = make_teacher()

    @patch(
        "accounts.views.send_sms",
        side_effect=SMSDeliveryError("provider down"),
    )
    def test_login_does_not_report_success_when_sms_fails(self, _mock):
        response = self.client.post(
            reverse("login-send-otp"),
            {"phone_number": "09123456789"},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertFalse(
            OTPVerification.objects.filter(
                phone_number="09123456789"
            ).exists()
        )

    @patch(
        "accounts.views.send_sms",
        side_effect=SMSDeliveryError("provider down"),
    )
    def test_registration_does_not_report_success_when_sms_fails(self, _mock):
        response = self.client.post(
            reverse("register-send-otp"),
            {
                "phone_number": "09999999999",
                "first_name": "Production",
                "last_name": "Teacher",
                "province": "Qom",
                "city": "Qom",
                "village": "",
                "school": "Production School",
                "position": "teacher",
                "gender": "man",
                "grade": ["first"],
                "national_id": "0000000009",
            },
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertFalse(
            OTPVerification.objects.filter(
                phone_number="09999999999"
            ).exists()
        )


class HealthCheckTests(APITestCase):
    def test_health_endpoint_reports_database_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["database"], "ok")


class JWTRefreshTests(APITestCase):
    def setUp(self):
        self.teacher = make_teacher()
        self.refresh = RefreshToken.for_user(self.teacher)
        self.url = reverse("token-refresh")

    def test_refresh_returns_new_access_and_rotated_refresh(self):
        response = self.client.post(
            self.url,
            {"refresh": str(self.refresh)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_rotated_refresh_token_cannot_be_reused(self):
        first = self.client.post(
            self.url,
            {"refresh": str(self.refresh)},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            self.url,
            {"refresh": str(self.refresh)},
            format="json",
        )
        self.assertEqual(
            second.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class RegistrationGradeValidationTests(APITestCase):
    def setUp(self):
        self.url = reverse("register-verify-otp")
        OTPVerification.create_otp("09123456789", code="1234")

    def _payload(self, **overrides):
        data = {
            "phone_number": "09123456789",
            "code": "1234",
            "first_name": "Production",
            "last_name": "Teacher",
            "province": "Qom",
            "city": "Qom",
            "village": "",
            "school": "Production School",
            "position": "teacher",
            "gender": "man",
            "national_id": "1234567890",
            "grade": ["first"],
        }
        data.update(overrides)
        return data

    def test_mixed_known_and_unknown_grade_is_rejected(self):
        response = self.client.post(
            self.url,
            self._payload(grade=["first", "does-not-exist"]),
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(
            Teacher.objects.filter(
                phone_number="09123456789"
            ).exists()
        )

    def test_empty_grade_list_is_rejected(self):
        response = self.client.post(
            self.url,
            self._payload(grade=[]),
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_invalid_national_id_is_rejected(self):
        response = self.client.post(
            self.url,
            self._payload(national_id="123"),
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class OTPCleanupCommandTests(APITestCase):
    def test_cleanup_removes_old_rows_only(self):
        old = OTPVerification.create_otp("09123456789", code="1111")
        OTPVerification.objects.filter(pk=old.pk).update(
            created_at=old.created_at.replace(year=2000)
        )
        recent = OTPVerification.create_otp("09123456789", code="2222")

        call_command("cleanup_otps", "--days", "1", verbosity=0)

        self.assertFalse(
            OTPVerification.objects.filter(pk=old.pk).exists()
        )
        self.assertTrue(
            OTPVerification.objects.filter(pk=recent.pk).exists()
        )
