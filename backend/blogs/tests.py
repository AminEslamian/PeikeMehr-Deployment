import base64
import os
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Teacher
from blogs.models import Blog

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


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


class BlogAPITests(APITestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self._tmp)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.addCleanup(shutil.rmtree, self._tmp, True)

        self.teacher = make_teacher()
        self.admin = make_teacher(
            phone_number="09120000000",
            national_id="0000000001",
            is_staff=True,
        )
        self.url = "/api/blogs/"

    def _image(self):
        return SimpleUploadedFile("announcement.png", PNG_BYTES, content_type="image/png")

    def test_unauthenticated_list_rejected(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_teacher_can_list(self):
        Blog.objects.create(title="News", content="Body", media=self._image())
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_teacher_cannot_create(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            self.url,
            {"title": "News", "content": "Body", "media": self._image()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_cannot_delete(self):
        blog = Blog.objects.create(title="News", content="Body", media=self._image())
        self.client.force_authenticate(user=self.teacher)
        response = self.client.delete(f"{self.url}{blog.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Blog.objects.filter(pk=blog.id).exists())

    def test_staff_delete_removes_media_file(self):
        blog = Blog.objects.create(title="News", content="Body", media=self._image())
        stored_path = blog.media.path
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f"{self.url}{blog.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(os.path.exists(stored_path))

    def test_staff_can_create_with_allowed_extension(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self.url,
            {"title": "News", "content": "Body", "media": self._image()},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Blog.objects.count(), 1)

    def test_staff_create_rejects_disallowed_extension(self):
        self.client.force_authenticate(user=self.admin)
        pdf = SimpleUploadedFile("doc.pdf", b"%PDF-1.4", content_type="application/pdf")
        response = self.client.post(
            self.url,
            {"title": "News", "content": "Body", "media": pdf},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_create_without_media_is_rejected(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            self.url,
            {"title": "News", "content": "Body"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
