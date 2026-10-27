from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Teacher
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


class TicketAPITests(APITestCase):
    def setUp(self):
        self.teacher = make_teacher()
        self.other = make_teacher(
            phone_number="09120000000",
            national_id="0000000001",
        )
        self.url = "/api/tickets/"

    def test_unauthenticated_list_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_sets_identity_from_authenticated_user(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self.url,
            {
                "title": "Help",
                "content": "Please help",
                "first_name": "Forged",
                "phone_number": "09999999999",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = Ticket.objects.get(pk=response.data["id"])
        self.assertEqual(ticket.first_name, self.teacher.first_name)
        self.assertEqual(ticket.phone_number, self.teacher.phone_number)

    def test_create_requires_title_and_content(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_only_sees_own_tickets(self):
        own = Ticket.objects.create(
            title="Own",
            content="Own content",
            first_name="Audit",
            last_name="Teacher",
            phone_number=self.teacher.phone_number,
        )
        Ticket.objects.create(
            title="Other",
            content="Other content",
            first_name="Other",
            last_name="Teacher",
            phone_number=self.other.phone_number,
        )
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [own.id])

    def test_user_cannot_retrieve_other_ticket(self):
        other = Ticket.objects.create(
            title="Other",
            content="Other content",
            first_name="Other",
            last_name="Teacher",
            phone_number=self.other.phone_number,
        )
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(f"{self.url}{other.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_delete_other_ticket(self):
        other = Ticket.objects.create(
            title="Other",
            content="Other content",
            first_name="Other",
            last_name="Teacher",
            phone_number=self.other.phone_number,
        )
        self.client.force_authenticate(user=self.teacher)
        response = self.client.delete(f"{self.url}{other.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Ticket.objects.filter(pk=other.id).exists())

    def test_user_cannot_write_admin_answer_fields(self):
        self.client.force_authenticate(user=self.teacher)
        create = self.client.post(
            self.url,
            {"title": "Help", "content": "Please help"},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            f"{self.url}{create.data['id']}/",
            {"answer": "Forged answer", "is_answered": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ticket = Ticket.objects.get(pk=create.data["id"])
        self.assertIsNone(ticket.answer)
        self.assertFalse(ticket.is_answered)
