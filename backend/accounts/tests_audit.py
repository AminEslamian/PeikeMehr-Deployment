from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import OTPVerification, Teacher


def make_teacher(**kwargs):
    defaults = {
        "phone_number": "09123456789",
        "first_name": "Audit",
        "last_name": "Teacher",
        "province": "Qom",
        "city": "Qom",
        "school": "Audit School",
        "position": "teacher",
        "gender": "man",
        "national_id": "1234567890",
    }
    defaults.update(kwargs)
    return Teacher.objects.create(**defaults)


class OTPLockoutTests(APITestCase):
    def setUp(self):
        self.teacher = make_teacher()
        self.otp = OTPVerification.create_otp("09123456789", code="1234")
        self.url = reverse("login-verify-otp")

    def test_six_wrong_attempts_invalidate_otp(self):
        for _ in range(6):
            response = self.client.post(
                self.url,
                {"phone_number": "09123456789", "code": "9999"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(
            OTPVerification.objects.filter(pk=self.otp.pk).exists()
        )

    def test_otp_cannot_be_reused_after_login(self):
        first = self.client.post(
            self.url,
            {"phone_number": "09123456789", "code": "1234"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            self.url,
            {"phone_number": "09123456789", "code": "1234"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second.data["error_code"], "No active OTP found.")

    def test_expired_otp_rejected(self):
        OTPVerification.objects.filter(pk=self.otp.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.post(
            self.url,
            {"phone_number": "09123456789", "code": "1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error_code"], "OTP has expired.")


class TokenHandlingTests(APITestCase):
    def setUp(self):
        self.teacher = make_teacher()
        self.url = reverse("profile")

    def test_missing_token_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_token_rejected(self):
        token = AccessToken.for_user(self.teacher)
        token.set_exp(
            from_time=timezone.now() - timedelta(days=10),
            lifetime=timedelta(minutes=5),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TeacherAuthorizationTests(APITestCase):
    def setUp(self):
        self.teacher_a = make_teacher()
        self.teacher_b = make_teacher(
            phone_number="09120000000",
            national_id="0000000001",
        )
        self.client.force_authenticate(user=self.teacher_a)

    def test_profile_returns_only_own_record(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone_number"], "09123456789")

    def test_teacher_cannot_list_admin_teachers(self):
        response = self.client.get("/admin-panel/api/teachers/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_read_another_teacher_via_admin(self):
        response = self.client.get(
            f"/admin-panel/api/teachers/{self.teacher_b.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_list_admin_reports(self):
        response = self.client.get("/admin-panel/api/reports/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_create_admin_points(self):
        response = self.client.post(
            "/admin-panel/api/points/",
            {"teacher": self.teacher_a.id, "score": 10, "reason": "self"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RegistrationValidationTests(APITestCase):
    def setUp(self):
        self.url = reverse("register-verify-otp")
        OTPVerification.create_otp("09123456789", code="1234")

    def _payload(self, **overrides):
        data = {
            "phone_number": "09123456789",
            "code": "1234",
            "first_name": "Audit",
            "last_name": "Teacher",
            "province": "Qom",
            "city": "Qom",
            "village": "",
            "school": "Audit School",
            "position": "teacher",
            "gender": "man",
            "national_id": "1234567890",
            "grade": ["first"],
        }
        data.update(overrides)
        return data

    def test_unknown_grade_is_rejected(self):
        response = self.client.post(
            self.url,
            self._payload(grade=["does-not-exist"]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_grade_does_not_create_teacher(self):
        response = self.client.post(
            self.url,
            self._payload(grade=["does-not-exist"]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            Teacher.objects.filter(
                phone_number="09123456789"
            ).exists()
        )
