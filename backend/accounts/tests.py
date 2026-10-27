# accounts/tests.py
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.models import Teacher, OTPVerification, Grade
from accounts.views import (
    normalize_phone_number,
    check_rate_limit,
    verify_otp_code,
)


# =========================================================
#   HELPERS / FIXTURES
# =========================================================

def create_teacher(**kwargs):
    """ساخت یک معلم با مقادیر پیش‌فرض معتبر"""
    defaults = {
        "phone_number": "09123456789",
        "first_name": "محمد",
        "last_name": "افشاری",
        "province": "قم",
        "city": "قم",
        "school": "طاهباز",
        "position": "teacher",
        "national_id": "1234567890",
        "gender": "man",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Teacher.objects.create(**defaults)


def create_otp(phone_number="09123456789", code="1234", **kwargs):
    """ساخت یک OTP معتبر"""
    return OTPVerification.create_otp(phone_number, code=code, **kwargs)


# =========================================================
#   UNIT TESTS — HELPERS
# =========================================================

class NormalizePhoneNumberTests(TestCase):
    """تست تابع normalize_phone_number"""

    def test_plus98_prefix_converted(self):
        self.assertEqual(
            normalize_phone_number("+989123456789"),
            "09123456789",
        )

    def test_already_normalized_unchanged(self):
        self.assertEqual(
            normalize_phone_number("09123456789"),
            "09123456789",
        )

    def test_other_prefix_unchanged(self):
        self.assertEqual(
            normalize_phone_number("989123456789"),
            "989123456789",
        )


class CheckRateLimitTests(TestCase):
    """تست تابع check_rate_limit"""

    def test_no_otp_returns_false(self):
        self.assertFalse(check_rate_limit("09123456789"))

    def test_recent_otp_returns_true(self):
        create_otp(phone_number="09123456789")
        self.assertTrue(check_rate_limit("09123456789"))

    def test_old_otp_returns_false(self):
        otp = create_otp(phone_number="09123456789")
        # OTP رو دستی ۲ دقیقه قبل می‌کنیم
        OTPVerification.objects.filter(pk=otp.pk).update(
            created_at=timezone.now() - timedelta(minutes=2)
        )
        self.assertFalse(check_rate_limit("09123456789"))

    def test_different_phone_returns_false(self):
        create_otp(phone_number="09123456789")
        self.assertFalse(check_rate_limit("09999999999"))


class VerifyOTPCodeTests(TestCase):
    """تست تابع verify_otp_code"""

    def test_no_otp_returns_error(self):
        otp, error = verify_otp_code("09123456789", "1234")
        self.assertIsNone(otp)
        self.assertEqual(error, "No active OTP found.")

    def test_expired_otp_returns_error(self):
        otp = create_otp(phone_number="09123456789", code="1234")
        OTPVerification.objects.filter(pk=otp.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        otp.refresh_from_db()
        _, error = verify_otp_code("09123456789", "1234")
        self.assertEqual(error, "OTP has expired.")

    def test_wrong_code_returns_error(self):
        create_otp(phone_number="09123456789", code="1234")
        _, error = verify_otp_code("09123456789", "9999")
        self.assertEqual(error, "Invalid OTP code.")

    def test_correct_code_returns_otp(self):
        create_otp(phone_number="09123456789", code="1234")
        otp, error = verify_otp_code("09123456789", "1234")
        self.assertIsNotNone(otp)
        self.assertIsNone(error)
        self.assertEqual(otp.code, "1234")

    def test_verified_otp_ignored(self):
        otp = create_otp(phone_number="09123456789", code="1234")
        otp.is_verified = True
        otp.save()
        _, error = verify_otp_code("09123456789", "1234")
        self.assertEqual(error, "No active OTP found.")

    def test_returns_latest_otp(self):
        create_otp(phone_number="09123456789", code="1111")
        create_otp(phone_number="09123456789", code="2222")
        otp, _ = verify_otp_code("09123456789", "2222")
        self.assertIsNotNone(otp)
        self.assertEqual(otp.code, "2222")


# =========================================================
#   INTEGRATION TESTS — SendOTPView
# =========================================================

@patch("accounts.views.send_sms")
class SendOTPViewTests(APITestCase):
    """تست SendOTPView"""

    def setUp(self):
        self.url = reverse("login-send-otp")

    def test_teacher_not_found(self, mock_send_sms):
        response = self.client.post(
            self.url,
            {"phone_number": "09123456789"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_send_sms.assert_not_called()

    def test_successful_otp_send(self, mock_send_sms):
        create_teacher(phone_number="09123456789")
        response = self.client.post(
            self.url,
            {"phone_number": "09123456789"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            OTPVerification.objects.filter(
                phone_number="09123456789"
            ).count(),
            1,
        )
        mock_send_sms.assert_called_once()

    def test_rate_limit_returns_429(self, mock_send_sms):
        create_teacher(phone_number="09123456789")
        create_otp(phone_number="09123456789")
        response = self.client.post(
            self.url,
            {"phone_number": "09123456789"},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        mock_send_sms.assert_not_called()

    def test_plus98_normalized(self, mock_send_sms):
        create_teacher(phone_number="09123456789")
        self.client.post(
            self.url,
            {"phone_number": "+989123456789"},
            format="json",
        )
        self.assertTrue(
            OTPVerification.objects.filter(
                phone_number="09123456789"
            ).exists()
        )

    def test_invalid_phone_format(self, mock_send_sms):
        response = self.client.post(
            self.url,
            {"phone_number": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =========================================================
#   INTEGRATION TESTS — VerifyOTPView
# =========================================================

class VerifyOTPViewTests(APITestCase):
    """تست VerifyOTPView"""

    def setUp(self):
        self.url = reverse("login-verify-otp")
        self.teacher = create_teacher(phone_number="09123456789")
        self.otp = create_otp(
            phone_number="09123456789", code="1234"
        )

    def test_invalid_code_returns_400(self):
        response = self.client.post(
            self.url,
            {"phone_number": "09123456789", "code": "9999"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["error_code"], "Invalid OTP code."
        )

    def test_teacher_not_found_returns_404(self):
        # OTP برای شماره‌ای که معلم نداره
        create_otp(phone_number="09999999999", code="5555")
        response = self.client.post(
            self.url,
            {"phone_number": "09999999999", "code": "5555"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_successful_login_returns_tokens(self):
        response = self.client.post(
            self.url,
            {"phone_number": "09123456789", "code": "1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("redirect_url", response.data)
        # معلم عادی ریدایرکت به /main/
        self.assertEqual(response.data["redirect_url"], "/main/")

    def test_superuser_redirects_to_admin(self):
        superuser = create_teacher(
            phone_number="09121111111",
            national_id="1111111111",
            is_superuser=True,
            is_staff=True,
        )
        create_otp(phone_number="09121111111", code="4321")
        response = self.client.post(
            self.url,
            {"phone_number": "09121111111", "code": "4321"},
            format="json",
        )
        self.assertEqual(
            response.data["redirect_url"],
            "/admin-panel/",
        )

    def test_otp_deleted_after_verify(self):
        self.client.post(
            self.url,
            {"phone_number": "09123456789", "code": "1234"},
            format="json",
        )
        self.assertFalse(
            OTPVerification.objects.filter(pk=self.otp.pk).exists()
        )

    def test_expired_otp_returns_400(self):
        OTPVerification.objects.filter(pk=self.otp.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.post(
            self.url,
            {"phone_number": "09123456789", "code": "1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =========================================================
#   INTEGRATION TESTS — RegisterSendOTPView
# =========================================================

@patch("accounts.views.send_sms")
class RegisterSendOTPViewTests(APITestCase):
    """تست RegisterSendOTPView"""

    def setUp(self):
        self.url = reverse("register-send-otp")

    def _payload(self, **overrides):
        data = {
            "phone_number": "09123456789",
            "first_name": "محمد",
            "last_name": "افشاری",
            "province": "قم",
            "city": "قم",
            "village": "",
            "school": "طاهباز",
            "position": "teacher",
            "gender": "man",
            "grade": ["first"],
            "national_id": "1234567890",
        }
        data.update(overrides)
        return data

    def test_successful_otp_send(self, mock_send_sms):
        response = self.client.post(
            self.url, self._payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            OTPVerification.objects.filter(
                phone_number="09123456789"
            ).exists()
        )
        mock_send_sms.assert_called_once()

    def test_blank_national_id_allowed(self, mock_send_sms):
        create_teacher(
            phone_number="09999999999",
            national_id="",
        )
        response = self.client.post(
            self.url,
            self._payload(phone_number="09123456789", national_id=""),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_sms.assert_called_once()

    def test_duplicate_phone_returns_400(self, mock_send_sms):
        create_teacher(phone_number="09123456789")
        response = self.client.post(
            self.url, self._payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_send_sms.assert_not_called()

    def test_duplicate_national_id_returns_400(self, mock_send_sms):
        create_teacher(
            phone_number="09999999999",
            national_id="1234567890",
        )
        response = self.client.post(
            self.url, self._payload(), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rate_limit_returns_429(self, mock_send_sms):
        create_otp(phone_number="09123456789")
        response = self.client.post(
            self.url, self._payload(), format="json"
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


# =========================================================
#   INTEGRATION TESTS — RegisterVerifyOTPView
# =========================================================

class RegisterVerifyOTPViewTests(APITestCase):
    """تست RegisterVerifyOTPView"""

    def setUp(self):
        self.url = reverse("register-verify-otp")

        # OTP برای ثبت‌نام
        create_otp(phone_number="09123456789", code="1234")

    def _payload(self, **overrides):
        data = {
            "phone_number": "09123456789",
            "code": "1234",
            "first_name": "محمد",
            "last_name": "افشاری",
            "province": "قم",
            "city": "قم",
            "village": "",
            "school": "طاهباز",
            "position": "teacher",
            "national_id": "1234567890",
            "gender": "man",
            "grade": ["first", "second"],
        }
        data.update(overrides)
        return data

    def test_successful_registration(self):
        response = self.client.post(
            self.url, self._payload(), format="json"
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED
        )
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        teacher = Teacher.objects.get(
            phone_number="09123456789"
        )
        self.assertEqual(teacher.first_name, "محمد")
        self.assertEqual(
            teacher.grade.count(), 2
        )

    def test_invalid_code_returns_400(self):
        response = self.client.post(
            self.url,
            self._payload(code="9999"),
            format="json",
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )
        self.assertFalse(
            Teacher.objects.filter(
                phone_number="09123456789"
            ).exists()
        )

    def test_phone_already_registered_returns_400(self):
        create_teacher(phone_number="09123456789")
        response = self.client.post(
            self.url, self._payload(), format="json"
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST
        )

    def test_otp_marked_as_verified(self):
        self.client.post(
            self.url, self._payload(), format="json"
        )
        otp = OTPVerification.objects.filter(
            phone_number="09123456789"
        ).first()
        self.assertTrue(otp.is_verified)

    def test_grade_set_correctly(self):
        self.client.post(
            self.url, self._payload(), format="json"
        )
        teacher = Teacher.objects.get(
            phone_number="09123456789"
        )
        grade_values = set(
            teacher.grade.values_list("value", flat=True)
        )
        self.assertEqual(grade_values, {"first", "second"})

    def test_blank_national_id_creates_null(self):
        response = self.client.post(
            self.url,
            self._payload(national_id=""),
            format="json",
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED
        )
        teacher = Teacher.objects.get(
            phone_number="09123456789"
        )
        self.assertIsNone(teacher.national_id)

    def test_teacher_is_active(self):
        self.client.post(
            self.url, self._payload(), format="json"
        )
        teacher = Teacher.objects.get(
            phone_number="09123456789"
        )
        self.assertTrue(teacher.is_active)

    def test_transaction_rollback_on_grade_error(self):
        """اگه ساخت grade خطا بده، teacher ساخته نشه"""
        # این رو با mock کردن Grade.objects.filter شبیه‌سازی می‌کنیم
        with patch(
            "accounts.views.Grade.objects.filter",
            side_effect=Exception("boom"),
        ):
            with self.assertRaises(Exception):
                self.client.post(
                    self.url, self._payload(), format="json"
                )

        # هیچ معلمی نباید ساخته شده باشه
        self.assertFalse(
            Teacher.objects.filter(
                phone_number="09123456789"
            ).exists()
        )


# =========================================================
#   INTEGRATION TESTS — ProfileView
# =========================================================

class ProfileViewTests(APITestCase):
    """تست ProfileView"""

    def setUp(self):
        self.url = reverse("profile")
        self.teacher = create_teacher(
            phone_number="09123456789"
        )

    def test_anonymous_user_gets_401(self):
        response = self.client.get(self.url)
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_authenticated_user_gets_profile(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["phone_number"], "09123456789"
        )

    def test_profile_get_returns_grade_values(self):
        self.teacher.grade.add(Grade.objects.get(value="first"))
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["grade"], ["first"])

    def test_profile_patch_accepts_grade_values(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.patch(
            self.url,
            {"grade": ["first", "second"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data["grade"]),
            {"first", "second"},
        )

        self.teacher.refresh_from_db()
        self.assertEqual(
            set(self.teacher.grade.values_list("value", flat=True)),
            {"first", "second"},
        )

    def test_profile_patch_updates_name(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.patch(
            self.url,
            {"first_name": "علی"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.first_name, "علی")

    def test_profile_patch_invalid_grade_returns_400(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.patch(
            self.url,
            {"grade": ["unknown"]},
            format="json",
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("grade", response.data)