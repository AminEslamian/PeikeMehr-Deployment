from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Teacher
from reports.models import Point
from tickets.models import Ticket


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


class AdminAPIAccessTests(APITestCase):
    def setUp(self):
        self.teacher = make_teacher()
        self.admin = make_teacher(
            phone_number="09120000000",
            national_id="0000000001",
            is_staff=True,
        )
        self.teacher_url = "/admin-panel/api/teachers/"

    def test_unauthenticated_rejected(self):
        response = self.client.get(self.teacher_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_forbidden(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.teacher_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_list_teachers(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.teacher_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_teacher_list_excludes_staff_accounts(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.teacher_url)
        ids = [item["id"] for item in response.data["results"]]
        self.assertNotIn(self.admin.id, ids)

    def test_teacher_list_excludes_superusers(self):
        superuser = make_teacher(
            phone_number="09120000002",
            national_id="0000000002",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.teacher_url)
        ids = [item["id"] for item in response.data["results"]]
        self.assertNotIn(superuser.id, ids)
        self.assertIn(self.teacher.id, ids)

    def test_staff_can_retrieve_teacher(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"{self.teacher_url}{self.teacher.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["phone_number"], self.teacher.phone_number)

    def test_staff_can_search_teachers(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f"{self.teacher_url}?search=09123456789")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_staff_can_list_reports(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/admin-panel/api/reports/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_can_award_points(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/admin-panel/api/points/",
            {"teacher": self.teacher.id, "score": 5, "reason": "Audit"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Point.objects.count(), 1)

    def test_staff_answer_marks_ticket_answered(self):
        ticket = Ticket.objects.create(
            title="Help",
            content="Please help",
            first_name="Audit",
            last_name="Teacher",
            phone_number=self.teacher.phone_number,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/admin-panel/api/tickets/{ticket.id}/",
            {"answer": "Resolved"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertTrue(ticket.is_answered)

    def test_staff_media_list_all_returns_list(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/admin-panel/api/media-list/?all=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_admin_template_page_requires_authentication(self):
        response = self.client.get("/admin-panel/")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_admin_template_page_allows_staff(self):
        self.client.force_login(self.admin)
        response = self.client.get("/admin-panel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_template_page_rejects_teacher(self):
        self.client.force_login(self.teacher)
        response = self.client.get("/admin-panel/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
